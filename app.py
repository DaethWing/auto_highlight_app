import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

app = FastAPI()

# Ensure folders
os.makedirs("uploads", exist_ok=True)
os.makedirs("presets", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head><title>Video Uploader</title></head>
    <body style="font-family:sans-serif; text-align:center; padding:50px;">
      <h1>Upload Video 🎬</h1>
      <form id="form" enctype="multipart/form-data">
        <input type="file" name="file" required /><br><br>
        <label><input type="checkbox" name="captions"> Add Captions</label><br>
        <label><input type="checkbox" name="music"> Add Music</label><br><br>
        <button type="submit">Upload</button>
      </form>
      <p id="status"></p>
      <script>
        document.getElementById("form").onsubmit = async (e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          document.getElementById("status").innerText = "Processing...";
          const res = await fetch("/upload_video/", { method: "POST", body: formData });
          if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "output.mp4";
            a.click();
            document.getElementById("status").innerText = "✅ Done!";
          } else {
            document.getElementById("status").innerText = "❌ Failed.";
          }
        }
      </script>
    </body>
    </html>
    """

@app.post("/upload_video/")
async def upload_video(file: UploadFile = File(...), captions: bool = Form(False), music: bool = Form(False)):
    input_path = f"uploads/{uuid.uuid4()}_{file.filename}"
    output_path = input_path.replace(".mp4", "_out.mp4")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    clip = VideoFileClip(input_path)

    if captions:
        txt = TextClip("Sample Captions", fontsize=40, color="white")
        txt = txt.set_duration(clip.duration).set_position(("center","bottom"))
        clip = CompositeVideoClip([clip, txt])

    if music:
        music_path = "presets/music.mp3"
        if not os.path.exists(music_path):
            import subprocess
            subprocess.run([
                "ffmpeg", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(int(clip.duration)), music_path
            ])
        bg = AudioFileClip(music_path).volumex(0.2)
        clip = clip.set_audio(bg.set_duration(clip.duration))

    clip.write_videofile(output_path, codec="libx264")

    return FileResponse(output_path, media_type="video/mp4", filename="output.mp4")

@app.get("/ping")
async def ping():
    return {"status": "ok"}
