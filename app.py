from fastapi import FastAPI, File, UploadFile, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os, tempfile, shutil
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, TextClip, CompositeVideoClip
import whisper
import stripe
from sqlalchemy.orm import Session
from your_auth_module import get_current_user, User, db  # replace with your auth/db module

STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

app = FastAPI()
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
app.mount("/presets", StaticFiles(directory="presets"), name="presets")

@app.get("/", response_class=HTMLResponse)
def home_page():
    return HTMLResponse(open('frontend/index.html').read())

@app.post("/process")
def process_video(file: UploadFile = File(...), mode: str = Form("short"),
                  background_music: bool = Form(True), captions: bool = Form(True),
                  music_file: str = Form(None), user: User = Depends(get_current_user)):
    if not user.subscribed and user.free_credits <= 0:
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity":1}],
            success_url="https://yourapp.com/success",
            cancel_url="https://yourapp.com/cancel"
        )
        return {"error":"Credits used up", "checkout_url":checkout.url}
    else:
        user.free_credits -= 1
        db.commit()

    with tempfile.NamedTemporaryFile(delete=False,suffix=".mp4") as tmp:
        tmp.write(file.file.read())
        input_path = tmp.name

    final_clip = VideoFileClip(input_path)

    if background_music and music_file:
        music_path = music_file if not music_file.startswith('/presets/') else '.'+music_file
        music = AudioFileClip(music_path).volumex(0.2)
        final_audio = CompositeAudioClip([final_clip.audio, music])
        final_clip = final_clip.set_audio(final_audio)

    if captions:
        model = whisper.load_model("small")
        result = model.transcribe(input_path)
        caption_clips = []
        for seg in result["segments"]:
            txt = TextClip(seg["text"], fontsize=24, color="white", bg_color="black")
            txt = txt.set_start(seg["start"]).set_duration(seg["end"]-seg["start"]).set_position(("center","bottom"))
            caption_clips.append(txt)
        final_clip = CompositeVideoClip([final_clip,*caption_clips])

    out_path = f"/tmp/final_{os.getpid()}.mp4"
    final_clip.write_videofile(out_path, codec="libx264", audio_codec="aac")
    return FileResponse(out_path, media_type="video/mp4", filename="highlight.mp4")

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(user: User = Depends(get_current_user)):
    if not user.is_admin:
        return HTMLResponse("<h1>Access Denied</h1>", status_code=403)
    return HTMLResponse(open('frontend/admin.html').read())

@app.get("/admin/presets")
def list_presets(user: User = Depends(get_current_user)):
    if not user.is_admin: return {"error":"access denied"}
    return os.listdir("./presets")

@app.post("/admin/upload_preset")
def upload_preset(file: UploadFile = File(...), name: str = Form(...), user: User = Depends(get_current_user)):
    if not user.is_admin: return {"error":"access denied"}
    ext = os.path.splitext(file.filename)[1]
    save_path = f"./presets/{name}{ext}"
    with open(save_path,"wb") as f: shutil.copyfileobj(file.file, f)
    return {"success":True}

@app.get("/admin/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(db)):
    if not user.is_admin: return {"error":"access denied"}
    users = db.query(User).all()
    return [{"email":u.email,"free_credits":u.free_credits,"subscribed":u.subscribed} for u in users]
