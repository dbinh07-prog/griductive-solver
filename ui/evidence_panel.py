"""Scrollable list of revealed public clues with selection highlighting."""
from collections.abc import Callable
import pygame

from contracts.models import PublicState
from ui.clue_text import describe_clue
from ui.theme import THEME, get_font, truncate_text, wrap_text


class EvidencePanel:
    """Display all revealed public clues and notify on clue selection."""

    def __init__(self, on_select_clue: Callable[[str], None]) -> None:
        self.on_select_clue = on_select_clue
        self._rect = pygame.Rect(0, 0, 240, 360)
        self._content_rect = pygame.Rect(0, 0, 240, 320)
        self._track_rect = pygame.Rect(0, 0, 0, 0)
        self._thumb_rect = pygame.Rect(0, 0, 0, 0)
        self._scroll_y = 0
        self._max_scroll = 0
        self._dragging_scrollbar = False
        self._drag_offset_y = 0
        self._item_rects: list[tuple[pygame.Rect, str]] = []

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = pygame.Rect(rect)

    def scroll_by(self, delta_y: int) -> None:
        self._scroll_y = max(0, min(self._scroll_y + delta_y, self._max_scroll))

    def _set_scroll_from_thumb_y(self, thumb_top: int) -> None:
        usable = self._track_rect.height - self._thumb_rect.height
        if usable <= 0 or self._max_scroll <= 0:
            self._scroll_y = 0
            return
        ratio = max(0.0, min(1.0, (thumb_top - self._track_rect.y) / usable))
        self._scroll_y = int(round(ratio * self._max_scroll))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            pos = getattr(event, "pos", None) or pygame.mouse.get_pos()
            if self._rect.collidepoint(pos) or pos == (0, 0):
                self.scroll_by(-event.y * 28)
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
        if event.button == 4 and self._rect.collidepoint(event.pos):
            self.scroll_by(-28)
        elif event.button == 5 and self._rect.collidepoint(event.pos):
            self.scroll_by(28)
        elif event.button == 1:
            if self._max_scroll > 0 and self._thumb_rect.collidepoint(event.pos):
                self._dragging_scrollbar = True
                self._drag_offset_y = event.pos[1] - self._thumb_rect.y
                return
            if self._max_scroll > 0 and self._track_rect.collidepoint(event.pos):
                self._dragging_scrollbar = True
                self._drag_offset_y = self._thumb_rect.height // 2
                self._set_scroll_from_thumb_y(event.pos[1] - self._drag_offset_y)
                return
            if self._content_rect.collidepoint(event.pos):
                for item_rect, clue_id in self._item_rects:
                    if item_rect.collidepoint(event.pos):
                        self.on_select_clue(clue_id)
                        return

    def render(
        self,
        surface: pygame.Surface,
        public_state: PublicState,
        selected_clue_id: str | None,
    ) -> None:
        pygame.draw.rect(surface, THEME.panel_bg, self._rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._rect, 1, border_radius=8)

        title_font = get_font(14, bold=True)
        head_font = get_font(12, bold=True)
        body_font = get_font(12)

        pad = 8
        clues = public_state.revealed_clues
        title_surf = title_font.render(f"Public Evidence ({len(clues)})", True, THEME.text)
        surface.blit(title_surf, (self._rect.x + pad, self._rect.y + pad))

        header_bottom = self._rect.y + pad + title_surf.get_height() + 6
        pygame.draw.line(
            surface,
            THEME.border,
            (self._rect.x + pad, header_bottom),
            (self._rect.right - pad, header_bottom),
            1,
        )

        self._content_rect = pygame.Rect(
            self._rect.x + pad,
            header_bottom + 6,
            max(20, self._rect.width - pad * 2),
            max(20, self._rect.bottom - pad - (header_bottom + 6)),
        )
        self._item_rects = []

        if not clues:
            self._max_scroll = 0
            self._scroll_y = 0
            self._track_rect = pygame.Rect(0, 0, 0, 0)
            self._thumb_rect = pygame.Rect(0, 0, 0, 0)
            self._dragging_scrollbar = False
            empty_surf = body_font.render("No public clues yet.", True, THEME.text_muted)
            surface.blit(empty_surf, (self._content_rect.x, self._content_rect.y + 4))
            return

        names = {ch.cell: ch.name for ch in public_state.characters}
        bar_w = 8
        item_w = max(40, self._content_rect.width - bar_w - 4)

        blocks: list[tuple[str, str, list[str], int]] = []
        total_h = 0
        gap = 6
        for owner_cell, clue in clues:
            owner_name = names.get(owner_cell, owner_cell)
            header_txt = truncate_text(f"{clue.id} | {owner_cell} {owner_name}", head_font, item_w - 14)
            lines = wrap_text(describe_clue(clue, public_state.size), body_font, item_w - 14)
            block_h = 8 + head_font.get_height() + 4 + len(lines) * (body_font.get_height() + 2) + 6
            blocks.append((clue.id, header_txt, lines, block_h))
            total_h += block_h + gap

        if blocks:
            total_h -= gap
        self._max_scroll = max(0, total_h - self._content_rect.height)
        self._scroll_y = max(0, min(self._scroll_y, self._max_scroll))

        prev_clip = surface.get_clip()
        surface.set_clip(self._content_rect)

        y = self._content_rect.y - self._scroll_y
        for clue_id, header_txt, lines, block_h in blocks:
            item_rect = pygame.Rect(self._content_rect.x, y, item_w, block_h)
            if item_rect.bottom >= self._content_rect.y and item_rect.y <= self._content_rect.bottom:
                is_sel = clue_id == selected_clue_id
                bg = THEME.clue_tint if is_sel else THEME.card_face_up
                border = THEME.clue_border if is_sel else THEME.border
                pygame.draw.rect(surface, bg, item_rect, border_radius=5)
                pygame.draw.rect(surface, border, item_rect, 2 if is_sel else 1, border_radius=5)

                hit_rect = item_rect.clip(self._content_rect)
                if hit_rect.width > 0 and hit_rect.height > 0:
                    self._item_rects.append((hit_rect, clue_id))

                ty = item_rect.y + 6
                h_surf = head_font.render(header_txt, True, THEME.accent if not is_sel else THEME.clue_border)
                surface.blit(h_surf, (item_rect.x + 7, ty))
                ty += head_font.get_height() + 4
                for line in lines:
                    l_surf = body_font.render(line, True, THEME.text)
                    surface.blit(l_surf, (item_rect.x + 7, ty))
                    ty += body_font.get_height() + 2

            y += block_h + gap

        surface.set_clip(prev_clip)

        if self._max_scroll > 0:
            self._track_rect = pygame.Rect(
                self._content_rect.right - bar_w + 2,
                self._content_rect.y,
                bar_w - 2,
                self._content_rect.height,
            )
            pygame.draw.rect(surface, THEME.panel_alt_bg, self._track_rect, border_radius=3)
            ratio = self._content_rect.height / total_h
            thumb_h = min(self._track_rect.height, max(20, int(self._track_rect.height * ratio)))
            usable = max(1, self._track_rect.height - thumb_h)
            thumb_y = self._track_rect.y + int(usable * (self._scroll_y / self._max_scroll))
            self._thumb_rect = pygame.Rect(self._track_rect.x, thumb_y, self._track_rect.width, thumb_h)
            thumb_color = THEME.text_muted if self._dragging_scrollbar else THEME.border
            pygame.draw.rect(surface, thumb_color, self._thumb_rect, border_radius=3)
        else:
            self._track_rect = pygame.Rect(0, 0, 0, 0)
            self._thumb_rect = pygame.Rect(0, 0, 0, 0)
            self._dragging_scrollbar = False
