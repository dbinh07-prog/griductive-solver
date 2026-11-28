"""Tutorial scene presenting game rules, card legend, and keyboard shortcuts."""
from dataclasses import dataclass
import re
import pygame

from contracts.models import Status
from scenes.base_scene import BaseScene, UIButton
from ui.theme import (
    THEME,
    draw_avatar_fallback,
    draw_status_icon,
    get_avatar_surface,
    get_font,
    status_visual,
    truncate_text,
    wrap_text,
)


_ACCENT_PATTERN = re.compile(
    r"(\[[A-Za-z]+\]|(?:ROW|COLUMN|NEIGHBORS|EXPLICIT|NOT_PROVABLE|CONTRADICTED|UNKNOWN|INCONSISTENT|TIMEOUT):)"
)
_RAIL_NAMES: tuple[str, ...] = ("Ada", "Bao", "Clara", "Derek", "Eliza", "Franz", "Grant", "Hannah", "Ivy", "Jonas")
_RAIL_TINTS: tuple[tuple[int, int, int], ...] = (
    THEME.panel_bg,
    THEME.innocent_bg,
    THEME.card_face_down,
    THEME.criminal_bg,
)

_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "1. No-Guess Deduction Rule",
        (
            "Verdicts are accepted ONLY when mathematically forced by the currently revealed clues (Public KB).",
            "Even if your choice matches the hidden solution, an unprovable guess returns NOT_PROVABLE and does not flip the card.",
        ),
    ),
    (
        "2. Always-True Clues",
        (
            "Every revealed clue is guaranteed true, even when the speaker is a Criminal. There are no liars in this ruleset.",
            "Character names and professions are purely visual flavor and never encode hidden logical constraints.",
        ),
    ),
    (
        "3. Board Regions",
        (
            "ROW: All cells in the specified 1-based horizontal row.",
            "COLUMN: All cells in the specified column letter (A, B, C...).",
            "NEIGHBORS: Up to 8 orthogonal and diagonal neighbors surrounding the anchor cell (excluding the anchor itself).",
            "EXPLICIT: Exact list of named coordinates.",
        ),
    ),
    (
        "4. Feedback & Terminal States",
        (
            "NOT_PROVABLE: Public evidence does not yet force the verdict. CONTRADICTED: Public evidence already proves the opposite.",
            "UNKNOWN: No forced move remains under the current public clues (consistent state; you are not shown hidden answers).",
            "INCONSISTENT: Public evidence has no valid assignment (UNSAT). TIMEOUT: SAT query exceeded its time limit.",
        ),
    ),
    (
        "5. Controls & Keyboard Shortcuts",
        (
            "[H] Hint: Highlight a forced move without revealing the card or adding a deduction step.",
            "[N] Next Step: Reveal one deterministic forced card via the solver.",
            "[Space] Auto Solve / Pause: Toggle automatic step-by-step solving or pause immediately.",
            "[R] Restart: Reset the current puzzle back to its initial clues.",
            "[C] Submit Criminal   [I] Submit Innocent   [Esc] Back / Menu",
        ),
    ),
)

_LEGEND_CARDS: tuple[tuple[Status | None, int, str, str], ...] = (
    (None, 1, "B2", "Unproved - submit only when forced."),
    (Status.INNOCENT, 2, "B1", "Proved Innocent - reveals a public clue."),
    (Status.CRIMINAL, 0, "A1", "Proved Criminal - clue is still 100% true."),
)


@dataclass(frozen=True)
class _LayoutMetrics:
    pad: int
    panel_w: int
    btn_w: int
    btn_h: int
    btn_font_size: int
    title_size: int
    sec_size: int
    body_size: int
    small_size: int
    pad_x: int
    pad_y: int
    gap: int
    line_gap: int
    legend_h: int
    legend_gap: int


def _layout_metrics(w: int, h: int) -> _LayoutMetrics:
    if w >= 1760 and h >= 980:
        pad = 24
        panel_w = min(1320, max(1080, int(w * 0.70)))
        return _LayoutMetrics(pad, panel_w, 116, 42, 14, 36, 20, 17, 14, 20, 14, 9, 3, 146, 16)
    if w >= 1500 and h >= 830:
        pad = 20
        panel_w = min(1180, max(980, int(w * 0.72)))
        return _LayoutMetrics(pad, panel_w, 108, 38, 13, 32, 18, 15, 13, 18, 12, 7, 2, 126, 12)
    if w >= 1360 and h >= 760:
        pad = 16
        panel_w = min(1060, max(940, int(w * 0.72)))
        return _LayoutMetrics(pad, panel_w, 104, 36, 13, 30, 16, 14, 12, 16, 10, 6, 1, 114, 10)
    if w >= 1200 and h >= 700:
        pad = 14
        panel_w = min(940, max(540, w - pad * 2))
        return _LayoutMetrics(pad, panel_w, 96, 34, 12, 26, 15, 13, 11, 14, 9, 5, 1, 102, 10)
    pad = 16
    panel_w = min(940, max(540, w - pad * 2))
    title_size = 24 if w >= 780 else 22
    return _LayoutMetrics(pad, panel_w, 96, 34, 12, title_size, 14, 12, 11, 14, 10, 6, 2, 104, 12)


def _accented_width(text: str, body_font: pygame.font.Font, bold_font: pygame.font.Font) -> int:
    width = 0
    for part in _ACCENT_PATTERN.split(text):
        if not part:
            continue
        font = bold_font if _ACCENT_PATTERN.fullmatch(part) else body_font
        width += font.size(part)[0]
    return width


def _wrap_accented_text(
    text: str,
    body_font: pygame.font.Font,
    bold_font: pygame.font.Font,
    max_width: int,
) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    for raw_line in text.splitlines():
        current = ""
        for word in raw_line.split(" "):
            candidate = word if not current else f"{current} {word}"
            if _accented_width(candidate, body_font, bold_font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if _accented_width(word, body_font, bold_font) <= max_width:
                current = word
                continue
            chunk = ""
            for ch in word:
                if chunk and _accented_width(chunk + ch, body_font, bold_font) > max_width:
                    lines.append(chunk)
                    chunk = ch
                else:
                    chunk += ch
            current = chunk
        lines.append(current)
    return lines or [""]


def _render_accented_line(
    surface: pygame.Surface,
    line: str,
    x: int,
    y: int,
    body_font: pygame.font.Font,
    bold_font: pygame.font.Font,
) -> None:
    cx = x
    bold_y = y + max(0, (body_font.get_height() - bold_font.get_height()) // 2)
    for part in _ACCENT_PATTERN.split(line):
        if not part:
            continue
        is_tok = bool(_ACCENT_PATTERN.fullmatch(part))
        font = bold_font if is_tok else body_font
        color = THEME.accent if is_tok else THEME.text
        surf = font.render(part, True, color)
        surface.blit(surf, (cx, bold_y if is_tok else y))
        cx += surf.get_width()


class TutorialScene(BaseScene):
    """Scrollable English guide to Griductive Solver rules and keyboard controls."""

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self._size = (1280, 720)
        self._metrics = _layout_metrics(1280, 720)
        self._panel_rect = pygame.Rect(32, 62, 940, 520)
        self._content_rect = pygame.Rect(32, 62, 940, 520)
        self._legend_rect = pygame.Rect(0, 0, 0, 0)
        self._btn_back: UIButton | None = None
        self._scroll_y = 0
        self._max_scroll = 0
        self._track_rect = pygame.Rect(0, 0, 0, 0)
        self._thumb_rect = pygame.Rect(0, 0, 0, 0)
        self._dragging_scrollbar = False
        self._drag_offset_y = 0

    def on_enter(self) -> None:
        self._scroll_y = 0
        self._rebuild_layout()

    def on_resize(self, width: int, height: int) -> None:
        self._size = (max(640, width), max(480, height))
        self._rebuild_layout()

    def _go_back(self) -> None:
        if hasattr(self.controller, "return_from_tutorial"):
            self.controller.return_from_tutorial()
        else:
            self.controller.show_menu()

    def _rebuild_layout(self) -> None:
        w, h = self._size
        m = _layout_metrics(w, h)
        self._metrics = m
        panel_x = (w - m.panel_w) // 2
        self._btn_back = UIButton(
            pygame.Rect(panel_x, m.pad, m.btn_w, m.btn_h),
            "Back",
            self._go_back,
            tooltip="Return to previous screen",
        )
        top = m.pad + m.btn_h + 12
        avail_h = max(200, h - top - m.pad)
        max_rules_h = (avail_h - m.legend_gap - m.legend_h) if avail_h >= 460 else avail_h
        self._panel_rect = pygame.Rect(panel_x, top, m.panel_w, max_rules_h)
        self._content_rect = pygame.Rect(self._panel_rect)

    def _draw_side_rail(self, surface: pygame.Surface, bounds_rect: pygame.Rect) -> None:
        screen_w = surface.get_width()
        left_margin = bounds_rect.left
        right_margin = screen_w - bounds_rect.right
        margin = min(left_margin, right_margin)
        if margin < 120:
            return

        if margin >= 240:
            tile_w, tile_h = 96, 112
            lbl_size = 12
        elif margin >= 200:
            tile_w, tile_h = 88, 102
            lbl_size = 11
        elif margin >= 165:
            tile_w, tile_h = 78, 90
            lbl_size = 10
        else:
            tile_w, tile_h = 66, 78
            lbl_size = 10

        count = min(5, max(3, (bounds_rect.height + 16) // (tile_h + 16)))
        step_y = (bounds_rect.height - tile_h) / max(1, count - 1)
        left_cx = left_margin // 2
        right_cx = bounds_rect.right + right_margin // 2
        label_font = get_font(lbl_size, bold=True)

        top_cy = bounds_rect.top + tile_h // 2
        bot_cy = bounds_rect.bottom - tile_h // 2
        if bot_cy > top_cy:
            pygame.draw.line(surface, THEME.border, (left_cx, top_cy), (left_cx, bot_cy), 1)
            pygame.draw.line(surface, THEME.border, (right_cx, top_cy), (right_cx, bot_cy), 1)

        av_sz = tile_w - 22
        for row in range(count):
            y = int(round(bounds_rect.top + row * step_y))
            for col_idx, (cx, col_letter, offset) in enumerate(((left_cx, "A", 10), (right_cx, "E", 15))):
                char_idx = offset + row
                rect = pygame.Rect(cx - tile_w // 2, y, tile_w, tile_h)
                tint = _RAIL_TINTS[(char_idx + col_idx) % len(_RAIL_TINTS)]
                pygame.draw.rect(surface, tint, rect, border_radius=8)
                pygame.draw.rect(surface, THEME.border, rect, 1, border_radius=8)

                av_rect = pygame.Rect(rect.centerx - av_sz // 2, rect.y + 8, av_sz, av_sz)
                av_surf = get_avatar_surface(char_idx, av_sz)
                if av_surf is not None:
                    surface.blit(av_surf, av_rect)
                else:
                    draw_avatar_fallback(surface, av_rect, _RAIL_NAMES[char_idx % len(_RAIL_NAMES)], char_idx)

                coord_surf = label_font.render(f"{col_letter}{row + 1}", True, THEME.text_muted)
                surface.blit(coord_surf, coord_surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 5))

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
        if self._btn_back is None:
            self._rebuild_layout()

        if self._btn_back is not None and self._btn_back.handle_event(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
            elif event.key == pygame.K_DOWN:
                self._scroll_by(36)
            elif event.key == pygame.K_UP:
                self._scroll_by(-36)
            elif event.key == pygame.K_PAGEDOWN:
                self._scroll_by(180)
            elif event.key == pygame.K_PAGEUP:
                self._scroll_by(-180)
            return

        if event.type == pygame.MOUSEWHEEL:
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            if self._content_rect.collidepoint(pos) or pos == (0, 0):
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
        if event.button == 4 and self._content_rect.collidepoint(event.pos):
            self._scroll_by(-36)
        elif event.button == 5 and self._content_rect.collidepoint(event.pos):
            self._scroll_by(36)
        elif event.button == 1 and self._max_scroll > 0:
            if self._thumb_rect.collidepoint(event.pos):
                self._dragging_scrollbar = True
                self._drag_offset_y = event.pos[1] - self._thumb_rect.y
            elif self._track_rect.collidepoint(event.pos):
                self._dragging_scrollbar = True
                self._drag_offset_y = self._thumb_rect.height // 2
                self._set_scroll_from_thumb_y(event.pos[1] - self._drag_offset_y)

    def _measure_cards(
        self,
        card_w: int,
        sec_font: pygame.font.Font,
        body_font: pygame.font.Font,
        bold_font: pygame.font.Font,
        gap: int,
        line_gap: int,
    ) -> tuple[list[tuple[str, list[list[str]], int]], int]:
        text_w = max(120, card_w - 28)
        line_step = body_font.get_height() + line_gap
        v_pad = 7 if self._metrics.body_size >= 16 else 5
        title_gap = 5 if self._metrics.body_size >= 16 else 3
        bullet_gap = 2 if self._metrics.body_size >= 16 else 1
        cards: list[tuple[str, list[list[str]], int]] = []
        total_h = 0
        for heading, bullets in _SECTIONS:
            wrapped = [_wrap_accented_text(item, body_font, bold_font, text_w) for item in bullets]
            line_count = sum(len(lines) for lines in wrapped)
            card_h = v_pad * 2 + sec_font.get_height() + title_gap + line_count * line_step + len(bullets) * bullet_gap
            cards.append((heading, wrapped, card_h))
            total_h += card_h + gap
        if cards:
            total_h -= gap
        return cards, total_h

    def _render_legend(
        self,
        surface: pygame.Surface,
        sec_font: pygame.font.Font,
        bold_font: pygame.font.Font,
        small_font: pygame.font.Font,
        icon_sz: int,
    ) -> None:
        pygame.draw.rect(surface, THEME.panel_bg, self._legend_rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._legend_rect, 1, border_radius=8)

        pad_x = 14
        title_y = self._legend_rect.y + 8
        surface.blit(sec_font.render("Card Status Legend", True, THEME.text), (self._legend_rect.x + pad_x, title_y))

        cards_top = title_y + sec_font.get_height() + 6
        cards_h = max(44, self._legend_rect.bottom - 10 - cards_top)
        gap = 10
        inner_w = self._legend_rect.width - pad_x * 2
        col_w = max(120, (inner_w - gap * 2) // 3)

        for idx, (status, char_idx, cell_id, desc) in enumerate(_LEGEND_CARDS):
            card_rect = pygame.Rect(self._legend_rect.x + pad_x + idx * (col_w + gap), cards_top, col_w, cards_h)
            vis = status_visual(status)
            bg = vis.bg if status is not None else THEME.card_face_down
            pygame.draw.rect(surface, bg, card_rect, border_radius=6)
            pygame.draw.rect(surface, vis.border, card_rect, 1, border_radius=6)

            av_sz = min(58, card_rect.height - 14)
            av_rect = pygame.Rect(card_rect.x + 8, card_rect.y + (card_rect.height - av_sz) // 2, av_sz, av_sz)
            av_surf = get_avatar_surface(char_idx, av_sz)
            if av_surf is not None:
                surface.blit(av_surf, av_rect)
            else:
                draw_avatar_fallback(surface, av_rect, _RAIL_NAMES[char_idx], char_idx)

            tx = av_rect.right + 10
            tw = max(40, card_rect.right - 8 - tx)
            ty = card_rect.y + 8
            icon_rect = pygame.Rect(tx, ty + max(0, (bold_font.get_height() - icon_sz) // 2), icon_sz, icon_sz)
            draw_status_icon(surface, status, icon_rect, vis.fg)
            badge_txt = truncate_text(f"{vis.badge} {vis.label} ({cell_id})", bold_font, max(20, tw - icon_sz - 5))
            badge = bold_font.render(badge_txt, True, vis.fg)
            surface.blit(badge, (icon_rect.right + 5, ty))

            desc_y = ty + bold_font.get_height() + 4
            for line in wrap_text(desc, small_font, tw)[:2]:
                surface.blit(small_font.render(line, True, THEME.text), (tx, desc_y))
                desc_y += small_font.get_height() + 1

    def render(self, surface: pygame.Surface) -> None:
        if surface.get_size() != self._size or self._btn_back is None:
            self.on_resize(*surface.get_size())

        surface.fill(THEME.bg)
        m = self._metrics

        title_font = get_font(m.title_size, bold=True)
        btn_font = get_font(m.btn_font_size, bold=True)
        sec_font = get_font(m.sec_size, bold=True)
        body_font = get_font(m.body_size)
        bold_font = get_font(m.body_size, bold=True)
        small_font = get_font(m.small_size)

        max_inner_h = max(120, self._panel_rect.height - m.pad_y * 2)
        card_w = self._panel_rect.width - m.pad_x * 2
        cards, total_h = self._measure_cards(card_w, sec_font, body_font, bold_font, m.gap, m.line_gap)

        if total_h > max_inner_h:
            card_w = self._panel_rect.width - m.pad_x * 2 - 14
            cards, total_h = self._measure_cards(card_w, sec_font, body_font, bold_font, m.gap, m.line_gap)

        panel_h = min(self._panel_rect.height, total_h + m.pad_y * 2)
        self._content_rect = pygame.Rect(self._panel_rect.x, self._panel_rect.y, self._panel_rect.width, panel_h)

        avail_h = max(200, self._size[1] - self._panel_rect.y - m.pad)
        if avail_h >= 460:
            self._legend_rect = pygame.Rect(
                self._content_rect.x,
                self._content_rect.bottom + m.legend_gap,
                self._content_rect.width,
                m.legend_h,
            )
            bounds = self._content_rect.union(self._legend_rect)
        else:
            self._legend_rect = pygame.Rect(0, 0, 0, 0)
            bounds = self._content_rect

        self._draw_side_rail(surface, bounds)

        assert self._btn_back is not None
        self._btn_back.draw(surface, btn_font)
        title_surf = title_font.render("How to Play Griductive Solver", True, THEME.text)
        surface.blit(title_surf, title_surf.get_rect(center=(self._content_rect.centerx, self._btn_back.rect.centery)))

        pygame.draw.rect(surface, THEME.panel_bg, self._content_rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._content_rect, 1, border_radius=8)

        inner = pygame.Rect(
            self._content_rect.x + m.pad_x,
            self._content_rect.y + m.pad_y,
            self._content_rect.width - m.pad_x * 2,
            self._content_rect.height - m.pad_y * 2,
        )
        self._max_scroll = max(0, total_h - inner.height)
        self._scroll_y = max(0, min(self._scroll_y, self._max_scroll))

        prev_clip = surface.get_clip()
        surface.set_clip(inner)

        line_step = body_font.get_height() + m.line_gap
        v_pad = 7 if m.body_size >= 16 else 5
        title_gap = 5 if m.body_size >= 16 else 3
        bullet_gap = 2 if m.body_size >= 16 else 1
        y = inner.y - self._scroll_y
        for heading, wrapped_bullets, card_h in cards:
            card_rect = pygame.Rect(inner.x, y, card_w, card_h)
            if card_rect.bottom >= inner.y and card_rect.y <= inner.bottom:
                pygame.draw.rect(surface, THEME.card_face_up, card_rect, border_radius=6)
                pygame.draw.rect(surface, THEME.border, card_rect, 1, border_radius=6)

                cy = card_rect.y + v_pad
                surface.blit(sec_font.render(heading, True, THEME.accent), (card_rect.x + 14, cy))
                cy += sec_font.get_height() + title_gap
                for bullet_lines in wrapped_bullets:
                    for line in bullet_lines:
                        _render_accented_line(surface, line, card_rect.x + 16, cy, body_font, bold_font)
                        cy += line_step
                    cy += bullet_gap
            y += card_h + m.gap

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
            self._dragging_scrollbar = False

        if self._legend_rect.height > 0:
            icon_sz = 15 if m.small_size >= 12 else 13
            self._render_legend(surface, sec_font, bold_font, small_font, icon_sz)
