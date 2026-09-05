"""Состояние выбранной башни, подсказки и кратковременные боевые сигналы."""
import math

import pygame

from src.localization.loc import loc


def wrapped_lines(text, font, width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + ([line] if line else [])


def draw_card(screen, font, texts, x, bottom, width):
    lines = [line for text in texts for line in wrapped_lines(text, font, width - 20)]
    line_height = font.get_linesize() + 3
    rect = pygame.Rect(x, bottom - len(lines) * line_height - 20,
                       width, len(lines) * line_height + 20)
    pygame.draw.rect(screen, (22, 29, 40), rect, border_radius=5)
    pygame.draw.rect(screen, (90, 140, 190), rect, 1, border_radius=5)
    for i, line in enumerate(lines):
        screen.blit(font.render(line, True, (230, 235, 240)),
                    (rect.x + 10, rect.y + 10 + i * line_height))
    return rect


class TacticalOverlay:
    def __init__(self):
        self.drops = []
        self.attacks = {}

    def clear(self):
        self.drops.clear()
        self.attacks.clear()

    def handle_event(self, event, now, **data):
        if event == "ai_module_dropped":
            self.drops.append((now + 6, data["module_key"]))
            self.drops = self.drops[-3:]
        elif event in ("tower_hit", "base_hit") and data.get("position") is not None:
            pos = data["position"]
            self.attacks[(pos.x, pos.y)] = (now + 4, pos)
            if len(self.attacks) > 8:
                del self.attacks[next(iter(self.attacks))]

    @staticmethod
    def tower_details(tower):
        powered = loc.get("hud.power_on" if tower.is_powered else "hud.power_off")
        target = tower.current_target
        target_name = loc.get("hud.target_none")
        if target is not None and target.is_alive():
            key = getattr(target, "type_name", None)
            target_name = loc.get(f"enemy.{key}") if key else loc.get("hud.target_nest")
        lines = [loc.get("hud.tower_health", hp=int(tower.health), max_hp=int(tower.max_health)),
                 loc.get("hud.tower_power", value=powered),
                 loc.get(f"hud.activity_{tower.activity_reason}")]
        if tower.IS_COMBAT_TOWER:
            lines.append(loc.get("hud.current_target", name=target_name))
            if tower.ai_module:
                lines.append(loc.get(f"hud.ai_desc_{tower.ai_module}"))
        return lines

    @staticmethod
    def marker_position(camera, position, viewport):
        sx, sy = camera.world_to_screen(position.x, position.y)
        if viewport.collidepoint(sx, sy):
            return None
        cx, cy = viewport.center
        dx, dy = sx - cx, sy - cy
        scale = min((viewport.width / 2) / max(abs(dx), 0.001),
                    (viewport.height / 2) / max(abs(dy), 0.001))
        return (int(cx + dx * scale), int(cy + dy * scale)), math.atan2(dy, dx)

    def draw_marker(self, screen, font, camera, position, viewport, label, color):
        marker = self.marker_position(camera, position, viewport)
        if marker is None:
            sx, sy = camera.world_to_screen(position.x, position.y)
            point = (int(sx), int(sy))
            pygame.draw.circle(screen, color, point, 12, 2)
        else:
            point, angle = marker
            dx, dy = math.cos(angle), math.sin(angle)
            px, py = -dy, dx
            points = [(point[0] + dx * 9, point[1] + dy * 9),
                      (point[0] - dx * 8 + px * 6, point[1] - dy * 8 + py * 6),
                      (point[0] - dx * 8 - px * 6, point[1] - dy * 8 - py * 6)]
            pygame.draw.polygon(screen, color, points)
        text = font.render(label, True, color)
        rect = text.get_rect(midtop=(point[0], point[1] + 14))
        rect.clamp_ip(viewport)
        pygame.draw.rect(screen, (22, 29, 40), rect.inflate(6, 4))
        screen.blit(text, rect)

    def render(self, screen, camera, session, controller, options, hud, font, width, height):
        operator_mode = getattr(controller, "operator_mode", False)
        if operator_mode:
            options = []
        now = session.elapsed_time
        self.drops = [(expiry, key) for expiry, key in self.drops if expiry > now]
        self.attacks = {key: value for key, value in self.attacks.items() if value[0] > now}
        top = hud.TOP_BAR_HEIGHT + (110 if session.objectives else 24)
        viewport = pygame.Rect(22, top, width - 44,
                               height - hud.BOTTOM_BAR_HEIGHT - top - 24)
        landings = [landing for strategy in session.threat_strategies.values()
                    for landing in getattr(strategy, "pending_landings", [])]
        if landings:
            landing = min(landings, key=lambda p: sum(
                (a - b) ** 2 for a, b in zip(camera.world_to_screen(p.position.x, p.position.y),
                                            viewport.center)))
            self.draw_marker(screen, font, camera, landing.position, viewport,
                             loc.get("hud.landing_alert", seconds=math.ceil(landing.time_remaining)),
                             (255, 190, 75))
        for _expiry, position in self.attacks.values():
            if self.marker_position(camera, position, viewport) is not None:
                self.draw_marker(screen, font, camera, position, viewport,
                                 loc.get("hud.attack_alert"), (255, 100, 90))
        if getattr(session, "story", False) and session.map.fauna_nests:
            self.draw_marker(screen, font, camera, session.map.fauna_nests[0].position,
                             viewport, loc.get("hud.mission_nest"), (130, 220, 130))

        tower = controller.selected_module
        bottom = height - hud.BOTTOM_BAR_HEIGHT - 8
        if tower and controller.selected_tower_type is None:
            draw_card(screen, font, self.tower_details(tower), 16, bottom, min(320, width - 32))
        elif getattr(session, "story", False) and not controller.selected_tower_type and not operator_mode:
            draw_card(screen, font, [loc.get("mission.story_hint")], 16, bottom, 320)
        mouse = pygame.mouse.get_pos()
        tooltip = None
        slots = hud._layout_build_panel(options, width, height)
        for rect, option in slots:
            if rect.collidepoint(mouse) and option["type"] in ("laser", "bullet", "mortar"):
                tooltip = loc.get(f"hud.role_{option['type']}")
        build_left = slots[0][0].left if slots else width // 2
        for rect, key in hud._layout_ai_module_buttons(
                controller, 16, height - hud.BOTTOM_BAR_HEIGHT + 10,
                build_left - 26, hud.BOTTOM_BAR_HEIGHT - 20):
            if rect.collidepoint(mouse):
                tooltip = loc.get(f"hud.ai_desc_{key}")
        if tooltip:
            draw_card(screen, font, [tooltip], max(16, width // 2 - 180), bottom, 360)
        if self.drops:
            texts = [loc.get("hud.module_drop", name=loc.get(f"hud.ai_module_full_{key}"))
                     for _expiry, key in self.drops]
            card_width = min(360, width - 32)
            line_count = sum(len(wrapped_lines(text, font, card_width - 20)) for text in texts)
            bottom = hud.TOP_BAR_HEIGHT + 8 + 20 + line_count * (font.get_linesize() + 3)
            draw_card(screen, font, texts, 16, bottom, card_width)
