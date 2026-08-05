"""Затемнение закрытых секторов (MapRenderer._draw_sector_overlay) - в частности,
регрессия на щель между соседними закрытыми секторами, которая появлялась/пропадала
при смене зума (см. жалобу игрока)."""
import types

import pygame

from src.systems.sector import Sector
from src.ui.map_renderer import MapRenderer

WIDTH, HEIGHT = 900, 600


def _camera(cam_x=0.0, cam_y=0.0, zoom=1.0):
    """Простая линейная камера world->screen, как реальная Camera при нулевом
    повороте: screen = (world - cam) * zoom."""
    return types.SimpleNamespace(
        world_to_screen=lambda x, y, cam_x=cam_x, cam_y=cam_y, zoom=zoom:
            ((x - cam_x) * zoom, (y - cam_y) * zoom),
        zoom=zoom,
    )


def _session_with_two_adjacent_locked_sectors():
    """Два закрытых сектора 300x300 (заведомо помещаются на экран WIDTHxHEIGHT даже
    без зума), стоящих вплотную по x=300 (общая граница)."""
    left = Sector(row=0, col=0, bounds=(0.0, 0.0, 300.0, 300.0), unlocked=False)
    right = Sector(row=0, col=1, bounds=(300.0, 0.0, 600.0, 300.0), unlocked=False)
    return types.SimpleNamespace(map=types.SimpleNamespace(sectors=[left, right])), left, right


def _spy_blits(monkeypatch, screen):
    calls = []
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        calls.append((source.get_size(), (dest[0], dest[1]) if isinstance(dest, tuple) else (dest.x, dest.y)))
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)
    return calls


def test_no_gap_or_overlap_between_adjacent_locked_sectors_at_integer_zoom(monkeypatch):
    session, left, right = _session_with_two_adjacent_locked_sectors()
    camera = _camera(zoom=1.0)
    screen = pygame.Surface((WIDTH, HEIGHT))
    calls = _spy_blits(monkeypatch, screen)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert len(calls) == 2
    (size_a, pos_a), (size_b, pos_b) = calls
    assert pos_a[0] + size_a[0] == pos_b[0], "правый край левого сектора должен точно совпадать с левым краем правого"


def test_no_gap_or_overlap_between_adjacent_locked_sectors_across_fractional_zoom_levels(monkeypatch):
    """Регрессия: щель между секторами то появлялась, то пропадала при смене зума -
    значит баг зависел от дробной части экранных координат. Проверяем на нескольких
    "некруглых" значениях zoom/позиции камеры, а не только на zoom=1.0."""
    checked_cases = 0
    for cam_x, cam_y, zoom in [(137.3, 42.7, 0.5638), (0.0, 0.0, 0.3333),
                                (-88.1, 15.0, 1.734), (500.5, 500.5, 0.777)]:
        session, left, right = _session_with_two_adjacent_locked_sectors()
        camera = _camera(cam_x=cam_x, cam_y=cam_y, zoom=zoom)
        screen = pygame.Surface((WIDTH, HEIGHT))
        calls = _spy_blits(monkeypatch, screen)

        MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

        if len(calls) != 2:
            continue  # один из секторов мог полностью уйти за экран при таком зуме/пане
        checked_cases += 1
        (size_a, pos_a), (size_b, pos_b) = calls
        left_first = pos_a[0] <= pos_b[0]
        first_pos, first_size = (pos_a, size_a) if left_first else (pos_b, size_b)
        second_pos, _second_size = (pos_b, size_b) if left_first else (pos_a, size_a)
        assert first_pos[0] + first_size[0] == second_pos[0], \
            f"щель/нахлёст между секторами при zoom={zoom}, cam=({cam_x},{cam_y})"

    assert checked_cases >= 3, "тест не должен молча пропускать почти все случаи"


def test_unlocked_sectors_get_no_overlay(monkeypatch):
    session, left, right = _session_with_two_adjacent_locked_sectors()
    left.unlocked = True
    right.unlocked = True
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    calls = _spy_blits(monkeypatch, screen)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert calls == []


def test_map_without_sectors_draws_nothing(monkeypatch):
    session = types.SimpleNamespace(map=types.SimpleNamespace(sectors=[]))
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    calls = _spy_blits(monkeypatch, screen)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert calls == []


def test_sector_fully_off_screen_is_skipped_without_crashing():
    left = Sector(row=0, col=0, bounds=(100000.0, 100000.0, 102000.0, 102000.0), unlocked=False)
    session = types.SimpleNamespace(map=types.SimpleNamespace(sectors=[left]))
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)
