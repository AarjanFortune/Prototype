"""YouTube URL validation and audio extraction."""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from config import TEMP_DIR


SUPPORTED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
}

SUPPORTED_PATH_PREFIXES = ("/watch", "/shorts/", "/live/", "/embed/")
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,}$")
MEDIA_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".opus", ".webm"}


class YouTubeUrlError(ValueError):
    """Raised when a submitted YouTube URL is malformed or unsupported."""


@dataclass(frozen=True)
class YouTubeDownload:
    audio_path: str
    title: str
    video_id: str
    webpage_url: str
    size_bytes: int


def clean_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def log_terminal(msg: str, is_error: bool = False) -> None:
    prefix = "\033[91m[YOUTUBE ERROR]\033[0m" if is_error else "\033[92m[YOUTUBE]\033[0m"
    print(f"{prefix} {msg}", flush=True)


def validate_youtube_url(raw_url: str) -> str:
    """Return a normalized single-video YouTube URL or raise YouTubeUrlError.

    Supported inputs include watch URLs, Shorts, live URLs, embeds, and youtu.be
    links. Playlist context is stripped from video URLs so extraction remains a
    single-item operation; playlist-only URLs are intentionally rejected.
    """
    value = raw_url.strip()
    if not value:
        raise YouTubeUrlError("A YouTube URL is required.")

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    query = parse_qs(parsed.query)

    if scheme not in {"http", "https"}:
        raise YouTubeUrlError("Only HTTP and HTTPS YouTube links are supported.")
    if host not in SUPPORTED_HOSTS:
        raise YouTubeUrlError("The URL must point to youtube.com or youtu.be.")

    video_id = _extract_video_id(host, path, query)
    if not video_id or not VIDEO_ID_PATTERN.match(video_id):
        raise YouTubeUrlError("The URL does not contain a valid YouTube video identifier.")

    if host == "youtu.be":
        return urlunparse(("https", "youtu.be", f"/{video_id}", "", "", ""))

    if path.startswith("/shorts/"):
        return urlunparse(("https", "www.youtube.com", f"/shorts/{video_id}", "", "", ""))
    if path.startswith("/live/"):
        return urlunparse(("https", "www.youtube.com", f"/live/{video_id}", "", "", ""))
    if path.startswith("/embed/"):
        return urlunparse(("https", "www.youtube.com", f"/watch", "", urlencode({"v": video_id}), ""))

    if path == "/watch":
        return urlunparse(("https", "www.youtube.com", "/watch", "", urlencode({"v": video_id}), ""))

    raise YouTubeUrlError("This YouTube URL format is not supported.")


def _extract_video_id(host: str, path: str, query: dict[str, list[str]]) -> str | None:
    if host == "youtu.be":
        return path.strip("/").split("/")[0] or None

    if path == "/watch":
        return _first(query.get("v"))

    for prefix in SUPPORTED_PATH_PREFIXES:
        if path.startswith(prefix) and prefix != "/watch":
            return path.removeprefix(prefix).strip("/").split("/")[0] or None

    return None


def _first(values: Iterable[str] | None) -> str | None:
    if not values:
        return None
    return next(iter(values), None)


def get_standalone_ytdlp() -> Path:
    """Download and cache the standalone yt-dlp executable when needed."""
    bin_dir = Path(__file__).parent / "bin"
    bin_dir.mkdir(exist_ok=True)
    exe_path = bin_dir / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")

    if exe_path.exists():
        return exe_path

    if os.name != "nt":
        installed = shutil.which("yt-dlp")
        if installed:
            return Path(installed)
        raise RuntimeError("yt-dlp is not installed. Install backend requirements first.")

    log_terminal("First run detected: downloading yt-dlp.exe.")
    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    try:
        with urllib.request.urlopen(url) as response, open(exe_path, "wb") as out_file:
            out_file.write(response.read())
        if exe_path.stat().st_size < 1_000_000:
            exe_path.unlink()
            raise RuntimeError("Downloaded file is too small and may be corrupt.")
    except Exception as exc:
        raise RuntimeError(f"Failed to download the yt-dlp executable: {exc}") from exc

    return exe_path


def download_youtube_source(raw_url: str) -> YouTubeDownload:
    """Validate a YouTube URL and return extracted audio with source metadata."""
    normalized_url = validate_youtube_url(raw_url)
    ytdlp_exe = get_standalone_ytdlp()
    output_dir = TEMP_DIR / f"youtube_{uuid.uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(ytdlp_exe),
        "--no-playlist",
        "--no-warnings",
        "--force-ipv4",
        "--format",
        "bestaudio/best",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "192K",
        "--write-info-json",
        "-o",
        str(output_dir / "%(id)s.%(ext)s"),
        normalized_url,
    ]

    ffmpeg_path = _resolve_ffmpeg_path()
    if ffmpeg_path:
        cmd.extend(["--ffmpeg-location", ffmpeg_path])

    js_runtime = _resolve_js_runtime()
    if js_runtime:
        cmd.extend(["--js-runtimes", js_runtime])

    try:
        log_terminal(f"Extracting audio from normalized URL: {normalized_url}")
        result = None
        for attempt in range(3):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                break
            if attempt < 2:
                log_terminal(f"Extraction attempt {attempt + 1} failed; refreshing the media URL.")
                _clear_download_attempt(output_dir)
                time.sleep(1)

        if result is None or result.returncode != 0:
            error_output = result.stderr if result else ""
            standard_output = result.stdout if result else ""
            raise RuntimeError(error_output.strip() or standard_output.strip() or "yt-dlp failed")

        media_files = [path for path in output_dir.glob("*") if path.suffix.lower() in MEDIA_EXTENSIONS]
        if not media_files:
            raise FileNotFoundError(result.stderr.strip() or "yt-dlp completed without producing audio.")

        audio_file = max(media_files, key=os.path.getmtime)
        source_metadata = _read_source_metadata(output_dir)
        video_id = str(source_metadata.get("id") or audio_file.stem)
        title = str(source_metadata.get("title") or video_id)
        webpage_url = str(source_metadata.get("webpage_url") or normalized_url)
        log_terminal(f"Audio extraction complete: {audio_file}")
        return YouTubeDownload(
            audio_path=str(audio_file),
            title=title,
            video_id=video_id,
            webpage_url=webpage_url,
            size_bytes=audio_file.stat().st_size,
        )
    except YouTubeUrlError:
        raise
    except Exception as exc:
        message = clean_ansi(str(exc))
        log_terminal(message, is_error=True)
        raise ValueError(f"YouTube extraction failed: {message}") from exc


def download_youtube_audio(raw_url: str) -> str:
    """Compatibility wrapper returning only the extracted audio path."""
    return download_youtube_source(raw_url).audio_path


def _read_source_metadata(output_dir: Path) -> dict:
    info_files = list(output_dir.glob("*.info.json"))
    if not info_files:
        return {}

    info_file = max(info_files, key=os.path.getmtime)
    try:
        with info_file.open("r", encoding="utf-8") as file:
            return json.load(file)
    finally:
        info_file.unlink(missing_ok=True)


def _clear_download_attempt(output_dir: Path) -> None:
    for path in output_dir.iterdir():
        if path.is_file():
            path.unlink(missing_ok=True)


def _resolve_ffmpeg_path() -> str | None:
    local_ffmpeg = os.path.expandvars(r"%LOCALAPPDATA%\ffmpeg\bin")
    if os.name == "nt" and os.path.exists(os.path.join(local_ffmpeg, "ffmpeg.exe")):
        return local_ffmpeg

    ffmpeg = shutil.which("ffmpeg")
    return str(Path(ffmpeg).parent) if ffmpeg else None


def _resolve_js_runtime() -> str | None:
    for runtime in ("deno", "node", "bun"):
        executable = shutil.which(runtime)
        if executable:
            return f"{runtime}:{executable}"
    return None
