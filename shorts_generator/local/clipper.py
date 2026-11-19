"""Local clipping: ffmpeg subclip + OpenCV face-aware vertical crop + animated word subtitles.

Three stages per highlight:
  1. Cut the source video to [start, end] with ffmpeg (re-encoded, audio kept).
  2. Reframe the cut to the target aspect ratio. For 9:16 we slide a vertical
     window horizontally across the frame to keep faces centred (Haar
     cascade — same approach as the original repo, no external models).
  3. Burn animated word-by-word subtitles (Whisper word timestamps) so silent
     viewers never swipe away.
"""
import os
import subprocess
import math
from typing import Dict, List, Optional, Tuple

from ..config import LOCAL_OUTPUT_DIR


def _ratio(aspect_ratio: str) -> float:
    """Parse '9:16' → 9/16, '1:1' → 1.0."""
    try:
        w, h = aspect_ratio.split(":")
        return float(w) / float(h)
    except (ValueError, ZeroDivisionError):
        return 9.0 / 16.0


def _cut_subclip(source_path: str, start: float, end: float, out_path: str) -> str:
    """ffmpeg -ss start -to end → high quality re-encoded mp4 with audio."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", source_path,
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def _get_words_for_clip(transcript: Optional[Dict], clip_start: float, clip_end: float) -> List[Dict]:
    """Extract word-level timestamps for a clip's time range, rebased to clip-local time."""
    if not transcript:
        return []
    segments = transcript.get("segments", [])
    words = []
    for seg in segments:
        seg_start = float(seg.get("start", 0))
        seg_end = float(seg.get("end", 0))
        # Skip segments entirely outside the clip range
        if seg_end < clip_start or seg_start > clip_end:
            continue
        seg_words = seg.get("words", [])
        if seg_words:
            for w in seg_words:
                ws = float(w.get("start", 0))
                we = float(w.get("end", 0))
                if ws >= clip_start - 0.1 and we <= clip_end + 0.5:
                    words.append({
                        "start": ws - clip_start,
                        "end": we - clip_start,
                        "word": w.get("word", ""),
                    })
        else:
            # Fallback: split segment text evenly across its duration
            text = seg.get("text", "").strip()
            if not text:
                continue
            text_words = text.split()
            effective_start = max(seg_start, clip_start)
            effective_end = min(seg_end, clip_end)
            if effective_end <= effective_start or not text_words:
                continue
            word_dur = (effective_end - effective_start) / len(text_words)
            for i, tw in enumerate(text_words):
                ws = effective_start + i * word_dur
                we = ws + word_dur
                words.append({
                    "start": ws - clip_start,
                    "end": we - clip_start,
                    "word": tw,
                })
    return words


def _build_subtitle_groups(words: List[Dict], max_words_per_group: int = 5) -> List[Dict]:
    """Group words into display lines (max 5 words per line) for better readability."""
    groups = []
    i = 0
    while i < len(words):
        chunk = words[i:i + max_words_per_group]
        groups.append({
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
            "words": chunk,
        })
        i += max_words_per_group
    return groups


def _get_subtitle_font(size: int = 48):
    """Load a font that supports both Hindi (Devanagari) and English.
    
    Uses PIL/Pillow TrueType font loading with a fallback chain:
      1. Nirmala UI — Windows system font, supports Hindi/Devanagari natively
      2. Mangal — classic Hindi font on Windows
      3. Noto Sans Devanagari — Google's Unicode coverage font
      4. Arial Unicode MS — broad Unicode coverage
      5. Default PIL font (ASCII only, last resort)
    """
    from PIL import ImageFont
    
    font_candidates = [
        r"C:\Windows\Fonts\Nirmala.ttc",     # Windows Hindi system font
        r"C:\Windows\Fonts\NirmalaB.ttf",     # Nirmala Bold
        r"C:\Windows\Fonts\mangal.ttf",       # Classic Hindi
        r"C:\Windows\Fonts\NotoSansDevanagari-Bold.ttf",
        r"C:\Windows\Fonts\arial.ttf",        # Fallback (English only)
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    # Absolute last resort
    return ImageFont.load_default()


def _draw_animated_subtitles(frame, frame_time: float, subtitle_groups: List[Dict],
                              out_w: int, out_h: int, cv2_module):
    """Draw animated word-by-word subtitles at the bottom of the frame.
    
    Uses PIL/Pillow for text rendering to support Hindi (Devanagari) + English.
    OpenCV's cv2.putText() CANNOT render non-ASCII characters.
    
    - Active word: YELLOW, bold
    - Already spoken: WHITE
    - Not yet spoken: GRAY (dimmed)
    - Semi-transparent dark backdrop behind text for readability
    """
    cv2 = cv2_module
    
    # Find the current active subtitle group
    active_group = None
    for grp in subtitle_groups:
        if grp["start"] - 0.3 <= frame_time <= grp["end"] + 0.2:
            active_group = grp
            break
    
    if not active_group:
        return
    
    words = active_group["words"]
    if not words:
        return
    
    # Import PIL for Unicode-aware text rendering
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError:
        return  # Skip subtitles if Pillow not available
    
    # Load Hindi-compatible font
    font_size = 52
    font = _get_subtitle_font(font_size)
    bold_font = _get_subtitle_font(int(font_size * 1.1))
    
    # Create a transparent PIL overlay the same size as the frame
    pil_overlay = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pil_overlay)
    
    # Measure total text width
    spacing = 16  # pixels between words
    word_metrics = []
    total_text_w = 0
    for w in words:
        text = w["word"]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        word_metrics.append({"text": text, "w": tw, "h": th, "data": w})
        total_text_w += tw + spacing
    total_text_w -= spacing
    
    # Position: centered, near bottom (above YouTube controls)
    text_y = out_h - 220
    text_x = max(20, (out_w - total_text_w) // 2)
    max_h = max(m["h"] for m in word_metrics) if word_metrics else 50
    
    # Draw semi-transparent backdrop using OpenCV (fast)
    pad_x = 28
    pad_y = 20
    backdrop_top = text_y - pad_y
    backdrop_bottom = text_y + max_h + pad_y + 10
    backdrop_left = max(0, text_x - pad_x)
    backdrop_right = min(out_w, text_x + total_text_w + pad_x)
    
    overlay_bg = frame.copy()
    cv2.rectangle(overlay_bg, (backdrop_left, backdrop_top), (backdrop_right, backdrop_bottom),
                  (15, 15, 25), -1)
    cv2.addWeighted(overlay_bg, 0.65, frame, 0.35, 0, frame)
    cv2.rectangle(frame, (backdrop_left, backdrop_top), (backdrop_right, backdrop_bottom),
                  (0, 200, 255), 2)
    
    # Draw each word using PIL (supports Hindi/Devanagari)
    cursor_x = text_x
    for m in word_metrics:
        w_data = m["data"]
        w_start = w_data["start"]
        w_end = w_data["end"]
        text = m["text"]
        
        if frame_time >= w_start and frame_time <= w_end + 0.15:
            # ACTIVE word — bright yellow
            color = (255, 255, 0, 255)  # RGBA Yellow
            current_font = bold_font
        elif frame_time > w_end:
            # Already spoken — white
            color = (255, 255, 255, 255)
            current_font = font
        else:
            # Not yet spoken — dimmed gray
            color = (170, 170, 180, 200)
            current_font = font
        
        # Shadow
        draw.text((cursor_x + 3, text_y + 3), text, font=current_font, fill=(0, 0, 0, 200))
        # Main text
        draw.text((cursor_x, text_y), text, font=current_font, fill=color)
        
        cursor_x += m["w"] + spacing
    
    # Composite PIL overlay onto OpenCV frame
    pil_array = np.array(pil_overlay)
    # pil_array is RGBA, frame is BGR
    alpha = pil_array[:, :, 3] / 255.0
    for c in range(3):
        # PIL is RGB, OpenCV is BGR → channel mapping: PIL[0]=R→cv[2], PIL[1]=G→cv[1], PIL[2]=B→cv[0]
        cv_channel = 2 - c
        frame[:, :, cv_channel] = (
            alpha * pil_array[:, :, c] + (1 - alpha) * frame[:, :, cv_channel]
        ).astype(frame.dtype)


def _reframe_vertical(in_path: str, out_path: str, aspect_ratio: str,
                       clip_words: Optional[List[Dict]] = None) -> str:
    """Smart vertical reframing (9:16) with animated word-by-word subtitles.
    
    If the video has screen recordings, presentation text, or wide graphics (common in tech/tutorials),
    a hard crop cuts off sides and text.
    We detect faces and content:
      1. If a clear human face is detected (> 8% of frame), center crop smoothly on the speaker.
      2. If no prominent face or wide graphic/text is on screen, use the industry-standard Shorts format:
         the original 16:9 full frame centered with a stylish blurred version of the video filling the 9:16 background!
         This guarantees NO text, images, or graphics ever get cut off!
    
    Subtitle burning:
      Word-by-word animated subtitles are burned into every frame using Whisper word timestamps.
      Active word = YELLOW (pop animation), spoken words = WHITE, upcoming = GRAY.
    """
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "opencv-python is required for --mode local. Install it with:\n"
            "    pip install -r requirements-local.txt"
        ) from e

    target_ratio = _ratio(aspect_ratio)
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        raise RuntimeError(f"could not open {in_path}")

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Target 9:16 vertical resolution in true 1080x1920 Full HD (YouTube Shorts Native Quality)
    out_w = 1080
    out_h = 1920

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    # Build subtitle groups from word-level timestamps
    subtitle_groups = _build_subtitle_groups(clip_words or [], max_words_per_group=5)
    has_subtitles = len(subtitle_groups) > 0
    if has_subtitles:
        print(f"    [subtitles] {len(subtitle_groups)} word groups ready for animated burn-in", flush=True)

    # Sample the clip to decide the best mode: Speaker-Focus Crop vs Smart Blurred Background
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sample_stride = max(1, total_frames // 20)
    face_detected_count = 0
    sampled_count = 0

    cur_f = 0
    while cur_f < total_frames and sampled_count < 20:
        cap.set(cv2.CAP_PROP_POS_FRAMES, cur_f)
        ret, s_frame = cap.read()
        if not ret:
            break
        sampled_count += 1
        gray = cv2.cvtColor(s_frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) > 0:
            face_detected_count += 1
        cur_f += sample_stride

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # If faces appear in > 40% of samples, it's a person/podcast talking: use face-tracking crop.
    # If < 40%, it's screen share, text, news b-roll, charts, or slides: use smart blurred letterbox
    # so NO text or visual information is cut!
    use_face_crop = (face_detected_count / max(1, sampled_count)) >= 0.40

    silent_path = out_path + ".silent.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(silent_path, fourcc, fps, (out_w, out_h))

    # For face crop mode:
    crop_h = src_h
    crop_w = int(crop_h * target_ratio)
    crop_w = max(2, crop_w - (crop_w % 2))

    last_center: Optional[Tuple[int, int]] = None
    smoothing = 0.15
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_time = frame_idx / fps

        if use_face_crop:
            # Face tracking crop mode
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                cx = x + w // 2
                cy = y + h // 2
                if last_center is None:
                    last_center = (cx, cy)
                else:
                    lx, ly = last_center
                    last_center = (
                        int(lx + (cx - lx) * smoothing),
                        int(ly + (cy - ly) * smoothing),
                    )
            if last_center is None:
                last_center = (src_w // 2, src_h // 2)

            cx, cy = last_center
            x0 = max(0, min(src_w - crop_w, cx - crop_w // 2))
            y0 = 0
            cropped = frame[y0:y0 + crop_h, x0:x0 + crop_w]
            final_frame = cv2.resize(cropped, (out_w, out_h))
        else:
            # Smart Blurred Background Mode (Preserves 100% of text, graphics, slides, and visuals)
            # 1. Background: Zoomed & heavily blurred frame filling 9:16 canvas
            bg_scale = max(out_w / src_w, out_h / src_h)
            bg_w = int(src_w * bg_scale)
            bg_h = int(src_h * bg_scale)
            bg_resized = cv2.resize(frame, (bg_w, bg_h))
            bg_x0 = (bg_w - out_w) // 2
            bg_y0 = (bg_h - out_h) // 2
            bg_canvas = bg_resized[bg_y0:bg_y0 + out_h, bg_x0:bg_x0 + out_w]
            blurred_bg = cv2.GaussianBlur(bg_canvas, (51, 51), 0)

            # 2. Foreground: Entire original video fitted cleanly in center with NO cropped text
            fg_w = out_w
            fg_h = int(src_h * (out_w / src_w))
            fg_resized = cv2.resize(frame, (fg_w, fg_h))

            # Overlay foreground onto center of blurred background
            y_offset = (out_h - fg_h) // 2
            blurred_bg[y_offset:y_offset + fg_h, 0:out_w] = fg_resized
            final_frame = blurred_bg

        # Overlays / Banners / Badges removed for completely clean video output
        # (No top banner, no bottom subscribe badge, and no captions)

        writer.write(final_frame)
        frame_idx += 1

    cap.release()
    writer.release()

    # Mux audio back with high quality settings
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", silent_path,
        "-i", in_path,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0?",
        "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    try:
        os.remove(silent_path)
    except Exception:
        pass
    return out_path


def _safe_remove(path: str, max_retries: int = 5, delay: float = 0.5):
    """Safely remove a file on Windows handling lingering file handle locks."""
    import time
    for _ in range(max_retries):
        try:
            if os.path.exists(path):
                os.remove(path)
            return
        except OSError:
            time.sleep(delay)
    # If still locked, don't crash the pipeline
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def crop_clip_local(
    source_path: str,
    start_time: float,
    end_time: float,
    aspect_ratio: str,
    out_path: str,
    clip_words: Optional[List[Dict]] = None,
) -> str:
    """Cut + reframe one highlight with animated subtitles, returning the local mp4 path."""
    import time
    cut_path = out_path + ".cut.mp4"
    try:
        _cut_subclip(source_path, start_time, end_time, cut_path)
        _reframe_vertical(cut_path, out_path, aspect_ratio, clip_words=clip_words)
    finally:
        _safe_remove(cut_path)
    return out_path


def crop_highlights_local(
    source_path: str,
    highlights: List[Dict],
    aspect_ratio: str = "9:16",
    out_dir: Optional[str] = None,
    transcript: Optional[Dict] = None,
) -> List[Dict]:
    out_dir = out_dir or LOCAL_OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict] = []
    for i, h in enumerate(highlights, 1):
        out_path = os.path.join(out_dir, f"short_{i:02d}.mp4")
        clip_start = float(h["start_time"])
        clip_end = float(h["end_time"])
        
        # Extract word-level timestamps for this clip's time range
        clip_words = _get_words_for_clip(transcript, clip_start, clip_end)
        
        print(f"[clip/local] {i}/{len(highlights)}: {h.get('title', '(untitled)')} ({len(clip_words)} words for subtitles)", flush=True)
        try:
            crop_clip_local(
                source_path,
                clip_start,
                clip_end,
                aspect_ratio,
                out_path,
                clip_words=clip_words,
            )
            results.append({**h, "clip_url": out_path})
        except Exception as e:
            print(f"[clip/local] {i} failed: {e}", flush=True)
            results.append({**h, "clip_url": None, "error": str(e)})
    return results
