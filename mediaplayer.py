import os
import re
import io
import json
import uuid
import hashlib
import shutil
import socket
import zipfile
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2000 * 1024 * 1024  # 2000 MB

_SCAN_LOCK = threading.Lock()

BASE_DIR = Path(__file__).parent
DATA_ROOT = Path(os.environ.get("FLOWCAST_DATA_DIR", str(BASE_DIR.parent)))
PORT = int(os.environ.get("FLOWCAST_PORT", "5010"))
HOST = os.environ.get("FLOWCAST_HOST", "0.0.0.0")
MEDIA_DIR = DATA_ROOT / "media_static"
MEDIA_GENERAL_DIR = DATA_ROOT / "media_general"
MEDIA_GUEST_DIR = DATA_ROOT / "media_guest"
MEDIA_FAVORITES_DIR = DATA_ROOT / "media_favorites"
ANDROID_UPLOAD_DIR = DATA_ROOT / "android_upload"
ARCHIVE_DIR = DATA_ROOT / "Archive"
CONVERTED_CACHE_DIR = DATA_ROOT / "media_converted"
CONVERTED_CACHE_MAP = CONVERTED_CACHE_DIR / "_cache_map.json"
PLAYLIST_FILE = BASE_DIR / "playlist.json"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "mp4"}
CONVERT_EXTENSIONS = {"avi", "wmv", "mov", "mkv"}
ALLOWED_FADE_TYPES = {"normaali", "liuku-vasen", "liuku-oikea", "zoom-in", "zoom-ulos", "random"}
HEX_RE = re.compile(r'^[0-9a-f]{32}$')
EXTERNAL_CACHE = []
_SCANNING_EXTERNAL = False
EXTERNAL_ALIAS_RE = re.compile(r'^ext-[0-9a-f]{32}$')

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_GENERAL_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_GUEST_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_FAVORITES_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
ANDROID_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ffmpeg_cmd() -> str:
    """Return path to ffmpeg executable."""
    ffmpeg_local = BASE_DIR / "ffmpeg.exe"
    return str(ffmpeg_local) if ffmpeg_local.exists() else "ffmpeg"


def _ffmpeg_encode_args() -> list:
    """Return optimal ffmpeg encode arguments. Prefers hardware acceleration."""
    # Try Intel QuickSync first (integrated GPU, common on i7)
    try:
        result = subprocess.run(
            [_ffmpeg_cmd(), "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5
        )
        encoders = result.stdout + result.stderr
        if "h264_qsv" in encoders:
            return ["-c:v", "h264_qsv", "-preset", "fast", "-c:a", "aac"]
        if "h264_nvenc" in encoders:
            return ["-c:v", "h264_nvenc", "-preset", "p1", "-c:a", "aac"]
        if "h264_amf" in encoders:
            return ["-c:v", "h264_amf", "-quality", "speed", "-c:a", "aac"]
    except Exception:
        pass
    # Software fallback: fast preset
    return ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac"]


def convert_to_mp4(src_path: Path) -> Path:
    """Convert a file to MP4, DELETING the original."""
    ffmpeg = _ffmpeg_cmd()
    out_path = src_path.with_suffix(".mp4")
    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(src_path)] + _ffmpeg_encode_args()
            + ["-movflags", "+faststart", str(out_path)],
            capture_output=True, timeout=600
        )
    except FileNotFoundError:
        src_path.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg ei ole asennettu")
    src_path.unlink(missing_ok=True)
    if result.returncode != 0 or not out_path.exists():
        out_path.unlink(missing_ok=True)
        raise RuntimeError("Konversio epaonnistui")
    return out_path


def _load_cache_map() -> dict:
    """Load the conversion cache mapping: {source_hash: cached_filename}."""
    if CONVERTED_CACHE_MAP.exists():
        try:
            with open(CONVERTED_CACHE_MAP, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache_map(mapping: dict) -> None:
    """Save the conversion cache mapping."""
    with open(CONVERTED_CACHE_MAP, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def convert_external_to_mp4(src_path: Path) -> Path:
    """Convert an external file to MP4, PRESERVING the original.
    Uses original filename; adds short suffix only on name collisions.
    Skips conversion if a fresh cached copy already exists."""
    src_key = hashlib.md5(str(src_path.resolve()).encode("utf-8")).hexdigest()
    cache_map = _load_cache_map()

    # Prefer original stem: MVI_4915.mp4
    base_name = f"{src_path.stem}.mp4"
    cache_name = cache_map.get(src_key)

    if cache_name:
        # Known source → check if cached file is still fresh
        cache_path = CONVERTED_CACHE_DIR / cache_name
        if cache_path.exists():
            try:
                if cache_path.stat().st_mtime >= src_path.stat().st_mtime:
                    return cache_path
            except OSError:
                pass
        # Cache stale or missing → reconvert with same name
    else:
        # New source → determine filename
        cache_path = CONVERTED_CACHE_DIR / base_name
        if cache_path.exists():
            # Name collision: check if it belongs to another source
            already_mapped = False
            for k, v in cache_map.items():
                if v == base_name and k != src_key:
                    already_mapped = True
                    break
            if already_mapped:
                # Add short hash suffix: MVI_4915_a1b2c3d4.mp4
                short_hash = src_key[:8]
                cache_name = f"{src_path.stem}_{short_hash}.mp4"
            else:
                cache_name = base_name
        else:
            cache_name = base_name
        cache_path = CONVERTED_CACHE_DIR / cache_name

    # Re-check staleness for newly resolved path
    if cache_path.exists():
        try:
            if cache_path.stat().st_mtime >= src_path.stat().st_mtime:
                cache_map[src_key] = cache_name
                _save_cache_map(cache_map)
                return cache_path
        except OSError:
            pass

    ffmpeg = _ffmpeg_cmd()
    print(f"  [ffmpeg] Konvertoidaan: {src_path.name} -> {cache_name}")
    try:
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(src_path)] + _ffmpeg_encode_args()
            + ["-movflags", "+faststart", str(cache_path)],
            capture_output=True, timeout=600
        )
    except FileNotFoundError:
        raise RuntimeError("FFmpeg ei ole asennettu")

    if result.returncode != 0 or not cache_path.exists():
        cache_path.unlink(missing_ok=True)
        stderr_tail = result.stderr.decode("utf-8", errors="replace")[-300:] if result.stderr else ""
        raise RuntimeError(f"Konversio epaonnistui: {stderr_tail}")

    # Store mapping
    cache_map[src_key] = cache_name
    _save_cache_map(cache_map)
    return cache_path


def get_video_duration(filepath: Path) -> float:
    """Return video duration in seconds using ffmpeg. Returns 0 on failure."""
    ffmpeg_local = BASE_DIR / "ffmpeg.exe"
    ffmpeg_cmd = str(ffmpeg_local) if ffmpeg_local.exists() else "ffmpeg"
    try:
        result = subprocess.run(
            [ffmpeg_cmd, "-i", str(filepath)],
            capture_output=True, text=True, timeout=30
        )
        # ffmpeg outputs duration info to stderr
        output = result.stderr
        # Look for "Duration: HH:MM:SS.ms"
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", output)
        if match:
            h, m, s, ms = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100.0
    except Exception:
        pass
    return 0.0


def load_playlist():
    if not PLAYLIST_FILE.exists():
        default = {
            "settings": {
                "default_duration": 60,
                "fade_enabled": True,
                "fade_duration": 1.0,
                "fade_type": "normaali",
                "video_audio": False,
                "video_duration": "default",
                "shuffle_enabled": True,
                "playback_buttons": True,
                "general_enabled": True,
                "general_shuffle_enabled": True,
                "guest_enabled": True,
                "guest_shuffle_enabled": True,
                "favorites_enabled": True,
                "favorites_shuffle_enabled": True,
                "favorites_playback_buttons": "minimi",
                "favorites_show_filename": False,
                "content_filter": "all",
                "external_shuffle_enabled": True,
                "show_video_timer": True,
                "show_filename": True
            },
            "items": [],
            "external_dirs": [],
            "admin_ui": {
                "show_fields": {
                    "default_duration": True,
                    "fade_enabled": True,
                    "fade_duration": True,
                    "fade_type": True,
                    "video_audio": True,
                    "video_duration": True,
                    "show_video_timer": True,
                    "playback_buttons": True,
                    "content_filter": True,
                    "show_filename": True
                },
                "sections": {
                    "custom": {"enabled": True, "open": False},
                    "general": {"enabled": True, "open": True},
                    "external": {"enabled": True, "open": False},
                    "favorites": {"enabled": True, "open": True},
                    "guest": {"enabled": True, "open": False}
                }
            }
        }
        save_playlist(default)
        return default
    with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_playlist(data):
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def scan_external_dirs():
    """Scan all registered external directories at startup. Missing dirs are skipped with a warning."""
    global EXTERNAL_CACHE, _SCANNING_EXTERNAL
    if not _SCAN_LOCK.acquire(blocking=False):
        # Toinen skannaus jo käynnissä — älä tuplaa
        return
    try:
        _SCANNING_EXTERNAL = True
        EXTERNAL_CACHE = []
        data = load_playlist()
        external_dirs = data.get("external_dirs", [])
        for entry in external_dirs:
            if not entry.get("enabled", True):
                continue
            dir_path = entry.get("path", "")
            if not dir_path:
                continue
            p = Path(dir_path)
            if not p.is_dir():
                print(f"  [!] Ulkoista hakemistoa ei loydy, ohitetaan: {dir_path}")
                continue
            file_count = 0
            try:
                for f in sorted(p.rglob("*")):
                    if not f.is_file():
                        continue
                    ext = f.suffix.lower().lstrip('.')
                    # Handle convert-to-mp4 formats (avi, wmv, mov, mkv)
                    if ext in CONVERT_EXTENSIONS:
                        try:
                            converted = convert_external_to_mp4(f)
                        except RuntimeError as e:
                            print(f"  [!] Konversio epaonnistui: {f.name} – {e}")
                            continue
                        alias = f"ext-{hashlib.md5(str(f).encode('utf-8')).hexdigest()}"
                        rel = f.relative_to(p).as_posix()
                        entry_data = {
                            "filename": rel,
                            "src": f"/media_converted/{converted.name}",
                            "type": "video",
                            "name": f"{entry.get('label', p.name)}/{rel}",
                            "alias": alias,
                            "duration": get_video_duration(converted)
                        }
                        EXTERNAL_CACHE.append(entry_data)
                        file_count += 1
                        continue

                    if ext not in ALLOWED_EXTENSIONS:
                        continue
                    ftype = "video" if ext == "mp4" else "image"
                    alias = f"ext-{hashlib.md5(str(f).encode('utf-8')).hexdigest()}"
                    rel = f.relative_to(p).as_posix()
                    entry_data = {
                        "filename": rel,
                        "src": f"/api/external/file?path={f.as_posix()}",
                        "type": ftype,
                        "name": f"{entry.get('label', p.name)}/{rel}",
                        "alias": alias
                    }
                    if ftype == "video":
                        entry_data["duration"] = get_video_duration(f)
                    EXTERNAL_CACHE.append(entry_data)
                    file_count += 1
                print(f"  [+] Ulkoinen hakemisto: {dir_path} ({file_count} tiedostoa)")
            except PermissionError:
                print(f"  [!] Ei lukuoikeutta hakemistoon: {dir_path}")
        print(f"  [*] Ulkoisia tiedostoja yhteensa: {len(EXTERNAL_CACHE)}")
    finally:
        _SCANNING_EXTERNAL = False
        _SCAN_LOCK.release()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


@app.route("/")
def index():
    return redirect(url_for("admin"))


@app.route("/favicon.ico")
@app.route("/favicon.svg")
def favicon():
    return send_from_directory(app.template_folder, "favicon.svg", mimetype="image/svg+xml")


@app.route("/display")
def display():
    return render_template("display.html", content_filter_override=None)


@app.route("/img")
def images():
    return render_template("display.html", content_filter_override="images")


@app.route("/vid")
def videos():
    return render_template("display.html", content_filter_override="videos")


@app.route("/fav")
def favorites():
    return render_template("display.html", content_filter_override=None, favorites_only=True)


@app.route("/adminloginhere")
def admin():
    return render_template("loading.html")


@app.route("/adminpanel")
def adminpanel():
    base = request.host_url.rstrip("/")
    display_url = f"{base}/display"
    images_url = f"{base}/img"
    videos_url = f"{base}/vid"
    fav_url = f"{base}/fav"
    guest_url = f"{base}/guest"
    favorites_dir = str(MEDIA_FAVORITES_DIR).replace("\\", "/")
    general_dir = str(MEDIA_GENERAL_DIR).replace("\\", "/")
    guest_dir = str(MEDIA_GUEST_DIR).replace("\\", "/")
    data = load_playlist()
    admin_ui = data.get("admin_ui", {})
    return render_template("admin.html", display_url=display_url, images_url=images_url, videos_url=videos_url, fav_url=fav_url, guest_url=guest_url, favorites_dir=favorites_dir, general_dir=general_dir, guest_dir=guest_dir, admin_ui=admin_ui)


@app.route("/adminsettings")
def adminsettings():
    data = load_playlist()
    admin_ui = data.get("admin_ui", {})
    return render_template("settings.html", admin_ui=admin_ui)


@app.route("/api/admin-ui", methods=["GET"])
def api_get_admin_ui():
    data = load_playlist()
    return jsonify(data.get("admin_ui", {}))


@app.route("/api/admin-ui", methods=["POST"])
def api_save_admin_ui():
    data = load_playlist()
    body = request.get_json()
    if "show_fields" in body:
        data.setdefault("admin_ui", {}).setdefault("show_fields", {}).update(body["show_fields"])
    if "sections" in body:
        data.setdefault("admin_ui", {}).setdefault("sections", {}).update(body["sections"])
    save_playlist(data)
    return jsonify({"ok": True})


@app.route("/api/ping")
def api_ping():
    return jsonify({"ok": True})


@app.route("/guest")
def guest():
    base = request.host_url.rstrip("/")
    display_url = f"{base}/display"
    images_url = f"{base}/img"
    videos_url = f"{base}/vid"
    return render_template("admin_guest.html", display_url=display_url, images_url=images_url, videos_url=videos_url)


@app.route("/api/playlist", methods=["GET"])
def api_get_playlist():
    response = jsonify(load_playlist())
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = load_playlist()
    body = request.get_json()
    if "default_duration" in body:
        data["settings"]["default_duration"] = int(body["default_duration"])
    if "fade_enabled" in body:
        data["settings"]["fade_enabled"] = bool(body["fade_enabled"])
    if "fade_duration" in body:
        data["settings"]["fade_duration"] = float(body["fade_duration"])
    if "fade_type" in body:
        if str(body["fade_type"]) in ALLOWED_FADE_TYPES:
            data["settings"]["fade_type"] = str(body["fade_type"])
    if "video_audio" in body:
        data["settings"]["video_audio"] = bool(body["video_audio"])
    if "playback_buttons" in body:
        data["settings"]["playback_buttons"] = bool(body["playback_buttons"])
    if "shuffle_enabled" in body:
        data["settings"]["shuffle_enabled"] = bool(body["shuffle_enabled"])
    if "general_enabled" in body:
        data["settings"]["general_enabled"] = bool(body["general_enabled"])
    if "general_shuffle_enabled" in body:
        data["settings"]["general_shuffle_enabled"] = bool(body["general_shuffle_enabled"])
    if "guest_enabled" in body:
        data["settings"]["guest_enabled"] = bool(body["guest_enabled"])
    if "guest_shuffle_enabled" in body:
        data["settings"]["guest_shuffle_enabled"] = bool(body["guest_shuffle_enabled"])
    if "favorites_enabled" in body:
        data["settings"]["favorites_enabled"] = bool(body["favorites_enabled"])
    if "favorites_shuffle_enabled" in body:
        data["settings"]["favorites_shuffle_enabled"] = bool(body["favorites_shuffle_enabled"])
    if "favorites_playback_buttons" in body:
        val = str(body["favorites_playback_buttons"])
        if val in ("täysin", "minimi", "off"):
            data["settings"]["favorites_playback_buttons"] = val
    if "favorites_show_filename" in body:
        data["settings"]["favorites_show_filename"] = bool(body["favorites_show_filename"])
    if "content_filter" in body:
        if body["content_filter"] in {"all", "images", "videos"}:
            data["settings"]["content_filter"] = str(body["content_filter"])
    if "external_shuffle_enabled" in body:
        data["settings"]["external_shuffle_enabled"] = bool(body["external_shuffle_enabled"])
    if "video_duration" in body:
        if body["video_duration"] in {"full", "default"}:
            data["settings"]["video_duration"] = str(body["video_duration"])
    if "show_video_timer" in body:
        data["settings"]["show_video_timer"] = bool(body["show_video_timer"])
    if "show_filename" in body:
        data["settings"]["show_filename"] = bool(body["show_filename"])
    save_playlist(data)
    return jsonify({"ok": True})


@app.route("/api/playlist/add", methods=["POST"])
def api_add_item():
    data = load_playlist()

    if "file" in request.files and request.files["file"].filename:
        file = request.files["file"]
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Ei-tuettu tiedostomuoto"}), 400
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(MEDIA_DIR / filename)
        src = f"/media/{filename}"
        name = request.form.get("name") or file.filename
        item_type = "video" if ext == "mp4" else "image"
    else:
        url = request.form.get("url", "").strip()
        if not url:
            return jsonify({"error": "Ei tiedostoa eikä URL:ia"}), 400
        if not re.match(r'^https?://', url, re.IGNORECASE):
            return jsonify({"error": "URL:n täytyy alkaa http:// tai https://"}), 400
        src = url
        name = request.form.get("name") or url
        item_type = "url"

    duration_raw = request.form.get("duration", "").strip()
    item = {
        "id": uuid.uuid4().hex,
        "type": item_type,
        "name": name,
        "src": src,
        "duration": int(duration_raw) if duration_raw.isdigit() else None,
        "fade_override": None,
        "fade_type_override": None,
        "disabled": False
    }
    data["items"].append(item)
    save_playlist(data)
    return jsonify(item)


@app.route("/api/playlist/<item_id>", methods=["PATCH"])
def api_update_item(item_id):
    if not HEX_RE.match(item_id):
        return jsonify({"error": "Virheellinen id"}), 400
    data = load_playlist()
    body = request.get_json()
    for item in data["items"]:
        if item["id"] == item_id:
            if "disabled" in body:
                item["disabled"] = bool(body["disabled"])
            if "duration" in body:
                item["duration"] = body["duration"]
            if "fade_override" in body:
                item["fade_override"] = body["fade_override"]
            if "fade_type_override" in body:
                item["fade_type_override"] = body["fade_type_override"]
            if "name" in body:
                item["name"] = body["name"]
            save_playlist(data)
            return jsonify(item)
    return jsonify({"error": "Ei löydy"}), 404


@app.route("/api/playlist/<item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    if not HEX_RE.match(item_id):
        return jsonify({"error": "Virheellinen id"}), 400
    data = load_playlist()
    item = next((i for i in data["items"] if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Ei löydy"}), 404
    if item["type"] in ("image", "video"):
        filename = item["src"].split("/")[-1]
        filepath = MEDIA_DIR / filename
        if filepath.exists():
            filepath.unlink()
    data["items"] = [i for i in data["items"] if i["id"] != item_id]
    save_playlist(data)
    return jsonify({"ok": True})


@app.route("/api/playlist/reorder", methods=["POST"])
def api_reorder():
    data = load_playlist()
    body = request.get_json()
    order = body.get("order", [])
    id_map = {item["id"]: item for item in data["items"]}
    data["items"] = [id_map[i] for i in order if i in id_map]
    save_playlist(data)
    return jsonify({"ok": True})


@app.route("/api/general/list", methods=["GET"])
def api_general_list():
    files = []
    for f in sorted(MEDIA_GENERAL_DIR.rglob("*")):
        if not f.is_file():
            continue
        if "Archive_" in str(f.relative_to(MEDIA_GENERAL_DIR)):
            continue
        ext = f.suffix.lower().lstrip('.')
        if ext in ALLOWED_EXTENSIONS:
            ftype = "video" if ext == "mp4" else "image"
            rel = f.relative_to(MEDIA_GENERAL_DIR).as_posix()
            entry_data = {
                "filename": rel,
                "src": f"/media_general/{rel}",
                "type": ftype,
                "name": rel
            }
            if ftype == "video":
                entry_data["duration"] = get_video_duration(f)
            files.append(entry_data)
    response = jsonify(files)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/general/upload", methods=["POST"])
def api_general_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Ei tiedostoja"}), 400
    folder_raw = request.form.get("folder", "").strip()
    if not folder_raw:
        return jsonify({"error": "Kansion nimi puuttuu"}), 400
    # Sanitize: allow letters, numbers, spaces, Finnish chars, hyphens, underscores, dots, parentheses
    folder_safe = re.sub(r'[^a-zA-Z0-9äöåÄÖÅ\s\-_.()]', '', folder_raw).strip()
    if not folder_safe or len(folder_safe) > 100:
        return jsonify({"error": "Kansion nimi ei kelpaa"}), 400
    target_dir = MEDIA_GENERAL_DIR / folder_safe
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    skipped = 0
    errors = []
    for file in files:
        if not file.filename:
            continue
        original_name = Path(file.filename).name
        stem = Path(original_name).stem
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext == "zip":
            zip_data = io.BytesIO(file.read())
            try:
                with zipfile.ZipFile(zip_data, "r") as zf:
                    for zinfo in zf.infolist():
                        if zinfo.is_dir():
                            continue
                        zname = Path(zinfo.filename).name
                        zext = zname.rsplit(".", 1)[-1].lower() if "." in zname else ""
                        if zext not in ALLOWED_EXTENSIONS and zext not in CONVERT_EXTENSIONS:
                            continue
                        data = zf.read(zinfo)
                        target_ext = "mp4" if zext in CONVERT_EXTENSIONS else zext
                        zstem = Path(zname).stem
                        target_path = target_dir / f"{zstem}.{target_ext}"
                        if target_path.exists():
                            skipped += 1
                            continue
                        if zext in CONVERT_EXTENSIONS:
                            tmp_path = target_dir / f"{zstem}.{zext}"
                            tmp_path.write_bytes(data)
                            try:
                                convert_to_mp4(tmp_path)
                            except RuntimeError as e:
                                errors.append(f"{zname}: {e}")
                                continue
                        else:
                            target_path.write_bytes(data)
                        saved += 1
            except zipfile.BadZipFile:
                errors.append(f"{file.filename}: Virheellinen ZIP")
        elif ext in ALLOWED_EXTENSIONS:
            target_path = target_dir / original_name
            if target_path.exists():
                skipped += 1
            else:
                data = file.read()
                target_path.write_bytes(data)
                saved += 1
        elif ext in CONVERT_EXTENSIONS:
            target_path = target_dir / f"{stem}.mp4"
            if target_path.exists():
                skipped += 1
            else:
                data = file.read()
                tmp_path = target_dir / original_name
                tmp_path.write_bytes(data)
                try:
                    convert_to_mp4(tmp_path)
                    saved += 1
                except RuntimeError as e:
                    errors.append(f"{original_name}: {e}")
        else:
            errors.append(f"{original_name}: Ei-tuettu muoto")
    return jsonify({"saved": saved, "skipped": skipped, "errors": errors})


@app.route("/api/general/<path:filename>", methods=["DELETE"])
def api_general_delete(filename):
    # Prevent path traversal
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    filepath = MEDIA_GENERAL_DIR / filename
    # Ensure resolved path is still within MEDIA_GENERAL_DIR
    try:
        filepath.resolve().relative_to(MEDIA_GENERAL_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not filepath.exists():
        return jsonify({"error": "Ei löydy"}), 404
    if not filepath.is_file():
        return jsonify({"error": "Ei tiedosto"}), 400
    filepath.unlink()
    return jsonify({"ok": True})


@app.route("/api/general/archive", methods=["POST"])
def api_general_archive():
    files = [f for f in MEDIA_GENERAL_DIR.rglob("*") if f.is_file()
             and f.suffix.lower().lstrip('.') in ALLOWED_EXTENSIONS
             and "Archive_" not in str(f.relative_to(MEDIA_GENERAL_DIR))]
    if not files:
        return jsonify({"error": "Ei tiedostoja arkistoitavaksi"}), 400
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    archive_dir = ARCHIVE_DIR / f"Archive_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.move(str(f), str(archive_dir / f.name))
    # Remove empty subdirectories
    for d in sorted(MEDIA_GENERAL_DIR.rglob("*"), reverse=True):
        if d.is_dir() and d != MEDIA_GENERAL_DIR and not any(d.iterdir()):
            d.rmdir()
    return jsonify({"ok": True, "archive": str(archive_dir), "count": len(files)})


@app.route("/api/general", methods=["DELETE"])
def api_general_clear():
    for f in MEDIA_GENERAL_DIR.rglob("*"):
        if f.is_file():
            f.unlink()
    for d in sorted(MEDIA_GENERAL_DIR.rglob("*"), reverse=True):
        if d.is_dir() and d != MEDIA_GENERAL_DIR and not any(d.iterdir()):
            d.rmdir()
    return jsonify({"ok": True})


@app.route("/api/general/delete-file", methods=["POST"])
def api_general_delete_file():
    body = request.get_json()
    filename = (body.get("filename") or "").strip()
    if not filename:
        return jsonify({"error": "Tiedostonimi puuttuu"}), 400
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    filepath = MEDIA_GENERAL_DIR / filename
    try:
        filepath.resolve().relative_to(MEDIA_GENERAL_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    filepath.unlink()
    data = load_playlist()
    old_src = f"/media_general/{filename}"
    updated = False
    for item in data.get("items", []):
        if item.get("src") == old_src:
            data["items"] = [i for i in data["items"] if i.get("src") != old_src]
            updated = True
            break
    if updated:
        save_playlist(data)
    return jsonify({"ok": True})


@app.route("/api/general/rename-file", methods=["POST"])
def api_general_rename_file():
    body = request.get_json()
    old_filename = (body.get("filename") or "").strip()
    new_name = (body.get("new_name") or "").strip()
    if not old_filename or not new_name:
        return jsonify({"error": "Tiedostonimi tai uusi nimi puuttuu"}), 400
    if ".." in old_filename or old_filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if ".." in new_name or "/" in new_name or "\\" in new_name:
        return jsonify({"error": "Uusi nimi ei saa sisaltaa polkua"}), 400
    old_path = MEDIA_GENERAL_DIR / old_filename
    try:
        old_path.resolve().relative_to(MEDIA_GENERAL_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not old_path.exists() or not old_path.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    new_path = old_path.parent / new_name
    try:
        new_path.resolve().relative_to(MEDIA_GENERAL_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen uusi nimi"}), 400
    if new_path.exists():
        return jsonify({"error": "Samanniminen tiedosto on jo olemassa"}), 400
    old_path.rename(new_path)
    new_rel = new_path.relative_to(MEDIA_GENERAL_DIR).as_posix()
    data = load_playlist()
    old_src = f"/media_general/{old_filename}"
    for item in data.get("items", []):
        if item.get("src") == old_src:
            item["src"] = f"/media_general/{new_rel}"
            if item.get("name") == old_filename:
                item["name"] = new_rel
            save_playlist(data)
            break
    return jsonify({"ok": True, "new_filename": new_rel})


# -- Serve static/media files from external directories --------------------------


@app.route("/media/<path:filename>")
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)


@app.route("/media_general/<path:filename>")
def serve_media_general(filename):
    return send_from_directory(MEDIA_GENERAL_DIR, filename)


@app.route("/media_converted/<path:filename>")
def serve_media_converted(filename):
    return send_from_directory(CONVERTED_CACHE_DIR, filename)


@app.route("/media_guest/<path:filename>")
def serve_media_guest(filename):
    return send_from_directory(MEDIA_GUEST_DIR, filename)


@app.route("/media_favorites/<path:filename>")
def serve_media_favorites(filename):
    return send_from_directory(MEDIA_FAVORITES_DIR, filename)


# -- Guest media management -------------------------------------------------------


@app.route("/api/guest/list", methods=["GET"])
def api_guest_list():
    files = []
    for f in sorted(MEDIA_GUEST_DIR.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower().lstrip('.')
        if ext in ALLOWED_EXTENSIONS:
            ftype = "video" if ext == "mp4" else "image"
            rel = f.relative_to(MEDIA_GUEST_DIR).as_posix()
            entry_data = {
                "filename": rel,
                "src": f"/media_guest/{rel}",
                "type": ftype,
                "name": rel
            }
            if ftype == "video":
                entry_data["duration"] = get_video_duration(f)
            files.append(entry_data)
    response = jsonify(files)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/guest/upload", methods=["POST"])
def api_guest_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Ei tiedostoja"}), 400
    folder_raw = request.form.get("folder", "").strip()
    if not folder_raw:
        return jsonify({"error": "Kansion nimi puuttuu"}), 400
    folder_safe = re.sub(r'[^a-zA-Z0-9äöåÄÖÅ\s\-_.()]', '', folder_raw).strip()
    if not folder_safe or len(folder_safe) > 100:
        return jsonify({"error": "Kansion nimi ei kelpaa"}), 400
    target_dir = MEDIA_GUEST_DIR / folder_safe
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    skipped = 0
    errors = []
    for file in files:
        if not file.filename:
            continue
        original_name = Path(file.filename).name
        stem = Path(original_name).stem
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext == "zip":
            zip_data = io.BytesIO(file.read())
            try:
                with zipfile.ZipFile(zip_data, "r") as zf:
                    for zinfo in zf.infolist():
                        if zinfo.is_dir():
                            continue
                        zname = Path(zinfo.filename).name
                        zext = zname.rsplit(".", 1)[-1].lower() if "." in zname else ""
                        if zext not in ALLOWED_EXTENSIONS and zext not in CONVERT_EXTENSIONS:
                            continue
                        data = zf.read(zinfo)
                        target_ext = "mp4" if zext in CONVERT_EXTENSIONS else zext
                        zstem = Path(zname).stem
                        target_path = target_dir / f"{zstem}.{target_ext}"
                        if target_path.exists():
                            skipped += 1
                            continue
                        if zext in CONVERT_EXTENSIONS:
                            tmp_path = target_dir / f"{zstem}.{zext}"
                            tmp_path.write_bytes(data)
                            try:
                                convert_to_mp4(tmp_path)
                            except RuntimeError as e:
                                errors.append(f"{zname}: {e}")
                                continue
                        else:
                            target_path.write_bytes(data)
                        saved += 1
            except zipfile.BadZipFile:
                errors.append(f"{file.filename}: Virheellinen ZIP")
        elif ext in ALLOWED_EXTENSIONS:
            target_path = target_dir / original_name
            if target_path.exists():
                skipped += 1
            else:
                data = file.read()
                target_path.write_bytes(data)
                saved += 1
        elif ext in CONVERT_EXTENSIONS:
            target_path = target_dir / f"{stem}.mp4"
            if target_path.exists():
                skipped += 1
            else:
                data = file.read()
                tmp_path = target_dir / original_name
                tmp_path.write_bytes(data)
                try:
                    convert_to_mp4(tmp_path)
                    saved += 1
                except RuntimeError as e:
                    errors.append(f"{original_name}: {e}")
        else:
            errors.append(f"{original_name}: Ei-tuettu muoto")
    return jsonify({"saved": saved, "skipped": skipped, "errors": errors})


@app.route("/api/guest/delete-file", methods=["POST"])
def api_guest_delete_file():
    body = request.get_json()
    filename = (body.get("filename") or "").strip()
    if not filename:
        return jsonify({"error": "Tiedostonimi puuttuu"}), 400
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    filepath = MEDIA_GUEST_DIR / filename
    try:
        filepath.resolve().relative_to(MEDIA_GUEST_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    filepath.unlink()
    return jsonify({"ok": True})


@app.route("/api/guest/rename-file", methods=["POST"])
def api_guest_rename_file():
    body = request.get_json()
    old_filename = (body.get("filename") or "").strip()
    new_name = (body.get("new_name") or "").strip()
    if not old_filename or not new_name:
        return jsonify({"error": "Tiedostonimi tai uusi nimi puuttuu"}), 400
    if ".." in old_filename or old_filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if ".." in new_name or "/" in new_name or "\\" in new_name:
        return jsonify({"error": "Uusi nimi ei saa sisaltaa polkua"}), 400
    old_path = MEDIA_GUEST_DIR / old_filename
    try:
        old_path.resolve().relative_to(MEDIA_GUEST_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not old_path.exists() or not old_path.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    new_path = old_path.parent / new_name
    try:
        new_path.resolve().relative_to(MEDIA_GUEST_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen uusi nimi"}), 400
    if new_path.exists():
        return jsonify({"error": "Samanniminen tiedosto on jo olemassa"}), 400
    old_path.rename(new_path)
    return jsonify({"ok": True})


# -- Favorites media management ---------------------------------------------------


@app.route("/api/favorites/list", methods=["GET"])
def api_favorites_list():
    files = []
    for f in sorted(MEDIA_FAVORITES_DIR.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower().lstrip('.')
        if ext in ALLOWED_EXTENSIONS:
            ftype = "video" if ext == "mp4" else "image"
            rel = f.relative_to(MEDIA_FAVORITES_DIR).as_posix()
            entry_data = {
                "filename": rel,
                "src": f"/media_favorites/{rel}",
                "type": ftype,
                "name": rel
            }
            if ftype == "video":
                entry_data["duration"] = get_video_duration(f)
            files.append(entry_data)
    response = jsonify(files)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/favorites/add", methods=["POST"])
def api_favorites_add():
    body = request.get_json()
    src_path = (body.get("src") or "").strip()
    name = (body.get("name") or "").strip()
    if not src_path:
        return jsonify({"error": "Lähdetiedosto puuttuu"}), 400

    # Resolve the source file path from the src URL
    source_file = None
    if src_path.startswith("/media/"):
        fname = src_path.split("/")[-1]
        candidate = MEDIA_DIR / fname
        if candidate.exists():
            source_file = candidate
    elif src_path.startswith("/media_general/"):
        rel = src_path[len("/media_general/"):]
        candidate = MEDIA_GENERAL_DIR / rel
        if candidate.exists():
            source_file = candidate
    elif src_path.startswith("/media_guest/"):
        rel = src_path[len("/media_guest/"):]
        candidate = MEDIA_GUEST_DIR / rel
        if candidate.exists():
            source_file = candidate
    elif src_path.startswith("/api/external/file"):
        # External file - extract path from query string
        import urllib.parse
        parsed = urllib.parse.urlparse(src_path)
        qs = urllib.parse.parse_qs(parsed.query)
        ext_path = qs.get("path", [None])[0]
        if ext_path:
            candidate = Path(ext_path)
            if candidate.exists() and candidate.is_file():
                source_file = candidate

    if not source_file:
        return jsonify({"error": "Lähdetiedostoa ei löydy: " + src_path}), 404

    # Determine target name - use original filename, handle collisions
    target_name = source_file.name
    target_path = MEDIA_FAVORITES_DIR / target_name
    if target_path.exists():
        # Add a suffix to avoid collision
        stem = target_path.stem
        ext = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = MEDIA_FAVORITES_DIR / f"{stem}_{counter}{ext}"
            counter += 1

    shutil.copy2(str(source_file), str(target_path))
    rel = target_path.relative_to(MEDIA_FAVORITES_DIR).as_posix()
    return jsonify({"ok": True, "filename": rel, "copied_to": str(target_path)})


@app.route("/api/favorites/delete-file", methods=["POST"])
def api_favorites_delete_file():
    body = request.get_json()
    filename = (body.get("filename") or "").strip()
    if not filename:
        return jsonify({"error": "Tiedostonimi puuttuu"}), 400
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    filepath = MEDIA_FAVORITES_DIR / filename
    try:
        filepath.resolve().relative_to(MEDIA_FAVORITES_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    filepath.unlink()
    return jsonify({"ok": True})


@app.route("/api/favorites/rename-file", methods=["POST"])
def api_favorites_rename_file():
    body = request.get_json()
    old_filename = (body.get("filename") or "").strip()
    new_name = (body.get("new_name") or "").strip()
    if not old_filename or not new_name:
        return jsonify({"error": "Tiedostonimi tai uusi nimi puuttuu"}), 400
    if ".." in old_filename or old_filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if ".." in new_name or "/" in new_name or "\\" in new_name:
        return jsonify({"error": "Uusi nimi ei saa sisaltaa polkua"}), 400
    old_path = MEDIA_FAVORITES_DIR / old_filename
    try:
        old_path.resolve().relative_to(MEDIA_FAVORITES_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not old_path.exists() or not old_path.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    new_path = old_path.parent / new_name
    try:
        new_path.resolve().relative_to(MEDIA_FAVORITES_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen uusi nimi"}), 400
    if new_path.exists():
        return jsonify({"error": "Samanniminen tiedosto on jo olemassa"}), 400
    old_path.rename(new_path)
    return jsonify({"ok": True})


# -- External directory management ------------------------------------------------

@app.route("/api/external/list", methods=["GET"])
def api_external_list():
    data = load_playlist()
    response = jsonify({
        "dirs": data.get("external_dirs", []),
        "files": EXTERNAL_CACHE,
        "scanning": _SCANNING_EXTERNAL
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/external/add", methods=["POST"])
def api_external_add():
    data = load_playlist()
    body = request.get_json()
    dir_path = (body.get("path") or "").strip()
    if not dir_path:
        return jsonify({"error": "Polku puuttuu"}), 400
    dir_path = str(Path(dir_path))
    if any(d["path"] == dir_path for d in data.get("external_dirs", [])):
        return jsonify({"error": "Hakemisto on jo lisätty"}), 400
    label = (body.get("label") or "").strip()
    entry = {
        "id": uuid.uuid4().hex,
        "path": dir_path,
        "label": label,
        "enabled": True,
        "allow_delete": False
    }
    data.setdefault("external_dirs", []).append(entry)
    save_playlist(data)
    scan_external_dirs()
    return jsonify(entry)


@app.route("/api/external/<entry_id>", methods=["PATCH"])
def api_external_update(entry_id):
    if not HEX_RE.match(entry_id):
        return jsonify({"error": "Virheellinen id"}), 400
    data = load_playlist()
    for entry in data.get("external_dirs", []):
        if entry.get("id") == entry_id:
            if "enabled" in request.get_json():
                entry["enabled"] = bool(request.get_json()["enabled"])
            if "label" in request.get_json():
                entry["label"] = str(request.get_json()["label"])
            if "allow_delete" in request.get_json():
                entry["allow_delete"] = bool(request.get_json()["allow_delete"])
            save_playlist(data)
            scan_external_dirs()
            return jsonify(entry)
    return jsonify({"error": "Ei löydy"}), 404


@app.route("/api/external/<entry_id>", methods=["DELETE"])
def api_external_delete(entry_id):
    if not HEX_RE.match(entry_id):
        return jsonify({"error": "Virheellinen id"}), 400
    data = load_playlist()
    before = len(data.get("external_dirs", []))
    data["external_dirs"] = [d for d in data.get("external_dirs", []) if d.get("id") != entry_id]
    if len(data["external_dirs"]) == before:
        return jsonify({"error": "Ei löydy"}), 404
    save_playlist(data)
    scan_external_dirs()
    return jsonify({"ok": True})


@app.route("/api/external/refresh", methods=["POST"])
def api_external_refresh():
    scan_external_dirs()
    return jsonify({"ok": True, "count": len(EXTERNAL_CACHE)})


@app.route("/api/external/file", methods=["GET"])
def api_external_serve_file():
    file_path = (request.args.get("path") or "").strip()
    if not file_path:
        return jsonify({"error": "Polku puuttuu"}), 400
    requested = Path(file_path).resolve()
    data = load_playlist()
    for entry in data.get("external_dirs", []):
        if not entry.get("enabled", True):
            continue
        base = Path(entry["path"]).resolve()
        try:
            requested.relative_to(base)
        except ValueError:
            continue
        if requested.is_file():
            return send_file(str(requested))
    return jsonify({"error": "Tiedostoa ei löydy"}), 404


@app.route("/api/external/delete-file", methods=["POST"])
def api_external_delete_file():
    body = request.get_json()
    file_path = (body.get("path") or "").strip()
    if not file_path:
        return jsonify({"error": "Polku puuttuu"}), 400
    requested = Path(file_path).resolve()
    # Tarkista että tiedosto kuuluu rekisteröityyn ulkoiseen hakemistoon jossa sallittu poisto
    data = load_playlist()
    entry_found = None
    for entry in data.get("external_dirs", []):
        if not entry.get("enabled", True):
            continue
        base = Path(entry["path"]).resolve()
        try:
            requested.relative_to(base)
            entry_found = entry
            break
        except ValueError:
            continue
    if not entry_found:
        return jsonify({"error": "Tiedosto ei kuulu rekisteröityyn ulkoiseen hakemistoon"}), 403
    if not entry_found.get("allow_delete"):
        return jsonify({"error": "Poisto ei ole sallittu tälle hakemistolle"}), 403
    if not requested.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    # Poista myös konvertoitu välimuistitiedosto jos sellainen on
    src_key = hashlib.md5(str(requested.resolve()).encode("utf-8")).hexdigest()
    cache_map = _load_cache_map()
    cache_name = cache_map.pop(src_key, None)
    if cache_name:
        cache_path = CONVERTED_CACHE_DIR / cache_name
        cache_path.unlink(missing_ok=True)
        _save_cache_map(cache_map)
    requested.unlink()
    return jsonify({"ok": True})


# -- Android App upload API -------------------------------------------------------

@app.route("/api/android/ping", methods=["GET"])
def api_android_ping():
    """Lightweight ping that also returns the server IP so the Android app can verify connectivity."""
    ip = get_local_ip()
    return jsonify({"ok": True, "server_ip": ip, "port": PORT})


@app.route("/api/android/folders", methods=["GET"])
def api_android_folders():
    """List available folders under android_upload for destination selection."""
    folders = []
    try:
        for d in sorted(ANDROID_UPLOAD_DIR.rglob("*")):
            if d.is_dir():
                rel = d.relative_to(ANDROID_UPLOAD_DIR).as_posix()
                if rel == ".":
                    continue
                folders.append(rel)
    except OSError:
        pass
    return jsonify({"folders": folders, "root": str(ANDROID_UPLOAD_DIR)})


@app.route("/api/android/list", methods=["GET"])
def api_android_list():
    """List all media files under android_upload with tree structure."""
    files = []
    for f in sorted(ANDROID_UPLOAD_DIR.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower().lstrip('.')
        if ext not in ALLOWED_EXTENSIONS:
            continue
        ftype = "video" if ext == "mp4" else "image"
        rel = f.relative_to(ANDROID_UPLOAD_DIR).as_posix()
        entry = {
            "filename": rel,
            "src": f"/media_android/{rel}",
            "type": ftype,
            "name": rel,
            "size": f.stat().st_size
        }
        if ftype == "video":
            entry["duration"] = get_video_duration(f)
        files.append(entry)
    response = jsonify(files)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/android/upload", methods=["POST"])
def api_android_upload():
    """Receive file uploads from the Android app."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Ei tiedostoja"}), 400

    folder_raw = request.form.get("folder", "").strip()
    delete_after = request.form.get("delete_after", "false").lower() == "true"

    if folder_raw:
        folder_safe = re.sub(r'[^a-zA-Z0-9äöåÄÖÅ\s\-_.()]', '', folder_raw).strip()
        if not folder_safe or len(folder_safe) > 100:
            return jsonify({"error": "Kansion nimi ei kelpaa"}), 400
        target_dir = ANDROID_UPLOAD_DIR / folder_safe
    else:
        target_dir = ANDROID_UPLOAD_DIR

    target_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0
    errors = []
    for file in files:
        if not file.filename:
            continue
        original_name = Path(file.filename).name
        stem = Path(original_name).stem
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

        if ext in ALLOWED_EXTENSIONS:
            target_path = target_dir / original_name
            if target_path.exists():
                skipped += 1
            else:
                file.save(str(target_path))
                saved += 1
        elif ext in CONVERT_EXTENSIONS:
            target_path = target_dir / f"{stem}.mp4"
            if target_path.exists():
                skipped += 1
            else:
                tmp_path = target_dir / original_name
                file.save(str(tmp_path))
                try:
                    convert_to_mp4(tmp_path)
                    saved += 1
                except RuntimeError as e:
                    errors.append(f"{original_name}: {e}")
        else:
            errors.append(f"{original_name}: Ei-tuettu muoto")

    return jsonify({
        "saved": saved,
        "skipped": skipped,
        "errors": errors,
        "folder": folder_raw or "(root)",
        "delete_requested": delete_after
    })


@app.route("/api/android/delete-file", methods=["POST"])
def api_android_delete_file():
    """Delete a file from the android_upload directory."""
    body = request.get_json()
    filename = (body.get("filename") or "").strip()
    if not filename:
        return jsonify({"error": "Tiedostonimi puuttuu"}), 400
    if ".." in filename or filename.startswith("/"):
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    filepath = ANDROID_UPLOAD_DIR / filename
    try:
        filepath.resolve().relative_to(ANDROID_UPLOAD_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Virheellinen tiedostonimi"}), 400
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": "Tiedostoa ei loydy"}), 404
    filepath.unlink()
    return jsonify({"ok": True})


@app.route("/api/android/create-folder", methods=["POST"])
def api_android_create_folder():
    """Create a new folder under android_upload."""
    body = request.get_json()
    folder_name = (body.get("folder") or "").strip()
    if not folder_name:
        return jsonify({"error": "Kansion nimi puuttuu"}), 400
    folder_safe = re.sub(r'[^a-zA-Z0-9äöåÄÖÅ\s\-_.()]', '', folder_name).strip()
    if not folder_safe or len(folder_safe) > 100:
        return jsonify({"error": "Kansion nimi ei kelpaa"}), 400
    new_dir = ANDROID_UPLOAD_DIR / folder_safe
    if new_dir.exists():
        return jsonify({"error": "Kansio on jo olemassa"}), 400
    new_dir.mkdir(parents=True, exist_ok=True)
    return jsonify({"ok": True, "folder": folder_safe})


@app.route("/media_android/<path:filename>")
def serve_media_android(filename):
    """Serve files from the android_upload directory."""
    return send_from_directory(ANDROID_UPLOAD_DIR, filename)


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


if __name__ == "__main__":
    ip = get_local_ip()
    print(f"\n  Admin:   http://{ip}:{PORT}/adminloginhere  (latautuu -> /adminpanel)")
    print(f"  Guest:   http://{ip}:{PORT}/guest")
    print(f"  Näyttö:  http://{ip}:{PORT}/display")
    print(f"  Kuvat:   http://{ip}:{PORT}/img")
    print(f"  Videot:  http://{ip}:{PORT}/vid")
    print(f"  Suosikit: http://{ip}:{PORT}/fav")
    print(f"  Data:    {DATA_ROOT}")
    print(f"  Kuuntelu: {HOST}:{PORT}\n")
    # Käynnistä ulkoisten hakemistojen skannaus taustalla, jotta palvelin
    # alkaa kuunnella heti eikä jumita startupissa suurilla tiedostomäärillä.
    threading.Thread(target=scan_external_dirs, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False)
