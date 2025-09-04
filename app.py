from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import shutil
import os
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, TextClip, CompositeVideoClip

app = FastAPI()

# Make sure uploads folder exists
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "App is running ✅"}

@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_location = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load video
        video = VideoFileClip(file_location)

        # Example: Add background music (if bg.mp3 exists in uploads)
        audio_clips = [video.audio]
        bg_music_path = os.path.join(UPLOAD_FOLDER, "bg.mp3")
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1)
            audio_clips.append(bg_music)

        final_audio = CompositeAudioClip(audio_clips)
        video = video.set_audio(final_audio)

        # Example: Add watermark text
        txt = TextClip("Demo Highlight", fontsize=40, color="white")
        txt = txt.set_pos(("center","bottom")).set_duration(video.duration)

        final = CompositeVideoClip([video, txt])

        output_path = os.path.join(OUTPUT_FOLDER, "output.mp4")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")

        return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
