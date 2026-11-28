"""Selected character inspector, verdict controls, hints, and feedback banner."""
from collections.abc import Callable
from dataclasses import dataclass
import pygame

from contracts.models import Analysis, PublicState, Status
from scenes.base_scene import UIButton
from ui.clue_text import describe_clue
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


@dataclass(frozen=True)
class FeedbackMessage:
    kind: str
    title: str
    detail: str


class InspectorPanel:
    """Display selected character details and handle Criminal/Innocent submissions."""

    def __init__(self, on_submit: Callable[[str, Status], None]) -> None:
        self.on_submit = on_submit
        self._rect = pygame.Rect(0, 0, 320, 400)
        self._feedback: FeedbackMessage | None = None
        self._hint: tuple[str, Status] | None = None
        self._no_forced_msg: str | None = None
        self._is_loading = False
        self._criminal_btn = UIButton(pygame.Rect(0, 0, 80, 34), "[!] Criminal", lambda: None)
        self._innocent_btn = UIButton(pygame.Rect(0, 0, 80, 34), "[OK] Innocent", lambda: None)
        self._btn_criminal: UIButton | None = None
        self._btn_innocent: UIButton | None = None

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = pygame.Rect(rect)

    def set_feedback(self, feedback: FeedbackMessage | None) -> None:
        self._feedback = feedback

    def set_hint(self, hint: tuple[str, Status] | None, no_forced_msg: str | None = None) -> None:
        self._hint = hint
        self._no_forced_msg = no_forced_msg

    def set_loading(self, is_loading: bool) -> None:
        self._is_loading = is_loading
        self._criminal_btn.enabled = not is_loading
        self._innocent_btn.enabled = not is_loading

    def handle_event(self, event: pygame.event.Event) -> None:
        if self._btn_criminal is not None and self._btn_criminal.handle_event(event):
            return
        if self._btn_innocent is not None:
            self._btn_innocent.handle_event(event)

    def _clear_verdict_buttons(self) -> None:
        self._btn_criminal = None
        self._btn_innocent = None
        self._criminal_btn.hovered = False
        self._innocent_btn.hovered = False

    def render(
        self,
        surface: pygame.Surface,
        public_state: PublicState,
        analysis: Analysis | None,
        selected_cell: str | None,
    ) -> None:
        del analysis  # Never inspect classifications to leak unrevealed verdicts.
        pygame.draw.rect(surface, THEME.panel_bg, self._rect, border_radius=8)
        pygame.draw.rect(surface, THEME.border, self._rect, 1, border_radius=8)

        title_font = get_font(14, bold=True)
        name_font = get_font(14, bold=True)
        body_font = get_font(12)
        small_font = get_font(11)
        btn_font = get_font(12, bold=True)

        pad = 10
        x = self._rect.x + pad
        w = max(40, self._rect.width - pad * 2)
        y = self._rect.y + pad

        hdr_surf = title_font.render("Inspector", True, THEME.text)
        surface.blit(hdr_surf, (x, y))
        if self._is_loading:
            load_surf = small_font.render("Analyzing...", True, THEME.accent)
            surface.blit(load_surf, (self._rect.right - pad - load_surf.get_width(), y + 2))
        y += hdr_surf.get_height() + 6
        pygame.draw.line(surface, THEME.border, (x, y), (x + w, y), 1)
        y += 8

        char_entry = next(
            ((idx, ch) for idx, ch in enumerate(public_state.characters) if ch.cell == selected_cell),
            None,
        )
        if char_entry is None or selected_cell is None:
            self._clear_verdict_buttons()
            for line in wrap_text(
                "Select a character card on the board to inspect public details or submit a verdict.",
                body_font,
                w,
            ):
                surface.blit(body_font.render(line, True, THEME.text_muted), (x, y))
                y += body_font.get_height() + 3
            y += 8
            self._render_messages(surface, x, y, w, body_font, small_font)
            return

        char_index, char = char_entry
        proved = dict(public_state.proved_statuses)
        is_revealed = selected_cell in proved
        status = (Status.CRIMINAL if proved[selected_cell] else Status.INNOCENT) if is_revealed else None
        vis = status_visual(status)

        av_sz = 64 if w >= 220 else 52
        av_rect = pygame.Rect(x, y, av_sz, av_sz)
        av_surf = get_avatar_surface(char_index, av_sz)
        if av_surf is not None:
            surface.blit(av_surf, av_rect)
        else:
            draw_avatar_fallback(surface, av_rect, char.name, char_index)

        info_x = av_rect.right + 10
        info_w = max(40, x + w - info_x)
        iy = y + max(0, (av_sz - 56) // 2)
        surface.blit(
            name_font.render(truncate_text(f"{char.cell} - {char.name}", name_font, info_w), True, THEME.text),
            (info_x, iy),
        )
        iy += name_font.get_height() + 2
        surface.blit(
            body_font.render(truncate_text(char.profession, body_font, info_w), True, THEME.text_muted),
            (info_x, iy),
        )
        iy += body_font.get_height() + 4
        badge_rect = pygame.Rect(info_x, iy, 14, 14)
        draw_status_icon(surface, status, badge_rect, vis.fg)
        status_text = vis.label if is_revealed else "FACE-DOWN"
        surface.blit(
            small_font.render(f"{vis.badge} {status_text}", True, vis.fg),
            (badge_rect.right + 5, iy),
        )
        y = max(av_rect.bottom, iy + 16) + 12

        if is_revealed:
            self._clear_verdict_buttons()
            revealed_clues = dict(public_state.revealed_clues)
            clue = revealed_clues.get(selected_cell)
            box_title = f"Revealed Clue ({clue.id})" if clue is not None else "Revealed Clue"
            surface.blit(body_font.render(box_title, True, THEME.accent), (x, y))
            y += body_font.get_height() + 4
            clue_body = describe_clue(clue, public_state.size) if clue is not None else "No clue attached."
            clue_lines = wrap_text(clue_body, body_font, w - 12)
            box_h = len(clue_lines) * (body_font.get_height() + 2) + 12
            clue_box = pygame.Rect(x, y, w, box_h)
            pygame.draw.rect(surface, THEME.card_face_up, clue_box, border_radius=5)
            pygame.draw.rect(surface, THEME.border, clue_box, 1, border_radius=5)
            cy = clue_box.y + 6
            for line in clue_lines:
                surface.blit(body_font.render(line, True, THEME.text), (clue_box.x + 6, cy))
                cy += body_font.get_height() + 2
            y = clue_box.bottom + 10
        else:
            surface.blit(body_font.render("Submit Proved Verdict:", True, THEME.text), (x, y))
            y += body_font.get_height() + 6
            btn_gap = 8
            btn_w = max(60, (w - btn_gap) // 2)
            btn_h = 34
            enabled = not self._is_loading
            self._criminal_btn.rect = pygame.Rect(x, y, btn_w, btn_h)
            self._criminal_btn.action = lambda c=selected_cell: self.on_submit(c, Status.CRIMINAL)
            self._criminal_btn.enabled = enabled
            self._innocent_btn.rect = pygame.Rect(x + btn_w + btn_gap, y, btn_w, btn_h)
            self._innocent_btn.action = lambda c=selected_cell: self.on_submit(c, Status.INNOCENT)
            self._innocent_btn.enabled = enabled
            self._btn_criminal = self._criminal_btn
            self._btn_innocent = self._innocent_btn
            self._btn_criminal.draw(surface, btn_font)
            self._btn_innocent.draw(surface, btn_font)
            y += btn_h + 10

        self._render_messages(surface, x, y, w, body_font, small_font)

    def _render_messages(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> None:
        if y >= self._rect.bottom - 12:
            return
        prev_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(x, y, w, max(0, self._rect.bottom - 8 - y)))

        if self._hint is not None or self._no_forced_msg:
            if self._hint is not None:
                h_cell, _ = self._hint
                hint_txt = f"Consider {h_cell} using the revealed clues."
            else:
                hint_txt = self._no_forced_msg or "No forced move available from current public evidence."
            y = self._draw_box(
                surface, x, y, w, "Solver Hint", hint_txt, THEME.hint_border, THEME.card_face_up, body_font, small_font
            )

        if self._feedback is not None:
            fb = self._feedback
            if fb.kind == "ACCEPTED":
                border, bg = THEME.innocent, THEME.innocent_bg
            elif fb.kind == "NOT_PROVABLE":
                border, bg = THEME.warn, THEME.clue_tint
            elif fb.kind in {"CONTRADICTED", "INCONSISTENT", "TIMEOUT", "ERROR"}:
                border, bg = THEME.criminal, THEME.criminal_bg
            else:
                border, bg = THEME.border, THEME.panel_alt_bg
            self._draw_box(surface, x, y, w, fb.title, fb.detail, border, bg, body_font, small_font)

        surface.set_clip(prev_clip)

    def _draw_box(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        title: str,
        detail: str,
        border: tuple[int, int, int],
        bg: tuple[int, int, int],
        body_font: pygame.font.Font,
        small_font: pygame.font.Font,
    ) -> int:
        lines = wrap_text(detail, small_font, w - 12)
        box_h = 8 + body_font.get_height() + 4 + len(lines) * (small_font.get_height() + 2) + 6
        box = pygame.Rect(x, y, w, box_h)
        pygame.draw.rect(surface, bg, box, border_radius=5)
        pygame.draw.rect(surface, border, box, 1, border_radius=5)

        ty = box.y + 6
        surface.blit(body_font.render(truncate_text(title, body_font, w - 12), True, border), (box.x + 6, ty))
        ty += body_font.get_height() + 4
        for line in lines:
            surface.blit(small_font.render(line, True, THEME.text), (box.x + 6, ty))
            ty += small_font.get_height() + 2
        return box.bottom + 8
