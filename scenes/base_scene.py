"""Base scene interface, reusable button widget, and shared avatar backdrop helpers."""
from collections.abc import Callable
from dataclasses import dataclass
import pygame

from ui.theme import THEME, draw_avatar_fallback, get_avatar_surface, truncate_text


_MINI_NAMES: tuple[str, ...] = (
    "Ada",
    "Bao",
    "Clara",
    "Derek",
    "Eliza",
    "Franz",
    "Grant",
    "Hannah",
    "Ivy",
    "Jonas",
    "Karl",
    "Leo",
)
_MINI_TINTS: tuple[tuple[int, int, int], ...] = (
    THEME.panel_bg,
    THEME.innocent_bg,
    THEME.card_face_down,
    THEME.criminal_bg,
)


def draw_avatar_tile(
    surface: pygame.Surface,
    rect: pygame.Rect,
    char_index: int,
    tint: tuple[int, int, int] | None = None,
) -> None:
    """Draw a rounded mini case-file card containing a centered character avatar."""
    if rect.width < 28 or rect.height < 28:
        return
    bg = tint if tint is not None else _MINI_TINTS[char_index % len(_MINI_TINTS)]
    pygame.draw.rect(surface, bg, rect, border_radius=10)
    pygame.draw.rect(surface, THEME.border, rect, 1, border_radius=10)

    av_sz = max(20, min(rect.width, rect.height) - 16)
    av_rect = pygame.Rect(0, 0, av_sz, av_sz)
    av_rect.center = rect.center
    av_surf = get_avatar_surface(char_index, av_sz)
    if av_surf is not None:
        surface.blit(av_surf, av_rect)
    else:
        draw_avatar_fallback(surface, av_rect, _MINI_NAMES[char_index % len(_MINI_NAMES)], char_index)


def draw_side_avatar_columns(
    surface: pygame.Surface,
    content_rect: pygame.Rect,
    *,
    staggered: bool = False,
    seed_offset: int = 0,
) -> None:
    """Draw symmetrical avatar tile columns in side margins when width permits."""
    screen_w, screen_h = surface.get_size()
    left_margin = content_rect.left
    right_margin = screen_w - content_rect.right
    margin = min(left_margin, right_margin)
    if margin < 110:
        return

    if staggered and margin >= 210:
        tile_sz = 78
        col_gap = 20
        row_gap = 24
        stagger_y = 26
        rows = 3
        cluster_w = tile_sz * 2 + col_gap
        cluster_h = rows * tile_sz + (rows - 1) * row_gap + stagger_y
        top_y = max(20, min(screen_h - cluster_h - 20, content_rect.centery - cluster_h // 2))

        left_x0 = (left_margin - cluster_w) // 2
        right_x0 = content_rect.right + (right_margin - cluster_w) // 2
        for col in range(2):
            for row in range(rows):
                y_l = top_y + row * (tile_sz + row_gap) + (stagger_y if col == 1 else 0)
                rect_l = pygame.Rect(left_x0 + col * (tile_sz + col_gap), y_l, tile_sz, tile_sz)
                draw_avatar_tile(surface, rect_l, seed_offset + col * rows + row)

                y_r = top_y + row * (tile_sz + row_gap) + (stagger_y if col == 0 else 0)
                rect_r = pygame.Rect(right_x0 + col * (tile_sz + col_gap), y_r, tile_sz, tile_sz)
                draw_avatar_tile(surface, rect_r, seed_offset + 6 + col * rows + row)
        return

    tile_sz = 74 if margin >= 140 else 66
    gap = 18
    avail_h = max(tile_sz, min(content_rect.height, screen_h - 48))
    rows = min(5, max(2, (avail_h + gap) // (tile_sz + gap)))
    col_h = rows * tile_sz + (rows - 1) * gap
    top_y = max(20, min(screen_h - col_h - 20, content_rect.centery - col_h // 2))
    left_x = (left_margin - tile_sz) // 2
    right_x = content_rect.right + (right_margin - tile_sz) // 2

    for row in range(rows):
        y = top_y + row * (tile_sz + gap)
        draw_avatar_tile(surface, pygame.Rect(left_x, y, tile_sz, tile_sz), seed_offset + row)
        draw_avatar_tile(surface, pygame.Rect(right_x, y, tile_sz, tile_sz), seed_offset + rows + row)


@dataclass
class UIButton:
    """Clickable rectangular button with hover, active, and disabled states."""

    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    enabled: bool = True
    active: bool = False
    tooltip: str = ""
    hovered: bool = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.enabled:
            bg = THEME.button_disabled
            fg = THEME.text_muted
            border = THEME.border
        elif self.active:
            bg = THEME.accent_hover if self.hovered else THEME.button_active
            fg = THEME.accent_text
            border = THEME.accent_hover
        elif self.hovered:
            bg = THEME.button_hover
            fg = THEME.text
            border = THEME.accent
        else:
            bg = THEME.button_bg
            fg = THEME.text
            border = THEME.border

        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, 1, border_radius=6)

        text = truncate_text(self.label, font, max(8, self.rect.width - 12))
        if text:
            txt_surf = font.render(text, True, fg)
            surface.blit(txt_surf, txt_surf.get_rect(center=self.rect.center))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", None) == 1:
            if self.enabled and self.rect.collidepoint(event.pos):
                self.action()
                return True
        return False


class BaseScene:
    """Lifecycle base class shared by all application scenes."""

    def __init__(self, controller) -> None:
        self.controller = controller

    def on_enter(self) -> None:
        return None

    def handle_event(self, event: pygame.event.Event) -> None:
        return None

    def update(self, dt: float) -> None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        return None

    def on_exit(self) -> None:
        return None

    def on_resize(self, width: int, height: int) -> None:
        return None
