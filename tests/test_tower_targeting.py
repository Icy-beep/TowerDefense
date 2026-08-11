from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker
from src.entities.turrets import BulletTurret, LaserTurret
from src.enums import ArmorType


class TestTowerTargeting:
    """Тесты наведения башен на цели"""

    def test_find_target_in_range(self):
        """Тест 4: Корректность определения противников в зоне действия башни"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_in_range = DroneWalker(Coordinate(150, 100))
        enemy_out_of_range = DroneWalker(Coordinate(300, 100))

        enemies = [enemy_out_of_range, enemy_in_range]
        target = tower.find_target(enemies)

        assert target == enemy_in_range
        assert target is not None

    def test_no_target_in_range(self):
        """Проверка, когда врагов в радиусе нет"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_far = DroneWalker(Coordinate(500, 500))

        target = tower.find_target([enemy_far])

        assert target is None

    def test_find_nearest_target(self):
        """Проверка выбора ближайшей цели"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_near = DroneWalker(Coordinate(120, 100))
        enemy_far = DroneWalker(Coordinate(180, 100))

        target = tower.find_target([enemy_far, enemy_near])

        assert target == enemy_near


class TestAiModuleTargeting:
    """ИИ-модули (см. DefenseModule.AI_MODULE_KEYS) меняют логику find_target -
    без установленного модуля поведение остаётся прежним."""

    def test_finish_wounded_prefers_lowest_health_over_nearest(self):
        tower = LaserTurret(Coordinate(100, 100))
        tower.ai_module = "finish_wounded"
        near_full_health = DroneWalker(Coordinate(120, 100))
        far_wounded = DroneWalker(Coordinate(180, 100))
        far_wounded.health = 1

        target = tower.find_target([near_full_health, far_wounded])

        assert target is far_wounded

    def test_ignore_resistant_skips_target_that_resists_own_damage_type(self):
        """BulletTurret бьёт KINETIC, HEAVY броня режет его на 50% - модуль должен
        предпочесть небронированную цель, даже если она дальше."""
        tower = BulletTurret(Coordinate(100, 100))
        tower.ai_module = "ignore_resistant"
        near_resistant = DroneWalker(Coordinate(120, 100), armor=ArmorType.HEAVY)
        far_vulnerable = DroneWalker(Coordinate(180, 100), armor=ArmorType.LIGHT)

        target = tower.find_target([near_resistant, far_vulnerable])

        assert target is far_vulnerable

    def test_ignore_resistant_falls_back_to_resistant_target_if_no_alternative(self):
        tower = BulletTurret(Coordinate(100, 100))
        tower.ai_module = "ignore_resistant"
        only_resistant = DroneWalker(Coordinate(120, 100), armor=ArmorType.HEAVY)

        target = tower.find_target([only_resistant])

        assert target is only_resistant

    def test_hunt_leaders_prefers_group_leader_over_nearest(self):
        tower = LaserTurret(Coordinate(100, 100))
        tower.ai_module = "hunt_leaders"
        near_regular = DroneWalker(Coordinate(120, 100))
        far_leader = DroneWalker(Coordinate(180, 100))
        far_leader.is_group_leader = True

        target = tower.find_target([near_regular, far_leader])

        assert target is far_leader

    def test_hunt_leaders_falls_back_to_nearest_without_a_leader_in_range(self):
        tower = LaserTurret(Coordinate(100, 100))
        tower.ai_module = "hunt_leaders"
        near_regular = DroneWalker(Coordinate(120, 100))
        far_regular = DroneWalker(Coordinate(180, 100))

        target = tower.find_target([far_regular, near_regular])

        assert target is near_regular

    def test_without_ai_module_behavior_is_unchanged(self):
        tower = LaserTurret(Coordinate(100, 100))
        assert tower.ai_module is None
        near = DroneWalker(Coordinate(120, 100))
        far_wounded_leader = DroneWalker(Coordinate(180, 100))
        far_wounded_leader.health = 1
        far_wounded_leader.is_group_leader = True

        target = tower.find_target([far_wounded_leader, near])

        assert target is near