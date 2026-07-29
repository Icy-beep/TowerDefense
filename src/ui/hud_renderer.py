"""HudRenderer — HUD-панели поверх игрового поля: деньги/здоровье базы/
номер волны, подсказки по управлению, информация о текущем выборе
(строим башню / выделена башня / ничего не выбрано).

Выделено из game_view.py отдельно от MapRenderer: разметку HUD можно
будет менять, не трогая отрисовку самого игрового поля."""
import pygame


class HudRenderer:
    def render(self, screen, camera, session, controller, tower_options, width, height, font, small_font):
        state = controller.get_game_state()
        alpha = 170
        pad = 10

        self._draw_status_panel(screen, state, font, pad, alpha)
        self._draw_controls_panel(screen, camera, small_font, pad, alpha, width, height)
        self._draw_selection_panel(screen, state, controller, tower_options, small_font, width, height)

    def _draw_status_panel(self, screen, state, font, pad, alpha):
        surf1 = pygame.Surface((250, 100), pygame.SRCALPHA)
        surf1.fill((20, 25, 35, alpha))
        screen.blit(surf1, (pad, pad))

        screen.blit(font.render(f"Деньги: {state['credits']}", True, (255, 215, 0)), (pad + 10, pad + 10))
        screen.blit(
            font.render(f"Целостность базы: {state['base_health']}/{state['max_base_health']}", True, (255, 100, 100)),
            (pad + 10, pad + 40))
        screen.blit(
            font.render(f"Волна: {state['current_wave']}/{state['total_waves']}", True, (100, 200, 255)),
            (pad + 10, pad + 70))

    def _draw_controls_panel(self, screen, camera, small_font, pad, alpha, width, height):
        surf2 = pygame.Surface((300, 120), pygame.SRCALPHA)
        surf2.fill((20, 25, 35, alpha))
        screen.blit(surf2, (pad, height - 130))

        screen.blit(small_font.render(
            f"Позиция камеры: {int(camera.x)}, {int(camera.y)} | Зум: {int(camera.zoom * 100)}%", True,
            (180, 180, 180)), (pad + 10, height - 120))
        screen.blit(small_font.render("WASD: Ходить | SCROLL: Зум | R: Камеру на базу", True, (150, 150, 150)),
                    (pad + 10, height - 100))
        screen.blit(small_font.render("1-3: Выбрать башню | SPACE: Начать волну", True, (150, 150, 150)),
                    (pad + 10, height - 80))
        screen.blit(small_font.render("ЛКМ: Поставить/Выбрать | ПКМ: Отменить выбор", True, (150, 150, 150)),
                    (pad + 10, height - 60))
        screen.blit(small_font.render("U: Улучшить башню | P: Пауза | ESC: Закрыть игру", True, (150, 150, 150)),
                    (pad + 10, height - 40))

    def _build_selection_info(self, state, controller, tower_options):
        info_lines = []
        if state['selected_tower']:
            opt = next((o for o in tower_options if o["type"] == state['selected_tower']), None)
            label = opt["name"] if opt else state['selected_tower']
            info_lines.append(f"Строить: {label}")
            info_lines.append("ЛКМ: Поставить | ПКМ: Отмена")
        elif controller.selected_module:
            mod = controller.selected_module
            info_lines.append(f"Уровень башни{mod.level} / {mod.max_level}")
            if mod.can_upgrade():
                cost = mod.get_upgrade_cost()
                can_afford = state['credits'] >= cost
                info_lines.append(f"Улучшить: {cost} cr {'ДА' if can_afford else 'НЕТ'}")
            else:
                info_lines.append("Макс. уровень")
        else:
            info_lines.append("Ничего не выбрано")
        return info_lines

    def _draw_selection_panel(self, screen, state, controller, tower_options, small_font, width, height):
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
