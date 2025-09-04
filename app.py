import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

app = FastAPI()

# Ensure uploads folder exists
os.makedirs("uploads", exist_ok=True)
os.makedirs("presets", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def main_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Video Upload</title>
    </head>
    <body style="font-family: sans-serif; text-align:center; padding:50px;">
      <h1>🎬 Upload a Video</h1>
      <form id="uploadForm" enctype="multipart/form-data">
        <input type="file" name="file" id="fileInput" required /><br><br>
        <label><input type="checkbox" id="captions" name="captions"> Add Captions</label><br>
        <label><input type="checkbox" id="music" name="music"> Add Background Music</label><br><br>
        <button type="submit">Upload</button>
      </form>
      <p id="status"></p>
      <script>
        document.getElementById("uploadForm").onsubmit = async (e) => {
          e.preventDefault();
          const fileInput = document.getElementById("fileInput").files[0];
          const formData = new FormData();
          formData.append("file", fileInput);
          formData.append("captions", document.getElementById("captions").checked);
          formData.append("music", document.getElementById("music").checked);

          document.getElementById("status").innerText = "Uploading...";

          const response = await fetch("/upload_video/", {
            method: "POST",
            body: formData
          });

          if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "processed_video.mp4";
            a.click();
            document.getElementById("status").innerText = "✅ Done! Video downloaded.";
          } else {
            document.getElementById("status").innerText = "❌ Upload failed.";
          }
        };
      </script>
    </body>
    </html>
    """

@app.post("/upload_video/")
async def upload_video(
    file: UploadFile = File(...),
    captions: bool = Form(False),
    music: bool = Form(False)
):
    # Save uploaded video
    input_path = f"uploads/{uuid.uuid4()}_{file.filename}"
    output_path = input_path.replace(".mp4", "_out.mp4")

    with open(input_path, "wb") as f:
        f.write(await file.read())

    # Load video
    clip = VideoFileClip(input_path)

    # Add captions if requested
    if captions:
        txt = TextClip("Sample Captions", fontsize=50, color="white")
        txt = txt.set_duration(clip.duration).set_position(("center", "bottom"))
        clip = CompositeVideoClip([clip, txt])

    # Add background music if requested
    if music:
        music_path = "presets/preset1.mp3"
        if not os.path.exists(music_path):
            # Generate placeholder silence if missing
            import subprocess
            subprocess.run([
                "ffmpeg", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-t", str(int(clip.duration)),
                music_path
            ])
        audio = AudioFileClip(music_path).volumex(0.2)
        clip = clip.set_audio(audio.set_duration(clip.duration))

    # Write output video
    clip.write_videofile(output_path, codec="libx264")

    return FileResponse(output_path, media_type="video/mp4", filename="processed_video.mp4")

@app.get("/ping")
async def ping():
    return {"status": "ok"}
