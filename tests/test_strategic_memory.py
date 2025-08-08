import pytest

from datetime import datetime

from gpt_oss.strategic_memory import Episode, StrategicMemory


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


def test_add_and_query_episode():
    memoria = StrategicMemory()
    ep = Episode(
        timestamp=datetime.utcnow(),
        input="hola",
        action="saludo",
        outcome="ok",
        metadata={"tema": "prueba"},
    )
    memoria.add_episode(ep)
    assert memoria.query({"action": "saludo"}) == [ep]
    assert memoria.query({"tema": "prueba"}) == [ep]


def test_summarize_episodes():
    memoria = StrategicMemory()
    memoria.add_episode(
        Episode(
            timestamp=datetime.utcnow(),
            input="uno",
            action="a",
            outcome="exito",
        )
    )
    memoria.add_episode(
        Episode(
            timestamp=datetime.utcnow(),
            input="dos",
            action="a",
            outcome="fracaso",
        )
    )
    resumen = memoria.summarize()
    assert resumen["total"] == 2
    assert resumen["actions"][0][0] == "a"
