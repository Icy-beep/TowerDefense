"""Loc — единая точка хранения текста интерфейса (data/locale/*.json)."""
import json

from src.localization.loc import Loc, loc


def test_loc_reads_real_ru_strings():
    assert loc.get("menu.start") == "Начать игру"
    assert loc.get("menu.exit") == "Выйти"
    assert loc.get("game_over.victory") == "ПОБЕДА"


def test_loc_substitutes_placeholders():
    text = loc.get("hud.money", credits=250)
    assert "250" in text


def test_loc_supports_format_spec_in_template():
    text = loc.get("hud.survive_remaining", seconds=3.14159)
    assert "3.1 с" in text


def test_loc_returns_bracketed_key_for_unknown_key():
    assert loc.get("does.not.exist") == "[does.not.exist]"


def test_loc_falls_back_to_template_when_placeholder_missing():
    """Не должно падать посреди рендера, если забыли передать аргумент —
    в худшем случае строка останется с {плейсхолдером} как есть."""
    result = Loc().get("hud.money")
    assert "hud.money" not in result


def test_loc_returns_empty_dict_gracefully_when_locale_dir_missing(tmp_path):
    broken_loc = Loc(locale_dir=tmp_path / "does_not_exist")
    assert broken_loc.get("menu.start") == "[menu.start]"


def test_loc_uses_custom_locale_dir(tmp_path):
    (tmp_path / "ru.json").write_text(json.dumps({"menu.start": "ИГРАТЬ"}), encoding="utf-8")
    custom_loc = Loc(locale_dir=tmp_path)

    assert custom_loc.get("menu.start") == "ИГРАТЬ"


def test_en_json_has_exactly_the_same_keys_as_ru_json():
    """Защита от расхождения переводов: у en.json должен быть тот же набор ключей, что у ru.json."""
    from src.localization.loc import DEFAULT_LOCALE_DIR
    with open(DEFAULT_LOCALE_DIR / "ru.json", encoding="utf-8") as f:
        ru_keys = set(json.load(f).keys())
    with open(DEFAULT_LOCALE_DIR / "en.json", encoding="utf-8") as f:
        en_keys = set(json.load(f).keys())

    assert ru_keys == en_keys


def test_available_languages_lists_all_locale_files(tmp_path):
    (tmp_path / "ru.json").write_text("{}", encoding="utf-8")
    (tmp_path / "en.json").write_text("{}", encoding="utf-8")
    custom_loc = Loc(locale_dir=tmp_path)

    assert custom_loc.available_languages() == ["en", "ru"]


def test_available_languages_falls_back_to_current_language_when_dir_missing(tmp_path):
    from src.localization.loc import DEFAULT_LANGUAGE
    broken_loc = Loc(locale_dir=tmp_path / "does_not_exist")
    assert broken_loc.available_languages() == [DEFAULT_LANGUAGE]


def test_set_language_switches_active_strings(tmp_path):
    (tmp_path / "ru.json").write_text(json.dumps({"menu.start": "ИГРАТЬ"}), encoding="utf-8")
    (tmp_path / "en.json").write_text(json.dumps({"menu.start": "PLAY"}), encoding="utf-8")
    multilingual_loc = Loc(locale_dir=tmp_path)

    assert multilingual_loc.get("menu.start") == "ИГРАТЬ"
    multilingual_loc.set_language("en")
    assert multilingual_loc.get("menu.start") == "PLAY"


def test_language_name_returns_friendly_name_for_known_languages():
    assert loc.language_name("ru") == "Русский"
    assert loc.language_name("en") == "English"


def test_language_name_falls_back_to_code_for_unknown_language():
    assert loc.language_name("xx") == "xx"


def test_all_ru_json_keys_used_by_hud_menu_gameover_are_present():
    """Все ключи, которые дергают hud_renderer/menu_screen/game_over_screen, есть в ru.json."""
    from src.localization.loc import DEFAULT_LOCALE_DIR
    with open(DEFAULT_LOCALE_DIR / "ru.json", encoding="utf-8") as f:
        keys = set(json.load(f).keys())

    used_keys = {
        "hud.money", "hud.base_health", "hud.survive_progress", "hud.survive_remaining",
        "hud.camera_info", "hud.controls_move", "hud.controls_drag",
        "hud.controls_build", "hud.controls_select", "hud.controls_misc",
        "hud.build_label", "hud.build_hint", "hud.tower_level",
        "hud.upgrade_cost", "hud.upgrade_yes", "hud.upgrade_no", "hud.max_level",
        "hud.enemy_label", "hud.enemy_hp", "hud.enemy_stats", "hud.enemy_reward",
        "hud.nothing_selected", "enemy.drone_walker", "enemy.giant_roach",
        "enemy.scout_drone", "armor.light", "armor.heavy", "armor.energy_shielded",
        "menu.title", "menu.start", "menu.exit",
        "game_over.defeat", "game_over.victory",
    }
    assert used_keys.issubset(keys)
