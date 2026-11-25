"""Base scene interface and reusable button widget for Pygame scenes."""
from collections.abc import Callable
from dataclasses import dataclass
import pygame

from ui.theme import THEME, truncate_text


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
            bg = THEME.button_active
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
