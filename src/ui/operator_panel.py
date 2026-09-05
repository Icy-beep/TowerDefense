import math

import pygame

from src.localization.loc import loc
from src.ui.tactical_overlay import wrapped_lines


class OperatorPanel:
    @staticmethod
    def toggle_rect(width, height):
        return pygame.Rect(width - 242, height - 78, 220, 30)

    @staticmethod
    def choice_rects(width, height):
        return [(pygame.Rect(width // 2 - 290, height // 2 - 105 + i * 135, 580, 115), kind)
                for i, kind in enumerate(("assault", "engineer"))]

    def handle_choice(self, event, width, height):
        if event.type == pygame.KEYDOWN:
            return {pygame.K_1: "assault", pygame.K_2: "engineer"}.get(event.key)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return next((kind for rect, kind in self.choice_rects(width, height)
                         if rect.collidepoint(event.pos)), None)
        return None

    def render(self, screen, session, controller, font, width, height, menu_open, error):
        operator = session.operator
        if operator and not controller.operator_mode:
            if operator.is_alive():
                status = loc.get("operator.auto_status", hp=int(operator.health))
            else:
                status = loc.get("operator.dead_status", seconds=max(
                    0, math.ceil(session.operator_respawn_at - session.elapsed_time)))
            rendered = font.render(status, True, (255, 210, 125))
            screen.blit(rendered, (width - 242, height - 100))
            if operator.is_alive():
                timer = loc.get("operator.timers", active=math.ceil(operator.boost_time),
                                cooldown=math.ceil(operator.ability_cooldown))
                timer_surface = font.render(timer, True, (160, 200, 220))
                if timer_surface.get_width() > 184:
                    timer_surface = pygame.transform.smoothscale(
                        timer_surface, (184, timer_surface.get_height()))
                screen.blit(timer_surface, (width - 242, height - 42))
        if controller.operator_mode and operator:
            pygame.draw.rect(screen, (18, 22, 30), (0, height - 130, width, 130))
            text = loc.get("operator.status", name=loc.get(f"operator.{operator.kind}"),
                           hp=int(operator.health), max_hp=operator.max_health,
                           cooldown=math.ceil(operator.ability_cooldown))
            screen.blit(font.render(text, True, (220, 235, 245)), (16, height - 116))
            screen.blit(font.render(loc.get("operator.controls"), True, (220, 235, 245)),
                        (16, height - 88))
            for i, line in enumerate(wrapped_lines(loc.get(f"operator.skill_{operator.kind}"),
                                                   font, width - 285)):
                screen.blit(font.render(line, True, (160, 200, 220)), (16, height - 57 + i * 18))
        rect = self.toggle_rect(width, height)
        pygame.draw.rect(screen, (45, 85, 100), rect, border_radius=4)
        label = loc.get("operator.orbit" if controller.operator_mode else "operator.enter")
        rendered = font.render(label, True, (235, 245, 255))
        screen.blit(rendered, rendered.get_rect(center=rect.center))
        if not menu_open:
            return
        shade = pygame.Surface((width, height), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 205))
        screen.blit(shade, (0, 0))
        wait = max(0, math.ceil(session.operator_respawn_at - session.elapsed_time))
        title = loc.get("operator.choose", cost=200 if session.operator_deployed_once else 0, wait=wait)
        title_surface = font.render(title, True, (235, 245, 255))
        screen.blit(title_surface, title_surface.get_rect(center=(width // 2, height // 2 - 135)))
        for i, (rect, kind) in enumerate(self.choice_rects(width, height)):
            pygame.draw.rect(screen, (22, 29, 40), rect, border_radius=5)
            pygame.draw.rect(screen, (90, 140, 190), rect, 1, border_radius=5)
            texts = [f"{i + 1}. {loc.get(f'operator.{kind}')}",
                     loc.get(f"operator.description_{kind}"), loc.get(f"operator.skill_{kind}")]
            lines = [line for text in texts for line in wrapped_lines(text, font, rect.width - 20)]
            for j, line in enumerate(lines):
                screen.blit(font.render(line, True, (230, 240, 250)),
                            (rect.x + 10, rect.y + 10 + j * (font.get_linesize() + 3)))
        footer = loc.get("operator.unavailable") if error else loc.get("operator.cancel")
        surface = font.render(footer, True, (255, 180, 120))
        screen.blit(surface, surface.get_rect(center=(width // 2, height // 2 + 170)))
