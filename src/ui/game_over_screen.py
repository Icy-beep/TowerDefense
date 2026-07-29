"""GameOverScreen — оверлей поверх игрового поля при победе/поражении.

Единственный потребитель session.state здесь — GameState.GAME_OVER /
GameState.VICTORY, за которые отвечает GameStateManager
(core/game_state.py); этот модуль только их отображает."""
import pygame

from src.enums import GameState


class GameOverScreen:
    def render(self, screen, session, width, height):
        if session.state == GameState.GAME_OVER:
            self._draw_overlay(screen, width, height, "ПОРАЖЕНИЕ", (255, 50, 50))
        elif session.state == GameState.VICTORY:
            self._draw_overlay(screen, width, height, "ПОБЕДА", (50, 255, 50))

    def _draw_overlay(self, screen, width, height, text, color):
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, (0, 0))
        big_font = pygame.font.SysFont("Arial", 48, bold=True)
        txt = big_font.render(text, True, color)
        screen.blit(txt, txt.get_rect(center=(width // 2, height // 2)))
