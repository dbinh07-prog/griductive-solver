"""Board grid view with coordinates, character avatars, clues, and highlights."""
from collections.abc import Callable
import pygame

from contracts.models import Character, Clue, PublicState, Status
from ui.theme import (
    THEME,
    draw_avatar_fallback,
    draw_status_icon,
    get_avatar_surface,
    get_font,
    status_visual,
    truncate_text,
)


class BoardView:
    """Interactive grid rendering public character cards and highlight overlays."""

    def __init__(self, on_select: Callable[[str], None]) -> None:
        self.on_select = on_select
        self._rect = pygame.Rect(0, 0, 480, 400)
        self._anim_mgr = None
        self._hint_cell: str | None = None
        self._secondary_cells: tuple[str, ...] = ()
        self._overlap_cells: tuple[str, ...] = ()
        self._card_rects: dict[str, pygame.Rect] = {}

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = pygame.Rect(rect)

    def set_animation_manager(self, anim_mgr) -> None:
        self._anim_mgr = anim_mgr

    def set_hint_cell(self, cell: str | None) -> None:
        self._hint_cell = cell

    def set_secondary_highlights(
        self,
        secondary_cells: tuple[str, ...] = (),
        overlap_cells: tuple[str, ...] = (),
    ) -> None:
        self._secondary_cells = tuple(secondary_cells)
        self._overlap_cells = tuple(overlap_cells)

    def cell_at(self, pos: tuple[int, int]) -> str | None:
        for cell, rect in self._card_rects.items():
            if rect.collidepoint(pos):
                return cell
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            cell = self.cell_at(event.pos)
            if cell is not None:
                self.on_select(cell)

    def render(
        self,
        surface: pygame.Surface,
        public_state: PublicState,
        selected_cell: str | None,
        highlighted_cells: tuple[str, ...],
    ) -> None:
        pygame.draw.rect(surface, THEME.panel_bg, self._rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._rect, 1, border_radius=8)

        size = max(1, public_state.size)
        pad = 8
        hdr_h = 20
        row_lbl_w = 22
        gap = 6 if size <= 4 else 4

        grid_x = self._rect.x + pad + row_lbl_w
        grid_y = self._rect.y + pad + hdr_h
        grid_w = max(40, self._rect.width - pad * 2 - row_lbl_w)
        grid_h = max(40, self._rect.height - pad * 2 - hdr_h)
        card_w = max(24, (grid_w - gap * (size - 1)) // size)
        card_h = max(24, (grid_h - gap * (size - 1)) // size)

        hdr_font = get_font(12, bold=True)
        for col in range(size):
            col_x = grid_x + col * (card_w + gap)
            lbl = hdr_font.render(chr(65 + col), True, THEME.text_muted)
            surface.blit(lbl, lbl.get_rect(center=(col_x + card_w // 2, self._rect.y + pad + hdr_h // 2)))

        for row in range(size):
            row_y = grid_y + row * (card_h + gap)
            lbl = hdr_font.render(str(row + 1), True, THEME.text_muted)
            surface.blit(lbl, lbl.get_rect(center=(self._rect.x + pad + row_lbl_w // 2, row_y + card_h // 2)))

        char_map: dict[str, tuple[int, Character]] = {
            ch.cell: (idx, ch) for idx, ch in enumerate(public_state.characters)
        }
        proved = dict(public_state.proved_statuses)
        revealed_clues = dict(public_state.revealed_clues)
        highlighted_set = set(highlighted_cells)
        secondary_set = set(self._secondary_cells)
        overlap_set = set(self._overlap_cells)

        self._card_rects = {}
        for row in range(size):
            for col in range(size):
                cell = f"{chr(65 + col)}{row + 1}"
                rect = pygame.Rect(
                    grid_x + col * (card_w + gap),
                    grid_y + row * (card_h + gap),
                    card_w,
                    card_h,
                )
                self._card_rects[cell] = rect

                idx, char = char_map.get(cell, (row * size + col, Character(cell, cell, "")))
                is_revealed = cell in proved
                status = (Status.CRIMINAL if proved[cell] else Status.INNOCENT) if is_revealed else None
                clue = revealed_clues.get(cell) if is_revealed else None

                self._render_card(
                    surface,
                    rect,
                    size,
                    idx,
                    char,
                    status,
                    clue,
                    selected=(cell == selected_cell),
                    highlighted=(cell in highlighted_set),
                    secondary=(cell in secondary_set),
                    overlap=(cell in overlap_set),
                    hinted=(cell == self._hint_cell),
                )

    def _render_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        size: int,
        char_index: int,
        char: Character,
        status: Status | None,
        clue: Clue | None,
        *,
        selected: bool,
        highlighted: bool,
        secondary: bool,
        overlap: bool,
        hinted: bool,
    ) -> None:
        draw_rect = pygame.Rect(rect)
        if self._anim_mgr is not None:
            offset_x = int(round(self._anim_mgr.reject_offset_x(char.cell)))
            scale_x = self._anim_mgr.flip_scale_x(char.cell)
            scaled_w = max(8, int(rect.width * scale_x))
            draw_rect = pygame.Rect(0, rect.y, scaled_w, rect.height)
            draw_rect.centerx = rect.centerx + offset_x

        vis = status_visual(status)
        bg = vis.bg if status is not None else THEME.card_face_down
        if highlighted and status is None:
            bg = THEME.clue_tint

        pygame.draw.rect(surface, bg, draw_rect, border_radius=6)
        pygame.draw.rect(surface, vis.border, draw_rect, 1, border_radius=6)

        if overlap:
            pygame.draw.rect(surface, THEME.overlap_border, draw_rect.inflate(-4, -4), 2, border_radius=5)
        elif secondary:
            pygame.draw.rect(surface, THEME.secondary_border, draw_rect.inflate(-4, -4), 2, border_radius=5)

        if highlighted:
            pygame.draw.rect(surface, THEME.clue_border, draw_rect.inflate(-2, -2), 3, border_radius=5)

        if hinted:
            pulse = self._anim_mgr.pulse_strength(char.cell) if self._anim_mgr is not None else 1.0
            width = 3 if pulse >= 0.4 else 2
            pygame.draw.rect(surface, THEME.hint_border, draw_rect.inflate(2, 2), width, border_radius=7)

        if selected:
            pygame.draw.rect(surface, THEME.select_border, draw_rect.inflate(4, 4), 3, border_radius=7)

        if draw_rect.width < 42:
            return

        coord_font = get_font(12 if draw_rect.height >= 72 else 11, bold=True)
        if draw_rect.height >= 108:
            name_size, sub_size = 14, 12
        elif draw_rect.height >= 80:
            name_size, sub_size = 13, 11
        elif draw_rect.height >= 66:
            name_size, sub_size = 12, 11
        else:
            name_size, sub_size = 11, 11
        name_font = get_font(name_size, bold=True)
        sub_font = get_font(sub_size)

        pad_x = 6 if draw_rect.width >= 105 else 5
        pad_y = 4 if draw_rect.height >= 72 else 2
        top_y = draw_rect.y + pad_y
        coord_surf = coord_font.render(char.cell, True, THEME.text)
        surface.blit(coord_surf, (draw_rect.x + pad_x, top_y))

        icon_sz = 14 if size <= 4 else 12
        icon_rect = pygame.Rect(draw_rect.right - pad_x - icon_sz, top_y + 1, icon_sz, icon_sz)
        draw_status_icon(surface, status, icon_rect, vis.fg)

        if clue is not None and draw_rect.width >= 96:
            tag_surf = sub_font.render(clue.id, True, THEME.accent)
            surface.blit(tag_surf, (icon_rect.x - tag_surf.get_width() - 4, top_y + 1))

        body_top = top_y + coord_surf.get_height() + 1
        status_h = sub_font.get_height()
        status_y = draw_rect.bottom - status_h - pad_y
        body_h = max(0, status_y - body_top - 1)

        text_x = draw_rect.x + pad_x
        text_w = max(20, draw_rect.width - pad_x * 2)

        av_sz = min(int(draw_rect.width * 0.40), body_h, 96)
        min_text_w = 50 if size >= 4 else 56
        # Show proportional avatars across 3x3/4x4/5x5 whenever card space keeps text >= 11px legible.
        if av_sz >= 24 and (text_w - av_sz - 6) >= min_text_w:
            av_rect = pygame.Rect(draw_rect.x + pad_x, body_top + (body_h - av_sz) // 2, av_sz, av_sz)
            av_surf = get_avatar_surface(char_index, av_sz)
            if av_surf is not None:
                surface.blit(av_surf, av_rect)
            else:
                draw_avatar_fallback(surface, av_rect, char.name, char_index)
            text_x = av_rect.right + 6
            text_w = max(20, draw_rect.right - pad_x - text_x)

        name_h = name_font.get_height()
        show_prof = bool(char.profession) and (name_h + sub_font.get_height() <= body_h)
        prof_gap = 1 if (show_prof and name_h + 1 + sub_font.get_height() <= body_h) else 0
        block_h = name_h + (prof_gap + sub_font.get_height() if show_prof else 0)
        y = body_top + max(0, (body_h - block_h) // 2)

        name_txt = truncate_text(char.name, name_font, text_w)
        name_surf = name_font.render(name_txt, True, THEME.text)
        surface.blit(name_surf, (text_x, y))
        if show_prof:
            prof_txt = truncate_text(char.profession, sub_font, text_w)
            prof_surf = sub_font.render(prof_txt, True, THEME.text_muted)
            surface.blit(prof_surf, (text_x, y + name_h + prof_gap))

        status_txt = truncate_text(f"{vis.badge} {vis.label}", sub_font, draw_rect.width - pad_x * 2)
        status_surf = sub_font.render(status_txt, True, vis.fg)
        surface.blit(status_surf, (draw_rect.x + pad_x, status_y))
