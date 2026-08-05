"""SaveManager: файловые операции со слотами сохранений и быстрым сохранением."""
import json

import pytest

from src.core.game_session import GameSession
from src.save_load.save_manager import QUICKSAVE_SLOT_ID, SaveManager


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game(endless=True)
    return s


@pytest.fixture
def manager(tmp_path):
    return SaveManager(saves_dir=tmp_path)


def test_save_to_new_slot_creates_file_and_returns_slot_id(manager, session, tmp_path):
    slot_id = manager.save_to_new_slot(session)

    assert slot_id is not None
    assert (tmp_path / f"{slot_id}.json").exists()


def test_save_to_new_slot_avoids_name_collisions(manager, session, tmp_path):
    first_id = manager.save_to_new_slot(session)
    second_id = manager.save_to_new_slot(session)

    assert first_id != second_id
    assert (tmp_path / f"{first_id}.json").exists()
    assert (tmp_path / f"{second_id}.json").exists()


def test_save_to_slot_overwrites_existing_slot(manager, session):
    manager.save_to_slot(session, "my_save")
    session.resources.credits = 9999
    manager.save_to_slot(session, "my_save")

    loaded = GameSession()
    assert manager.load_slot(loaded, "my_save") is True
    assert loaded.resources.credits == 9999


def test_quicksave_writes_to_reserved_slot(manager, session, tmp_path):
    ok = manager.quicksave(session)

    assert ok is True
    assert (tmp_path / f"{QUICKSAVE_SLOT_ID}.json").exists()


def test_load_slot_restores_session_state(manager, session):
    session.resources.credits = 555
    manager.save_to_slot(session, "slot_a")

    loaded = GameSession()
    ok = manager.load_slot(loaded, "slot_a")

    assert ok is True
    assert loaded.resources.credits == 555


def test_load_slot_returns_false_for_missing_file(manager):
    loaded = GameSession()

    assert manager.load_slot(loaded, "does_not_exist") is False


def test_load_slot_returns_false_for_corrupt_file(manager, tmp_path):
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    loaded = GameSession()

    assert manager.load_slot(loaded, "broken") is False


def test_list_slots_excludes_quicksave(manager, session):
    manager.save_to_slot(session, "named_a")
    manager.quicksave(session)

    slots = manager.list_slots()

    assert {info["slot_id"] for info in slots} == {"named_a"}


def test_list_slots_sorts_from_newest_to_oldest(manager, session, tmp_path):
    manager.save_to_slot(session, "older")
    manager.save_to_slot(session, "newer")
    _set_saved_at(tmp_path, "older", "2020-01-01T00:00:00")
    _set_saved_at(tmp_path, "newer", "2024-01-01T00:00:00")

    slots = manager.list_slots()

    assert [info["slot_id"] for info in slots] == ["newer", "older"]


def test_quicksave_info_returns_none_when_absent(manager):
    assert manager.quicksave_info() is None


def test_quicksave_info_returns_metadata_when_present(manager, session):
    manager.quicksave(session)

    info = manager.quicksave_info()

    assert info is not None
    assert info["slot_id"] == QUICKSAVE_SLOT_ID


def test_has_any_save_false_when_empty(manager):
    assert manager.has_any_save() is False


def test_has_any_save_true_with_only_quicksave(manager, session):
    manager.quicksave(session)

    assert manager.has_any_save() is True


def test_has_any_save_true_with_only_named_slot(manager, session):
    manager.save_to_slot(session, "named")

    assert manager.has_any_save() is True


def test_most_recent_slot_id_returns_none_when_empty(manager):
    assert manager.most_recent_slot_id() is None


def test_most_recent_slot_id_picks_latest_across_named_and_quicksave(manager, session, tmp_path):
    manager.save_to_slot(session, "named")
    manager.quicksave(session)
    _set_saved_at(tmp_path, "named", "2020-01-01T00:00:00")
    _set_saved_at(tmp_path, QUICKSAVE_SLOT_ID, "2024-01-01T00:00:00")

    assert manager.most_recent_slot_id() == QUICKSAVE_SLOT_ID


def _set_saved_at(saves_dir, slot_id, iso_timestamp):
    """Подменяет поле saved_at в уже записанном файле слота - нужно, чтобы
    детерминированно проверить сортировку по свежести (разрешение реального
    timestamp'а в SaveManager - секунды, тесты выполняются быстрее)."""
    path = saves_dir / f"{slot_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["saved_at"] = iso_timestamp
    path.write_text(json.dumps(data), encoding="utf-8")
