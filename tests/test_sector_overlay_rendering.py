"""Затемнение закрытых секторов и цветные границы сетки секторов
(MapRenderer._draw_sector_overlay) - в частности, регрессия на щель между соседними
закрытыми секторами, которая появлялась/пропадала при смене зума (см. жалобу игрока),
и границы, которые теперь рисуются у ЛЮБОГО сектора (не только закрытого), чтобы
сетка была видна и после открытия (см. запрос пользователя про цветную полосу)."""
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


class _SpySurface(pygame.Surface):
    """pygame.Surface - C-тип без __dict__ на экземпляре, поэтому
    monkeypatch.setattr(screen, "blit", ...) падает с "attribute is
    read-only"; вместо этого переопределяем blit в Python-подклассе."""

    def __init__(self, size):
        super().__init__(size)
        self.blit_calls = []

    def blit(self, source, dest, *a, **k):
        self.blit_calls.append(
            (source.get_size(), (dest[0], dest[1]) if isinstance(dest, tuple) else (dest.x, dest.y))
        )
        return super().blit(source, dest, *a, **k)


def _spy_draw_rects(monkeypatch):
    calls = []

    def spy_rect(screen, color, rect, width=0):
        calls.append((tuple(color), (rect.left, rect.top, rect.width, rect.height), width))

    monkeypatch.setattr(pygame.draw, "rect", spy_rect)
    return calls


def test_no_gap_or_overlap_between_adjacent_locked_sectors_at_integer_zoom():
    session, left, right = _session_with_two_adjacent_locked_sectors()
    camera = _camera(zoom=1.0)
    screen = _SpySurface((WIDTH, HEIGHT))

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    calls = screen.blit_calls
    assert len(calls) == 2
    (size_a, pos_a), (size_b, pos_b) = calls
    assert pos_a[0] + size_a[0] == pos_b[0], "правый край левого сектора должен точно совпадать с левым краем правого"


def test_no_gap_or_overlap_between_adjacent_locked_sectors_across_fractional_zoom_levels():
    """Регрессия: щель между секторами то появлялась, то пропадала при смене зума -
    значит баг зависел от дробной части экранных координат. Проверяем на нескольких
    "некруглых" значениях zoom/позиции камеры, а не только на zoom=1.0."""
    checked_cases = 0
    for cam_x, cam_y, zoom in [(137.3, 42.7, 0.5638), (0.0, 0.0, 0.3333),
                                (-88.1, 15.0, 1.734), (500.5, 500.5, 0.777)]:
        session, left, right = _session_with_two_adjacent_locked_sectors()
        camera = _camera(cam_x=cam_x, cam_y=cam_y, zoom=zoom)
        screen = _SpySurface((WIDTH, HEIGHT))

        MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

        calls = screen.blit_calls
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


def test_unlocked_sectors_get_no_overlay():
    session, left, right = _session_with_two_adjacent_locked_sectors()
    left.unlocked = True
    right.unlocked = True
    camera = _camera()
    screen = _SpySurface((WIDTH, HEIGHT))

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert screen.blit_calls == []


def test_map_without_sectors_draws_nothing():
    session = types.SimpleNamespace(map=types.SimpleNamespace(sectors=[]))
    camera = _camera()
    screen = _SpySurface((WIDTH, HEIGHT))

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert screen.blit_calls == []


def test_locked_sector_border_uses_locked_color(monkeypatch):
    session, left, right = _session_with_two_adjacent_locked_sectors()
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    rect_calls = _spy_draw_rects(monkeypatch)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    colors_used = {c for c, _rect, _w in rect_calls}
    assert MapRenderer.SECTOR_BORDER_COLOR_LOCKED in colors_used
    assert MapRenderer.SECTOR_BORDER_COLOR_UNLOCKED not in colors_used


def test_unlocked_sector_border_uses_unlocked_color(monkeypatch):
    """Регрессия для запроса пользователя: сетка секторов должна оставаться видна и
    после открытия - границу рисуем даже у sector.unlocked=True (просто без тёмной
    заливки, которая осталась только у закрытых)."""
    session, left, right = _session_with_two_adjacent_locked_sectors()
    left.unlocked = True
    right.unlocked = True
    camera = _camera()
    screen = _SpySurface((WIDTH, HEIGHT))
    rect_calls = _spy_draw_rects(monkeypatch)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    assert screen.blit_calls == [], "у открытых секторов не должно быть тёмной заливки"
    colors_used = {c for c, _rect, _w in rect_calls}
    assert MapRenderer.SECTOR_BORDER_COLOR_UNLOCKED in colors_used
    assert MapRenderer.SECTOR_BORDER_COLOR_LOCKED not in colors_used


def test_border_between_locked_and_unlocked_sector_prefers_locked_color(monkeypatch):
    """На общей границе открытого и закрытого сектора должен быть виден более важный
    сигнал "закрыто" - закрытый цвет рисуется вторым проходом поверх открытого."""
    session, left, right = _session_with_two_adjacent_locked_sectors()
    left.unlocked = True  # правый (right) остаётся закрытым
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    rect_calls = _spy_draw_rects(monkeypatch)

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)

    # Последний нарисованный на общей границе x=300 прямоугольник должен быть
    # закрытого сектора (правого) - т.к. закрытые рисуются вторым проходом.
    shared_edge_calls = [call for call in rect_calls if call[1][0] == 300 or call[1][0] + call[1][2] == 300]
    assert shared_edge_calls, "должна быть хотя бы одна граница, задевающая общий стык x=300"
    assert shared_edge_calls[-1][0] == MapRenderer.SECTOR_BORDER_COLOR_LOCKED


def test_sector_fully_off_screen_is_skipped_without_crashing():
    left = Sector(row=0, col=0, bounds=(100000.0, 100000.0, 102000.0, 102000.0), unlocked=False)
    session = types.SimpleNamespace(map=types.SimpleNamespace(sectors=[left]))
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))

    MapRenderer()._draw_sector_overlay(screen, camera, session, WIDTH, HEIGHT)
