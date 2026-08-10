"""Дерево технологий башен (см. src/ui/tech_tree_screen.py, GameSession.tech_tree).

Апгрейд ветки покупается один раз для ЦЕЛОГО ТИПА башни (не для конкретной
поставленной башни, как раньше устроена была прокачка по 'U') и сразу действует
на все уже стоящие и все будущие башни этого типа - см. GameSession.upgrade_tech_branch
и GameSession.place_turret."""

BRANCHES = ("radius", "damage", "attack_speed")
MULTIPLIER_PER_LEVEL = {"radius": 0.2, "damage": 0.4, "attack_speed": 0.25}


class TechTree:
    """Хранит уровень каждой ветки для каждого типа боевой башни за сессию."""

    def __init__(self):
        """Создаёт пустое дерево - все ветки всех типов на уровне 0."""
        self.levels: dict[str, dict[str, int]] = {}

    def level_for(self, tower_type: str, branch: str) -> int:
        """Текущий уровень ветки branch у типа tower_type (0, если ещё не куплена)."""
        return self.levels.get(tower_type, {}).get(branch, 0)

    def multiplier_for(self, tower_type: str, branch: str) -> float:
        """Множитель характеристики ветки branch с учётом текущего уровня."""
        return 1.0 + self.level_for(tower_type, branch) * MULTIPLIER_PER_LEVEL[branch]

    def upgrade_cost(self, tower_type: str, branch: str, upgrade_costs: list[int]) -> int | None:
        """Стоимость следующего уровня ветки, или None, если она уже максимальна.
        upgrade_costs - прогрессия цен типа tower_type (см. TowerFactory.get_upgrade_costs) -
        та же самая, что раньше использовалась для единой линейной прокачки по 'U'."""
        level = self.level_for(tower_type, branch)
        if level >= len(upgrade_costs):
            return None
        return upgrade_costs[level]

    def upgrade(self, tower_type: str, branch: str) -> None:
        """Повышает уровень ветки branch у типа tower_type на 1."""
        per_type = self.levels.setdefault(tower_type, {})
        per_type[branch] = per_type.get(branch, 0) + 1

    def apply_to(self, module) -> None:
        """Пересчитывает range_radius/damage/attack_speed башни module из её
        base_range/base_damage/base_attack_speed и текущих уровней дерева для её типа -
        вызывается и при постройке новой башни (см. GameSession.place_turret), и
        сразу после покупки апгрейда для всех уже стоящих башен этого типа (см.
        GameSession.upgrade_tech_branch)."""
        module.range_radius = module.base_range * self.multiplier_for(module.type_name, "radius")
        module.damage = module.base_damage * self.multiplier_for(module.type_name, "damage")
        module.attack_speed = module.base_attack_speed * self.multiplier_for(module.type_name, "attack_speed")
