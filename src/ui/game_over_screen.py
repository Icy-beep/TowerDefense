"""Экран победы/поражения."""
import pygame

from src.enums import GameState
from src.localization.loc import loc


class GameOverScreen:
    """Оверлей с надписью о победе или поражении."""

    def render(self, screen, session, width, height):
        """Рисует оверлей, если игра завершена."""
        if session.state == GameState.GAME_OVER:
            self._draw_overlay(screen, width, height, loc.get("game_over.defeat"), (255, 50, 50))
        elif session.state == GameState.VICTORY:
            self._draw_overlay(screen, width, height, loc.get("game_over.victory"), (50, 255, 50))

    def _draw_overlay(self, screen, width, height, text, color):
        """Рисует затемнение и текст по центру экрана."""
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, (0, 0))
        big_font = pygame.font.SysFont("Arial", 48, bold=True)
        txt = big_font.render(text, True, color)
        screen.blit(txt, txt.get_rect(center=(width // 2, height // 2)))
