"""Main menu scene with Play, Tutorial, and Exit actions."""
import pygame

from scenes.base_scene import BaseScene, UIButton, draw_side_avatar_columns
from ui.theme import THEME, get_font, wrap_text


_MENU_DESC = (
    "Deduce every character's role strictly from public evidence. "
    "No guessing is allowed: every verdict must follow logically from revealed clues."
)


def _draw_grid_icon(surface: pygame.Surface, rect: pygame.Rect) -> None:
    colors = (
        THEME.innocent,
        THEME.card_face_down,
        THEME.criminal,
        THEME.card_face_down,
        THEME.innocent,
        THEME.card_face_down,
        THEME.criminal,
        THEME.card_face_down,
        THEME.innocent,
    )
    cell_sz = 7
    gap = 2
    ox = rect.x + (rect.width - (cell_sz * 3 + gap * 2)) // 2
    oy = rect.y + (rect.height - (cell_sz * 3 + gap * 2)) // 2
    for idx, fill in enumerate(colors):
        row, col = divmod(idx, 3)
        cell = pygame.Rect(ox + col * (cell_sz + gap), oy + row * (cell_sz + gap), cell_sz, cell_sz)
        pygame.draw.rect(surface, fill, cell, border_radius=2)
        if fill == THEME.card_face_down:
            pygame.draw.rect(surface, THEME.border, cell, 1, border_radius=2)


def _draw_magnifier_icon(surface: pygame.Surface, rect: pygame.Rect) -> None:
    cx, cy = rect.x + 10, rect.y + 10
    radius = 8
    pygame.draw.line(surface, THEME.text, (cx + 5, cy + 5), (rect.right - 3, rect.bottom - 3), 3)
    pygame.draw.circle(surface, THEME.card_face_up, (cx, cy), radius)
    pygame.draw.circle(surface, THEME.accent, (cx, cy), radius, 2)
    pygame.draw.circle(surface, THEME.accent, (cx - 2, cy - 2), 2)


class MenuScene(BaseScene):
    """Entry scene offering case selection, rules tutorial, and application exit."""

    def __init__(self, controller) -> None:
        super().__init__(controller)
        self._size = (1280, 720)
        self._card_rect = pygame.Rect(0, 0, 660, 440)
        self._desc_lines: list[str] = []
        self._title_y = 0
        self._divider_y = 0
        self._desc_y = 0
        self._title_size = 36
        self._body_size = 15
        self._buttons: list[UIButton] = []

    def on_enter(self) -> None:
        self._rebuild_layout()

    def on_resize(self, width: int, height: int) -> None:
        self._size = (max(640, width), max(480, height))
        self._rebuild_layout()

    def _rebuild_layout(self) -> None:
        w, h = self._size
        card_w = min(660, max(420, w - 80))

        self._title_size = 36 if w >= 720 else 32
        self._body_size = 15 if w >= 720 else 14
        title_font = get_font(self._title_size, bold=True)
        body_font = get_font(self._body_size)
        hint_font = get_font(12)

        self._desc_lines = wrap_text(_MENU_DESC, body_font, card_w - 84)
        desc_step = body_font.get_height() + 4
        desc_h = len(self._desc_lines) * desc_step

        compact_h = h < 540
        top_pad = 26 if compact_h else 36
        title_gap = 16 if compact_h else 22
        btn_top_gap = 18 if compact_h else 26
        btn_h = 44 if compact_h else 52
        btn_gap = 10 if compact_h else 14
        footer_gap = 18 if compact_h else 24
        bottom_pad = 16 if compact_h else 22

        buttons_h = btn_h * 3 + btn_gap * 2
        needed_h = (
            top_pad
            + title_font.get_height()
            + title_gap
            + desc_h
            + btn_top_gap
            + buttons_h
            + footer_gap
            + hint_font.get_height()
            + bottom_pad
        )
        card_h = min(h - 48, max(440 if not compact_h else 380, needed_h))
        shift_up = 40 if h >= 640 else max(0, (h - card_h) // 6)
        card_y = max(24, (h - card_h) // 2 - shift_up)
        self._card_rect = pygame.Rect((w - card_w) // 2, card_y, card_w, card_h)

        slack = max(0, card_h - needed_h)
        y = self._card_rect.y + top_pad + slack // 3
        self._title_y = y
        self._divider_y = y + title_font.get_height() + title_gap // 2
        y += title_font.get_height() + title_gap
        self._desc_y = y
        start_y = y + desc_h + btn_top_gap

        btn_w = min(340, card_w - 80)
        btn_x = self._card_rect.centerx - btn_w // 2
        self._buttons = [
            UIButton(
                pygame.Rect(btn_x, start_y, btn_w, btn_h),
                "Play",
                self.controller.show_case_select,
                active=True,
                tooltip="Choose a puzzle case",
            ),
            UIButton(
                pygame.Rect(btn_x, start_y + (btn_h + btn_gap), btn_w, btn_h),
                "Tutorial",
                self.controller.show_tutorial,
                tooltip="Read deduction rules and shortcuts",
            ),
            UIButton(
                pygame.Rect(btn_x, start_y + (btn_h + btn_gap) * 2, btn_w, btn_h),
                "Exit",
                self.controller.close,
                tooltip="Quit Griductive Solver",
            ),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self._buttons:
            self._rebuild_layout()

        for btn in self._buttons:
            if btn.handle_event(event):
                return

        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p):
            self.controller.show_case_select()
        elif event.key == pygame.K_t:
            self.controller.show_tutorial()
        elif event.key in (pygame.K_ESCAPE, pygame.K_q):
            self.controller.close()

    def render(self, surface: pygame.Surface) -> None:
        if surface.get_size() != self._size or not self._buttons:
            self.on_resize(*surface.get_size())

        surface.fill(THEME.bg)
        draw_side_avatar_columns(surface, self._card_rect, staggered=True, seed_offset=0)

        shadow_rect = self._card_rect.move(0, 6)
        pygame.draw.rect(surface, (222, 217, 206), shadow_rect, border_radius=12)
        pygame.draw.rect(surface, THEME.panel_bg, self._card_rect, border_radius=12)
        pygame.draw.rect(surface, THEME.border, self._card_rect, 1, border_radius=12)

        title_font = get_font(self._title_size, bold=True)
        body_font = get_font(self._body_size)
        btn_font = get_font(15, bold=True)
        hint_font = get_font(12)

        lead_surf = title_font.render("Griductive", True, THEME.accent)
        tail_surf = title_font.render("Solver", True, THEME.criminal)
        space_w = title_font.size(" ")[0]
        total_w = lead_surf.get_width() + space_w + tail_surf.get_width()
        title_x = self._card_rect.centerx - total_w // 2
        surface.blit(lead_surf, (title_x, self._title_y))
        surface.blit(tail_surf, (title_x + lead_surf.get_width() + space_w, self._title_y))

        icon_sz = 26
        icon_y = self._title_y + (title_font.get_height() - icon_sz) // 2
        if title_x - 14 - icon_sz >= self._card_rect.x + 14:
            _draw_grid_icon(surface, pygame.Rect(title_x - 14 - icon_sz, icon_y, icon_sz, icon_sz))
            _draw_magnifier_icon(surface, pygame.Rect(title_x + total_w + 14, icon_y, icon_sz, icon_sz))

        div_w = min(180, self._card_rect.width - 140)
        div_x = self._card_rect.centerx - div_w // 2
        pygame.draw.line(surface, THEME.border, (div_x, self._divider_y), (div_x + div_w, self._divider_y), 1)
        pygame.draw.line(
            surface,
            THEME.accent,
            (self._card_rect.centerx - 24, self._divider_y),
            (self._card_rect.centerx + 24, self._divider_y),
            2,
        )

        y = self._desc_y
        for line in self._desc_lines:
            line_surf = body_font.render(line, True, THEME.text_muted)
            surface.blit(line_surf, line_surf.get_rect(centerx=self._card_rect.centerx, top=y))
            y += body_font.get_height() + 4

        for btn in self._buttons:
            btn.draw(surface, btn_font)

        footer = "[Enter / P] Play   [T] Tutorial   [Esc / Q] Exit"
        footer_surf = hint_font.render(footer, True, THEME.text_muted)
        surface.blit(
            footer_surf,
            footer_surf.get_rect(centerx=self._card_rect.centerx, bottom=self._card_rect.bottom - 18),
        )
