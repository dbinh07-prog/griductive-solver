"""Case selection scene listing puzzle files without parsing private JSON contents."""
from dataclasses import dataclass
from pathlib import Path
import re
import pygame

from scenes.base_scene import BaseScene, UIButton
from ui.theme import THEME, draw_avatar_fallback, get_avatar_surface, get_font, truncate_text, wrap_text
from ui.file_dialogs import choose_file


_SIZE_PATTERN = re.compile(r"\b(\d+)\s*[xX]\s*(\d+)\b")
_PIN_NAMES: tuple[str, ...] = ("Eliza", "Franz", "Grant", "Hannah", "Ivy", "Jonas", "Karl", "Leo")
_PIN_TINTS: tuple[tuple[int, int, int], ...] = (
    THEME.panel_bg,
    THEME.innocent_bg,
    THEME.card_face_down,
    THEME.criminal_bg,
)


def _format_case_label(stem: str) -> str:
    words = [w for w in stem.replace("-", "_").split("_") if w]
    formatted: list[str] = []
    for word in words:
        match = _SIZE_PATTERN.fullmatch(word)
        if match:
            formatted.append(f"{match.group(1)}x{match.group(2)}")
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted) or stem


def _detect_size_tag(stem: str) -> str:
    match = _SIZE_PATTERN.search(stem.replace("_", " "))
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    return ""


@dataclass(frozen=True)
class CaseEntry:
    path: str
    label: str
    group: str


class CaseSelectScene(BaseScene):
    """Browse built-in puzzle JSON paths or pick one from disk."""

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self._size = (1280, 720)
        self.cases: list[CaseEntry] = []
        self._scroll_y = 0
        self._max_scroll = 0
        self._dragging_scrollbar = False
        self._drag_offset_y = 0
        self._local_error = ""

        self._list_rect = pygame.Rect(40, 96, 800, 420)
        self._track_rect = pygame.Rect(0, 0, 0, 0)
        self._thumb_rect = pygame.Rect(0, 0, 0, 0)
        self._row_rects: list[tuple[pygame.Rect, CaseEntry]] = []
        self._btn_load: UIButton | None = None
        self._btn_back: UIButton | None = None
        self._pin_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._pin_tile_sz = 0

    def on_enter(self) -> None:
        self._local_error = ""
        self.refresh_cases()
        self._rebuild_layout()

    def on_resize(self, width: int, height: int) -> None:
        self._size = (max(640, width), max(480, height))
        self._rebuild_layout()

    def refresh_cases(self) -> None:
        root = Path(__file__).resolve().parent.parent / "puzzles"
        if not root.is_dir():
            root = Path("puzzles")

        entries: list[CaseEntry] = []
        for folder_name, group in (("examples", "Examples"), ("benchmark", "Benchmark")):
            folder = root / folder_name
            if not folder.is_dir():
                continue
            for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if path.is_file() and path.suffix.lower() == ".json":
                    pretty = _format_case_label(path.stem)
                    entries.append(CaseEntry(path=str(path), label=f"{pretty} ({path.name})", group=group))
        self.cases = entries
        self._scroll_y = 0

    def open_file_dialog(self) -> None:
        selected = ""
        try:
            selected = choose_file(
                "Select Puzzle JSON", [("JSON files", "*.json"), ("All files", "*.*")]
            )
        except Exception as exc:
            self._local_error = f"File dialog unavailable in current environment: {exc}"
            return

        if selected:
            self._local_error = ""
            self.controller.load_case(selected)

    def _rebuild_layout(self) -> None:
        w, h = self._size
        pad = 24
        panel_w = min(900, max(540, w - pad * 2))
        panel_x = (w - panel_w) // 2

        self._btn_back = UIButton(
            pygame.Rect(panel_x, pad, 96, 38),
            "Back",
            self.controller.show_menu,
            tooltip="Return to main menu",
        )
        self._btn_load = UIButton(
            pygame.Rect(panel_x + panel_w - 152, pad, 152, 38),
            "Load JSON...",
            self.open_file_dialog,
            active=True,
            tooltip="Browse for a puzzle JSON file",
        )
        list_top = pad + 58
        list_h = max(180, h - list_top - 74)
        self._list_rect = pygame.Rect(panel_x, list_top, panel_w, list_h)

    def _get_pinned_card(self, char_index: int, tile_sz: int, angle_deg: int) -> pygame.Surface:
        if tile_sz != self._pin_tile_sz:
            self._pin_cache.clear()
            self._pin_tile_sz = tile_sz

        key = (char_index, tile_sz, angle_deg)
        cached = self._pin_cache.get(key)
        if cached is not None:
            return cached

        card = pygame.Surface((tile_sz, tile_sz + 8), pygame.SRCALPHA)
        body = pygame.Rect(0, 6, tile_sz, tile_sz)
        tint = _PIN_TINTS[char_index % len(_PIN_TINTS)]
        pygame.draw.rect(card, tint, body, border_radius=10)
        pygame.draw.rect(card, THEME.border, body, 1, border_radius=10)

        av_sz = max(20, tile_sz - 18)
        av_rect = pygame.Rect(0, 0, av_sz, av_sz)
        av_rect.center = (body.centerx, body.centery + 2)
        av_surf = get_avatar_surface(char_index, av_sz)
        if av_surf is not None:
            card.blit(av_surf, av_rect)
        else:
            draw_avatar_fallback(card, av_rect, _PIN_NAMES[char_index % len(_PIN_NAMES)], char_index)

        pin_color = THEME.criminal if char_index % 2 == 0 else THEME.accent
        pin_pos = (tile_sz // 2, 7)
        pygame.draw.circle(card, pin_color, pin_pos, 4)
        pygame.draw.circle(card, THEME.accent_text, (pin_pos[0] - 1, pin_pos[1] - 1), 1)

        rotated = pygame.transform.rotozoom(card, angle_deg, 1.0)
        self._pin_cache[key] = rotated
        return rotated

    def _draw_pinboard_avatars(self, surface: pygame.Surface) -> None:
        screen_w, screen_h = surface.get_size()
        left_margin = self._list_rect.left
        right_margin = screen_w - self._list_rect.right
        margin = min(left_margin, right_margin)
        if margin < 120:
            return

        tile_sz = 72 if margin >= 160 else 60
        left_angles = (-8, 7, -6, 9)
        right_angles = (8, -7, 6, -9)
        avail_h = max(tile_sz * 4, min(self._list_rect.height + 24, screen_h - 48))
        step_y = max(tile_sz + 14, (avail_h - tile_sz) // 3)
        total_h = step_y * 3 + tile_sz
        top_y = max(20, min(screen_h - total_h - 20, self._list_rect.centery - total_h // 2))

        max_shift = max(8, (margin - 24 - tile_sz - 14) // 2)
        zigzag = min(24, max_shift)
        left_base_cx = left_margin // 2
        right_base_cx = self._list_rect.right + right_margin // 2

        for row in range(4):
            cy = top_y + row * step_y + tile_sz // 2
            shift = -zigzag if row % 2 == 0 else zigzag

            surf_l = self._get_pinned_card(4 + row, tile_sz, left_angles[row])
            cx_l = max(surf_l.get_width() // 2 + 10, min(left_margin - surf_l.get_width() // 2 - 10, left_base_cx + shift))
            surface.blit(surf_l, surf_l.get_rect(center=(cx_l, cy)))

            surf_r = self._get_pinned_card(8 + row, tile_sz, right_angles[row])
            cx_r = max(
                self._list_rect.right + surf_r.get_width() // 2 + 10,
                min(screen_w - surf_r.get_width() // 2 - 10, right_base_cx - shift),
            )
            surface.blit(surf_r, surf_r.get_rect(center=(cx_r, cy)))

    def _scroll_by(self, delta_y: int) -> None:
        self._scroll_y = max(0, min(self._scroll_y + delta_y, self._max_scroll))

    def _set_scroll_from_thumb_y(self, thumb_top: int) -> None:
        usable = self._track_rect.height - self._thumb_rect.height
        if usable <= 0 or self._max_scroll <= 0:
            self._scroll_y = 0
            return
        ratio = max(0.0, min(1.0, (thumb_top - self._track_rect.y) / usable))
        self._scroll_y = int(round(ratio * self._max_scroll))

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._btn_back is None or self._btn_load is None:
            self._rebuild_layout()

        if self._btn_back is not None and self._btn_back.handle_event(event):
            return
        if self._btn_load is not None and self._btn_load.handle_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.controller.show_menu()
            elif event.key == pygame.K_DOWN:
                self._scroll_by(36)
            elif event.key == pygame.K_UP:
                self._scroll_by(-36)
            return

        if event.type == pygame.MOUSEWHEEL:
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            if self._list_rect.collidepoint(pos) or pos == (0, 0):
                self._scroll_by(-event.y * 36)
            return

        if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", None) == 1:
            self._dragging_scrollbar = False
            return

        if event.type == pygame.MOUSEMOTION:
            if self._dragging_scrollbar:
                self._set_scroll_from_thumb_y(event.pos[1] - self._drag_offset_y)
            return

        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        if event.button == 4 and self._list_rect.collidepoint(event.pos):
            self._scroll_by(-36)
            return
        if event.button == 5 and self._list_rect.collidepoint(event.pos):
            self._scroll_by(36)
            return
        if event.button != 1:
            return

        if self._max_scroll > 0 and self._thumb_rect.collidepoint(event.pos):
            self._dragging_scrollbar = True
            self._drag_offset_y = event.pos[1] - self._thumb_rect.y
            return
        if self._max_scroll > 0 and self._track_rect.collidepoint(event.pos):
            self._dragging_scrollbar = True
            self._drag_offset_y = self._thumb_rect.height // 2
            self._set_scroll_from_thumb_y(event.pos[1] - self._drag_offset_y)
            return
        if self._list_rect.collidepoint(event.pos):
            for row_rect, entry in self._row_rects:
                if row_rect.collidepoint(event.pos):
                    self._local_error = ""
                    self.controller.load_case(entry.path)
                    return

    def render(self, surface: pygame.Surface) -> None:
        if surface.get_size() != self._size or self._btn_back is None:
            self.on_resize(*surface.get_size())

        surface.fill(THEME.bg)
        self._draw_pinboard_avatars(surface)

        title_font = get_font(26 if self._size[0] >= 740 else 22, bold=True)
        btn_font = get_font(12, bold=True)
        item_font = get_font(14, bold=True)
        sub_font = get_font(12)

        assert self._btn_back is not None and self._btn_load is not None
        self._btn_back.draw(surface, btn_font)
        self._btn_load.draw(surface, btn_font)

        title_surf = title_font.render("Select Puzzle Case", True, THEME.text)
        surface.blit(title_surf, title_surf.get_rect(center=(self._list_rect.centerx, self._btn_back.rect.centery)))

        pygame.draw.rect(surface, THEME.panel_bg, self._list_rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._list_rect, 1, border_radius=8)

        inner = self._list_rect.inflate(-16, -16)
        self._row_rects = []
        if not self.cases:
            self._max_scroll = 0
            self._scroll_y = 0
            self._track_rect = pygame.Rect(0, 0, 0, 0)
            self._thumb_rect = pygame.Rect(0, 0, 0, 0)
            empty = sub_font.render(
                "No puzzle JSON files found in puzzles/examples or puzzles/benchmark. Use Load JSON...",
                True,
                THEME.text_muted,
            )
            surface.blit(empty, (inner.x, inner.y + 8))
        else:
            row_h = 58
            gap = 8
            total_h = len(self.cases) * (row_h + gap) - gap
            self._max_scroll = max(0, total_h - inner.height)
            self._scroll_y = max(0, min(self._scroll_y, self._max_scroll))

            bar_w = 12 if self._max_scroll > 0 else 0
            item_w = max(120, inner.width - bar_w)
            mouse_pos = pygame.mouse.get_pos()

            prev_clip = surface.get_clip()
            surface.set_clip(inner)
            y = inner.y - self._scroll_y
            for entry in self.cases:
                row_rect = pygame.Rect(inner.x, y, item_w, row_h)
                if row_rect.bottom >= inner.y and row_rect.y <= inner.bottom:
                    hovered = inner.collidepoint(mouse_pos) and row_rect.collidepoint(mouse_pos)
                    bg = THEME.button_hover if hovered else THEME.card_face_up
                    border = THEME.accent if hovered else THEME.border
                    pygame.draw.rect(surface, bg, row_rect, border_radius=6)
                    pygame.draw.rect(surface, border, row_rect, 1, border_radius=6)

                    hit_rect = row_rect.clip(inner)
                    if hit_rect.width > 0 and hit_rect.height > 0:
                        self._row_rects.append((hit_rect, entry))

                    badge_txt = sub_font.render(f"[{entry.group.upper()}]", True, THEME.accent)
                    surface.blit(badge_txt, (row_rect.x + 12, row_rect.y + 8))

                    size_tag = _detect_size_tag(Path(entry.path).stem)
                    if size_tag:
                        size_surf = sub_font.render(f"[{size_tag}]", True, THEME.text_muted)
                        surface.blit(size_surf, (row_rect.x + 18 + badge_txt.get_width(), row_rect.y + 8))

                    lbl = truncate_text(entry.label, item_font, row_rect.width - 140)
                    surface.blit(item_font.render(lbl, True, THEME.text), (row_rect.x + 12, row_rect.y + 28))

                    open_txt = btn_font.render("Open >", True, THEME.accent)
                    surface.blit(open_txt, open_txt.get_rect(right=row_rect.right - 14, centery=row_rect.centery))

                y += row_h + gap

            if len(self.cases) < 4:
                hint_y = y + 8
                hint_msg = (
                    "Place 3x3 / 4x4 / 5x5 JSON files in puzzles/examples or puzzles/benchmark, "
                    "or click Load JSON..."
                )
                for line in wrap_text(hint_msg, sub_font, item_w - 16):
                    if hint_y + sub_font.get_height() <= inner.bottom:
                        surface.blit(sub_font.render(line, True, THEME.text_muted), (inner.x + 6, hint_y))
                    hint_y += sub_font.get_height() + 3

            surface.set_clip(prev_clip)

            if self._max_scroll > 0:
                self._track_rect = pygame.Rect(inner.right - 8, inner.y, 8, inner.height)
                pygame.draw.rect(surface, THEME.panel_alt_bg, self._track_rect, border_radius=4)
                thumb_h = min(self._track_rect.height, max(24, int(self._track_rect.height * (inner.height / total_h))))
                usable = max(1, self._track_rect.height - thumb_h)
                thumb_y = self._track_rect.y + int(usable * (self._scroll_y / self._max_scroll))
                self._thumb_rect = pygame.Rect(self._track_rect.x, thumb_y, self._track_rect.width, thumb_h)
                thumb_color = THEME.text_muted if self._dragging_scrollbar else THEME.border
                pygame.draw.rect(surface, thumb_color, self._thumb_rect, border_radius=4)
            else:
                self._track_rect = pygame.Rect(0, 0, 0, 0)
                self._thumb_rect = pygame.Rect(0, 0, 0, 0)

        msg = self._local_error or getattr(self.controller, "status_message", "")
        if msg:
            status_rect = pygame.Rect(self._list_rect.x, self._list_rect.bottom + 12, self._list_rect.width, 36)
            is_err = bool(self._local_error) or any(
                word in msg.lower() for word in ("failed", "error", "timed out", "timeout", "unavailable")
            )
            bg = THEME.criminal_bg if is_err else THEME.panel_alt_bg
            border = THEME.criminal if is_err else THEME.border
            fg = THEME.criminal if is_err else THEME.text
            pygame.draw.rect(surface, bg, status_rect, border_radius=6)
            pygame.draw.rect(surface, border, status_rect, 1, border_radius=6)
            txt = sub_font.render(truncate_text(msg, sub_font, status_rect.width - 20), True, fg)
            surface.blit(txt, txt.get_rect(left=status_rect.x + 10, centery=status_rect.centery))
