"""
Web server: upload an audio file, get the full guitar-tab transcription
+ visualization back automatically. No manual path editing at any point.

Run with:  python app.py
Then open: http://localhost:5001
"""

import os
import uuid
import traceback

from flask import Flask, request, jsonify, send_file, render_template

from pipeline import run_full_pipeline

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded. Field name must be 'audio'."}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type '{ext}'."}), 400

    # Optional manual BPM override; if omitted, pipeline auto-estimates it.
    bpm_raw = request.form.get("bpm")
    bpm = float(bpm_raw) if bpm_raw not in (None, "") else None

    session_id = uuid.uuid4().hex
    session_dir = os.path.join(OUTPUT_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    audio_path = os.path.join(session_dir, audio_file.filename)
    audio_file.save(audio_path)

    try:
        result = run_full_pipeline(audio_path, session_dir, bpm=bpm)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    return jsonify(
        {
            "session_id": session_id,
            "bpm_used": result["bpm"],
            "midi_url": f"/download/{session_id}/output.mid",
            "npz_url": f"/download/{session_id}/prediction.npz",
            "image_url": f"/download/{session_id}/tab_visualization.png",
        }
    )


@app.route("/download/<session_id>/<filename>")
def download(session_id, filename):
    # Basic guard against path traversal.
    if "/" in session_id or "\\" in session_id or "/" in filename or "\\" in filename:
        return jsonify({"error": "invalid path"}), 400
    path = os.path.join(OUTPUT_DIR, session_id, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404
    return send_file(path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)