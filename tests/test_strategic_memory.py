import pytest

from gpt_oss.strategic_memory import StrategicMemory


def test_save_and_get():
    memoria = StrategicMemory()
    memoria.save("plan", "inicial")
    assert memoria.get("plan") == "inicial"


def test_save_existing_key_raises():
    memoria = StrategicMemory()
    memoria.save("plan", "inicial")
    with pytest.raises(ValueError):
        memoria.save("plan", "nuevo")


def test_update():
    memoria = StrategicMemory()
    memoria.save("plan", "inicial")
    memoria.update("plan", "actualizado")
    assert memoria.get("plan") == "actualizado"


def test_update_missing_key_raises():
    memoria = StrategicMemory()
    with pytest.raises(KeyError):
        memoria.update("plan", "valor")
