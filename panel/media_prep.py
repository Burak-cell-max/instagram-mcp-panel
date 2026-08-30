"""Fit an uploaded image to an Instagram-legal aspect ratio without cropping.

Instagram rejects feed images outside 4:5 (0.8) .. 1.91:1 and wants stories/reels
at 9:16. Rather than force every upload into a square, we keep the image whole and
pad the short axis with a blurred, zoomed copy of the image itself (the familiar
"blurred bars" look), so a portrait, a wide banner or an odd screenshot all publish.

An image already within range is returned untouched.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

FEED_MIN, FEED_MAX = 0.8, 1.91          # width / height
STORY_RATIO = 1080 / 1920               # 9:16
_MAX_LONG_SIDE = 1920
_JPEG_Q = 90


def _load(src: Path) -> Image.Image:
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)      # honour phone rotation
    if im.mode not in ("RGB",):
        im = im.convert("RGB")
    return im


def _blurred_canvas(im: Image.Image, cw: int, ch: int) -> Image.Image:
    """A cw x ch background: the image scaled to *cover*, then blurred."""
    scale = max(cw / im.width, ch / im.height)
    bg = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    left = (bg.width - cw) // 2
    top = (bg.height - ch) // 2
    bg = bg.crop((left, top, left + cw, top + ch))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=max(cw, ch) // 40))
    return Image.blend(bg, Image.new("RGB", (cw, ch), (18, 18, 20)), 0.25)


def fit(src: Path, *, mode: str = "feed", target_ratio: float | None = None) -> Path:
    """Return a path to an image whose aspect ratio Instagram will accept.

    mode="feed": clamp to 0.8..1.91 (or to `target_ratio` when given, e.g. to make a
    carousel uniform). mode="story": pad to 9:16. Returns `src` unchanged when it
    already fits and no explicit target is forced.
    """
    im = _load(src)
    w, h = im.size
    ratio = w / h

    if mode == "story":
        target = STORY_RATIO
    elif target_ratio is not None:
        target = target_ratio
    elif FEED_MIN <= ratio <= FEED_MAX:
        if max(w, h) <= _MAX_LONG_SIDE:
            return src
        target = ratio
    else:
        target = min(FEED_MAX, max(FEED_MIN, ratio))

    # canvas that contains the whole image at `target`
    if ratio > target:                    # too wide -> add height
        cw = w
        ch = round(w / target)
    else:                                 # too tall -> add width
        ch = h
        cw = round(h * target)

    if max(cw, ch) > _MAX_LONG_SIDE:
        s = _MAX_LONG_SIDE / max(cw, ch)
        cw, ch = round(cw * s), round(ch * s)
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)

    canvas = _blurred_canvas(im, cw, ch)
    canvas.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))

    out = src.with_name(f"{src.stem}_ig.jpg")
    canvas.save(out, "JPEG", quality=_JPEG_Q)
    return out


def ratio_of(src: Path) -> float:
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    return im.width / im.height


def feed_fits(src: Path) -> bool:
    return FEED_MIN <= ratio_of(src) <= FEED_MAX
