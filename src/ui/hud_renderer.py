"""HUD-панели поверх игрового поля."""
import pygame

from src.enums import ArmorType, Faction
from src.localization.loc import loc

ENEMY_DISPLAY_KEYS = {
    "drone_walker": "enemy.drone_walker",
    "giant_roach": "enemy.giant_roach",
    "scout_drone": "enemy.scout_drone",
    "heavy_assault_drone": "enemy.heavy_assault_drone",
    "bio_titan": "enemy.bio_titan",
    "medic_drone": "enemy.medic_drone",
}

ARMOR_LABEL_KEYS = {
    ArmorType.LIGHT: "armor.light",
    ArmorType.HEAVY: "armor.heavy",
    ArmorType.ENERGY_SHIELDED: "armor.energy_shielded",
    ArmorType.ORGANIC: "armor.organic",
}

FACTION_LABEL_KEYS = {
    Faction.CORPORATION: "faction.corporation",
    Faction.FAUNA: "faction.fauna",
}


class HudRenderer:
    """Рисует HUD-панели поверх игрового поля."""

    def render(self, screen, camera, session, controller, tower_options, width, height, font, small_font):
        """Рисует все панели HUD."""
        state = controller.get_game_state()
        alpha = 170
        pad = 10

        self._draw_status_panel(screen, state, controller, font, pad, alpha)
        self._draw_missions_panel(screen, session, small_font, pad, alpha, width)
        self._draw_controls_panel(screen, camera, small_font, pad, alpha, width, height)
        self._draw_selection_panel(screen, state, controller, tower_options, small_font, width, height)

    def _draw_status_panel(self, screen, state, controller, font, pad, alpha):
        """Рисует панель с деньгами, здоровьем базы и прогрессом по времени
        под давлением угроз."""
        surf1 = pygame.Surface((360, 125), pygame.SRCALPHA)
        surf1.fill((20, 25, 35, alpha))
        screen.blit(surf1, (pad, pad))

        screen.blit(font.render(loc.get("hud.money", credits=state['credits']), True, (255, 215, 0)),
                    (pad + 10, pad + 10))
        screen.blit(
            font.render(loc.get("hud.base_health", hp=state['base_health'], max_hp=state['max_base_health']),
                        True, (255, 100, 100)),
            (pad + 10, pad + 40))

        target = state['survive_duration_target']
        current = min(state['elapsed_time'], target)
        screen.blit(
            font.render(loc.get("hud.survive_progress", current=int(current), target=int(target)),
                        True, (100, 200, 255)),
            (pad + 10, pad + 70))

        remaining = max(0.0, target - state['elapsed_time'])
        color = (150, 255, 150) if remaining <= 0 else (200, 200, 100)
        screen.blit(font.render(loc.get("hud.survive_remaining", seconds=remaining), True, color),
                    (pad + 10, pad + 100))

    def _draw_missions_panel(self, screen, session, small_font, pad, alpha, width):
        """Рисует панель заданий в правом верхнем углу."""
        objectives = getattr(session, "objectives", [])
        if not objectives:
            return

        line_height = 22
        w = 340
        h = len(objectives) * line_height + 35
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((20, 25, 35, alpha))
        x = width - w - pad
        screen.blit(surf, (x, pad))

        screen.blit(small_font.render(loc.get("mission.title"), True, (200, 200, 255)),
                    (x + 10, pad + 8))

        for i, objective in enumerate(objectives):
            text = objective.describe(session)
            if objective.completed:
                color = (100, 255, 100)
                text += f" — {loc.get('mission.status_completed')}"
            elif objective.failed:
                color = (255, 100, 100)
                text += f" — {loc.get('mission.status_failed')}"
            else:
                color = (230, 230, 230)
            screen.blit(small_font.render(text, True, color), (x + 10, pad + 32 + i * line_height))

    def _draw_controls_panel(self, screen, camera, small_font, pad, alpha, width, height):
        """Рисует панель с подсказками по управлению."""
        surf2 = pygame.Surface((300, 160), pygame.SRCALPHA)
        surf2.fill((20, 25, 35, alpha))
        screen.blit(surf2, (pad, height - 170))

        screen.blit(small_font.render(
            loc.get("hud.camera_info", x=int(camera.x), y=int(camera.y), zoom=int(camera.zoom * 100)),
            True, (180, 180, 180)), (pad + 10, height - 160))
        screen.blit(small_font.render(loc.get("hud.controls_move"), True, (150, 150, 150)),
                    (pad + 10, height - 140))
        screen.blit(small_font.render(loc.get("hud.controls_drag"), True, (150, 150, 150)),
                    (pad + 10, height - 120))
        screen.blit(small_font.render(loc.get("hud.controls_build"), True, (150, 150, 150)),
                    (pad + 10, height - 100))
        screen.blit(small_font.render(loc.get("hud.controls_select"), True, (150, 150, 150)),
                    (pad + 10, height - 80))
        screen.blit(small_font.render(loc.get("hud.controls_misc"), True, (150, 150, 150)),
                    (pad + 10, height - 60))
        screen.blit(small_font.render(loc.get("hud.controls_alt"), True, (150, 150, 150)),
                    (pad + 10, height - 40))

    def _build_selection_info(self, state, controller, tower_options):
        """Собирает строки текста для панели выбора."""
        info_lines = []
        if state['selected_tower']:
            opt = next((o for o in tower_options if o["type"] == state['selected_tower']), None)
            label = opt["name"] if opt else state['selected_tower']
            info_lines.append(loc.get("hud.build_label", name=label))
            info_lines.append(loc.get("hud.build_hint"))
        elif controller.selected_module:
            mod = controller.selected_module
            info_lines.append(loc.get("hud.tower_level", level=mod.level, max_level=mod.max_level))
            if mod.can_upgrade():
                cost = mod.get_upgrade_cost()
                can_afford = state['credits'] >= cost
                status = loc.get("hud.upgrade_yes") if can_afford else loc.get("hud.upgrade_no")
                info_lines.append(loc.get("hud.upgrade_cost", cost=cost, status=status))
            else:
                info_lines.append(loc.get("hud.max_level"))
        elif controller.selected_enemy:
            enemy = controller.selected_enemy
            name_key = ENEMY_DISPLAY_KEYS.get(getattr(enemy, "type_name", None))
            name = loc.get(name_key) if name_key else type(enemy).__name__
            armor_key = ARMOR_LABEL_KEYS.get(enemy.armor)
            armor_label = loc.get(armor_key) if armor_key else str(enemy.armor)
            faction_key = FACTION_LABEL_KEYS.get(getattr(enemy, "faction", None))
            faction_label = loc.get(faction_key) if faction_key else None
            info_lines.append(loc.get("hud.enemy_label", name=name))
            if faction_label:
                info_lines.append(loc.get("hud.enemy_faction", faction=faction_label))
            info_lines.append(loc.get("hud.enemy_hp", hp=int(enemy.health), max_hp=int(enemy.max_health)))
            info_lines.append(loc.get("hud.enemy_stats", armor=armor_label, speed=int(enemy.speed)))
            info_lines.append(loc.get("hud.enemy_reward", reward=enemy.reward))
        else:
            info_lines.append(loc.get("hud.nothing_selected"))
        return info_lines

    def _draw_selection_panel(self, screen, state, controller, tower_options, small_font, width, height):
        """Рисует панель с информацией о текущем выборе."""
        info_lines = self._build_selection_info(state, controller, tower_options)

        w3 = max(len(line) * 8 for line in info_lines) + 40
        h3 = len(info_lines) * 22 + 25
        surf3 = pygame.Surface((w3, h3), pygame.SRCALPHA)
        surf3.fill((20, 25, 35, 170))
        x3 = (width - w3) // 2
        y3 = height - h3 - 10
        screen.blit(surf3, (x3, y3))

        for i, line in enumerate(info_lines):
            col = (255, 255, 255)
            if "НЕТ" in line:
                col = (255, 100, 100)
            elif "ДА" in line:
                col = (100, 255, 100)
            elif "МАКСИМУМ" in line:
                col = (255, 215, 0)
            screen.blit(small_font.render(line, True, col), (x3 + 10, y3 + 10 + i * 22))
