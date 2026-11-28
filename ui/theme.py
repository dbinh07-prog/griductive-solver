"""Shared theme, typography, asset loaders, status visuals, and layout helpers."""
from dataclasses import dataclass
from pathlib import Path
import pygame

from contracts.models import Status


assets_dir = Path(__file__).resolve().parent.parent / "assets"
fonts_dir = assets_dir / "fonts"
sprites_dir = assets_dir / "sprites"
avatars_dir = sprites_dir / "avatars_png"
flip_sound_path = assets_dir / "sounds" / "flip.mp3"


@dataclass(frozen=True)
class ThemeColors:
    bg: tuple[int, int, int] = (244, 241, 234)
    panel_bg: tuple[int, int, int] = (252, 250, 246)
    panel_alt_bg: tuple[int, int, int] = (236, 232, 223)
    card_face_up: tuple[int, int, int] = (255, 254, 250)
    card_face_down: tuple[int, int, int] = (224, 220, 210)
    border: tuple[int, int, int] = (196, 189, 174)
    text: tuple[int, int, int] = (32, 36, 44)
    text_muted: tuple[int, int, int] = (100, 106, 118)
    accent: tuple[int, int, int] = (37, 99, 166)
    accent_hover: tuple[int, int, int] = (28, 78, 134)
    accent_text: tuple[int, int, int] = (255, 255, 255)
    criminal: tuple[int, int, int] = (178, 38, 46)
    criminal_bg: tuple[int, int, int] = (253, 236, 237)
    innocent: tuple[int, int, int] = (24, 125, 75)
    innocent_bg: tuple[int, int, int] = (233, 247, 239)
    sealed: tuple[int, int, int] = (92, 98, 110)
    sealed_bg: tuple[int, int, int] = (224, 220, 210)
    select_border: tuple[int, int, int] = (28, 92, 184)
    clue_border: tuple[int, int, int] = (212, 122, 18)
    clue_tint: tuple[int, int, int] = (255, 243, 220)
    secondary_border: tuple[int, int, int] = (128, 76, 168)
    overlap_border: tuple[int, int, int] = (18, 136, 142)
    hint_border: tuple[int, int, int] = (14, 132, 146)
    warn: tuple[int, int, int] = (184, 108, 12)
    error: tuple[int, int, int] = (176, 36, 44)
    button_bg: tuple[int, int, int] = (242, 239, 232)
    button_hover: tuple[int, int, int] = (228, 235, 244)
    button_disabled: tuple[int, int, int] = (232, 229, 222)
    button_active: tuple[int, int, int] = (37, 99, 166)


@dataclass(frozen=True)
class StatusVisual:
    label: str
    badge: str
    fg: tuple[int, int, int]
    bg: tuple[int, int, int]
    border: tuple[int, int, int]


@dataclass(frozen=True)
class LayoutRects:
    header: pygame.Rect
    toolbar: pygame.Rect
    evidence: pygame.Rect
    board: pygame.Rect
    inspector: pygame.Rect
    trace: pygame.Rect
    status_bar: pygame.Rect


THEME = ThemeColors()
_AVATAR_PALETTE: tuple[tuple[int, int, int], ...] = (
    (66, 105, 148),
    (138, 86, 62),
    (64, 122, 98),
    (122, 82, 142),
    (156, 108, 52),
    (74, 114, 126),
)
font_cache: dict[tuple[int, bool, bool], pygame.font.Font] = {}
avatar_paths_cache: dict[Path | None, tuple[Path, ...]] = {}
avatar_raw_cache: dict[Path, pygame.Surface] = {}
avatar_scaled_cache: dict[tuple[Path, int], pygame.Surface] = {}
sound_cache: dict[Path, pygame.mixer.Sound] = {}


def reset_runtime_caches() -> None:
    """Drop SDL resources before shutdown/reinitialization of the application."""
    font_cache.clear()
    sound_cache.clear()
    avatar_raw_cache.clear()
    avatar_scaled_cache.clear()
mixer_failed = False


def _find_custom_font(bold: bool, mono: bool) -> Path | None:
    if mono:
        name = "JetBrainsMono-Regular.ttf"
    elif bold:
        name = "Inter-Bold.ttf"
    else:
        name = "Inter-Regular.ttf"
    path = fonts_dir / name
    return path if path.is_file() else None


def get_font(size: int, *, bold: bool = False, mono: bool = False) -> pygame.font.Font:
    """Return a cached bundled font with safe fallback to Pygame's default font."""
    if not pygame.font.get_init():
        pygame.font.init()
        font_cache.clear()
    key = (max(8, size), bold, mono)
    cached = font_cache.get(key)
    if cached is not None:
        return cached

    custom_path = _find_custom_font(bold, mono)
    try:
        font = pygame.font.Font(str(custom_path) if custom_path is not None else None, key[0])
        if bold and (custom_path is None or custom_path.name != "Inter-Bold.ttf"):
            font.set_bold(True)
    except (pygame.error, OSError):
        font = pygame.font.Font(None, key[0])
        font.set_bold(bold)

    font_cache[key] = font
    return font


def status_visual(status: Status | None) -> StatusVisual:
    """Return accessible label, ASCII badge, and colors for a card status."""
    if status == Status.CRIMINAL:
        return StatusVisual("CRIMINAL", "[!]", THEME.criminal, THEME.criminal_bg, THEME.criminal)
    if status == Status.INNOCENT:
        return StatusVisual("INNOCENT", "[OK]", THEME.innocent, THEME.innocent_bg, THEME.innocent)
    return StatusVisual("SEALED", "[?]", THEME.sealed, THEME.sealed_bg, THEME.border)


def draw_status_icon(
    surface: pygame.Surface,
    status: Status | None,
    rect: pygame.Rect,
    color: tuple[int, int, int],
) -> None:
    """Draw a vector status symbol directly with pygame.draw to avoid missing glyphs."""
    if rect.width < 4 or rect.height < 4:
        return
    cx, cy = rect.center
    r = max(3, min(rect.width, rect.height) // 2 - 2)

    if status == Status.CRIMINAL:
        pts = [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)]
        pygame.draw.polygon(surface, color, pts, 2)
        pygame.draw.line(surface, color, (cx, cy - r // 2 + 1), (cx, cy + r // 3), 2)
        pygame.draw.circle(surface, color, (cx, cy + r - 3), 1)
        return

    if status == Status.INNOCENT:
        pygame.draw.circle(surface, color, (cx, cy), r, 2)
        check = [
            (cx - r // 2, cy),
            (cx - r // 8, cy + r // 2 - 1),
            (cx + r // 2 + 1, cy - r // 3),
        ]
        pygame.draw.lines(surface, color, False, check, 2)
        return

    body = pygame.Rect(cx - r + 2, cy - 1, (r - 2) * 2, r + 1)
    pygame.draw.rect(surface, color, body, 2, border_radius=2)
    shackle = pygame.Rect(cx - r // 2, cy - r + 1, r, r)
    pygame.draw.arc(surface, color, shackle, 0.0, 3.14159, 2)


def list_avatar_paths(sprites_dir: Path | None = None) -> tuple[Path, ...]:
    """Return sorted avatar PNG paths, checking avatars_png/ before sprites/."""
    cache_key = None if sprites_dir is None else sprites_dir.resolve()
    cached = avatar_paths_cache.get(cache_key)
    if cached is not None:
        return cached

    search_dirs = (
        (avatars_dir, globals()["sprites_dir"])
        if sprites_dir is None
        else (sprites_dir / "avatars_png", sprites_dir)
    )
    result: tuple[Path, ...] = ()
    for folder in search_dirs:
        if not folder.is_dir():
            continue
        pngs = sorted(
            (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".png"),
            key=lambda p: p.name.lower(),
        )
        if pngs:
            result = tuple(pngs)
            break

    avatar_paths_cache[cache_key] = result
    return result


def get_avatar_surface(
    char_index: int,
    size: int,
    *,
    sprites_dir: Path | None = None,
) -> pygame.Surface | None:
    """Load, scale, and cache an avatar surface mapped deterministically by character index."""
    if size <= 0:
        return None
    paths = list_avatar_paths(sprites_dir)
    if not paths:
        return None

    path = paths[char_index % len(paths)]
    key = (path, size)
    cached = avatar_scaled_cache.get(key)
    if cached is not None:
        return cached

    raw = avatar_raw_cache.get(path)
    if raw is None:
        try:
            loaded = pygame.image.load(str(path))
            # convert_alpha requires an initialized display surface; skip in pure Surface tests.
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                loaded = loaded.convert_alpha()
        except (pygame.error, OSError):
            return None
        avatar_raw_cache[path] = loaded
        raw = loaded

    try:
        if raw.get_bitsize() in (24, 32):
            scaled = pygame.transform.smoothscale(raw, (size, size))
        else:
            scaled = pygame.transform.scale(raw, (size, size))
    except (pygame.error, ValueError):
        scaled = pygame.transform.scale(raw, (size, size))

    avatar_scaled_cache[key] = scaled
    return scaled


def _ascii_initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    letters = []
    for part in parts[:2]:
        ch = next((c.upper() for c in part if c.isascii() and c.isalnum()), "")
        if ch:
            letters.append(ch)
    if letters:
        return "".join(letters)
    raw = [c.upper() for c in name if c.isascii() and c.isalnum()]
    return "".join(raw[:2]) or "?"


def draw_avatar_fallback(
    surface: pygame.Surface,
    rect: pygame.Rect,
    name: str,
    index: int = 0,
) -> None:
    """Draw a deterministic colored avatar circle with ASCII initials when sprites fail."""
    if rect.width < 4 or rect.height < 4:
        return
    radius = max(4, min(rect.width, rect.height) // 2)
    fill = _AVATAR_PALETTE[index % len(_AVATAR_PALETTE)]
    pygame.draw.circle(surface, fill, rect.center, radius)
    pygame.draw.circle(surface, THEME.border, rect.center, radius, 1)

    initials = _ascii_initials(name)
    font = get_font(max(9, int(radius * 0.9)), bold=True)
    txt = font.render(initials, True, THEME.accent_text)
    surface.blit(txt, txt.get_rect(center=rect.center))


def play_flip_sound(*, muted: bool = False, sound_path: Path | None = None) -> bool:
    """Lazily initialize pygame.mixer and play the card-flip sound without failing headless."""
    global mixer_failed
    if muted or mixer_failed:
        return False
    target = sound_path or flip_sound_path
    if not target.is_file():
        return False

    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
            sound_cache.clear()
        except (pygame.error, NotImplementedError, OSError):
            mixer_failed = True
            return False

    try:
        sound = sound_cache.get(target)
        if sound is None:
            sound = pygame.mixer.Sound(str(target))
            sound_cache[target] = sound
        sound.play()
        return True
    except (pygame.error, NotImplementedError, OSError):
        return False


def compute_game_layout(width: int, height: int) -> LayoutRects:
    """Compute non-overlapping panel rectangles for the main game screen."""
    w = max(640, width)
    h = max(480, height)
    pad = 10
    gap = 8
    header_h = 40
    toolbar_h = 40
    status_h = 26

    inner_w = w - pad * 2
    usable_h = max(220, h - pad * 2 - header_h - toolbar_h - status_h - gap * 4)
    trace_h = max(136, min(200, int(usable_h * 0.30)))
    mid_h = usable_h - trace_h

    avail_mid_w = inner_w - gap * 2
    left_w = max(170, min(280, int(avail_mid_w * 0.24)))
    right_w = max(200, min(300, int(avail_mid_w * 0.26)))
    center_w = avail_mid_w - left_w - right_w
    if center_w < 260:
        side_budget = max(240, avail_mid_w - 260)
        left_w = side_budget // 2
        right_w = side_budget - left_w
        center_w = avail_mid_w - left_w - right_w

    y = pad
    header = pygame.Rect(pad, y, inner_w, header_h)
    y += header_h + gap
    toolbar = pygame.Rect(pad, y, inner_w, toolbar_h)
    y += toolbar_h + gap
    evidence = pygame.Rect(pad, y, left_w, mid_h)
    board = pygame.Rect(pad + left_w + gap, y, center_w, mid_h)
    inspector = pygame.Rect(pad + left_w + gap + center_w + gap, y, right_w, mid_h)
    y += mid_h + gap
    trace = pygame.Rect(pad, y, inner_w, trace_h)
    y += trace_h + gap
    status_bar = pygame.Rect(pad, y, inner_w, status_h)

    return LayoutRects(
        header=header,
        toolbar=toolbar,
        evidence=evidence,
        board=board,
        inspector=inspector,
        trace=trace,
        status_bar=status_bar,
    )


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Wrap text into lines that fit within max_width pixels."""
    if not text:
        return [""]
    if max_width <= 8:
        return text.splitlines() or [""]

    lines: list[str] = []
    for raw_line in text.splitlines():
        words = raw_line.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if font.size(word)[0] <= max_width:
                current = word
                continue
            chunk = ""
            for ch in word:
                if chunk and font.size(chunk + ch)[0] > max_width:
                    lines.append(chunk)
                    chunk = ch
                else:
                    chunk += ch
            current = chunk
        lines.append(current)
    return lines or [""]


def truncate_text(text: str, font: pygame.font.Font, max_width: int) -> str:
    """Truncate text with an ASCII ellipsis so it fits within max_width pixels."""
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    if font.size(ellipsis)[0] >= max_width:
        return ""
    end = len(text)
    while end > 0 and font.size(text[:end] + ellipsis)[0] > max_width:
        end -= 1
    return text[:end] + ellipsis
