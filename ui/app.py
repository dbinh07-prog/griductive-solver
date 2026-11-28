"""Pygame desktop entry loop for Griductive Solver."""
import pygame

from app_controller import AppController
from game.factory import create_session
from ui.theme import reset_runtime_caches


DEFAULT_WINDOW_SIZE = (1280, 720)
MIN_WINDOW_SIZE = (960, 600)


def run(session_factory=None) -> None:
    """Launch the resizable 60 FPS Pygame application loop."""
    factory = session_factory or create_session
    reset_runtime_caches()
    pygame.init()
    controller = None
    try:
        screen = pygame.display.set_mode(DEFAULT_WINDOW_SIZE, pygame.RESIZABLE)
        pygame.display.set_caption("Griductive Solver")
        clock = pygame.time.Clock()
        controller = AppController(factory)
        controller.show_menu()
        controller.on_resize(*screen.get_size())
        while not controller.should_quit:
            dt = min(0.1, clock.tick(60) / 1000.0)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    controller.close()
                    break
                if event.type == pygame.VIDEORESIZE:
                    width = max(MIN_WINDOW_SIZE[0], event.w)
                    height = max(MIN_WINDOW_SIZE[1], event.h)
                    cur = pygame.display.get_surface()
                    if cur is None or cur.get_size() != (width, height):
                        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    else:
                        screen = cur
                    controller.on_resize(width, height)
                else:
                    controller.handle_event(event)

            if controller.should_quit:
                break
            controller.update(dt)
            controller.render(screen)
            pygame.display.flip()
    finally:
        if controller is not None:
            controller.close()
        reset_runtime_caches()
        pygame.quit()
