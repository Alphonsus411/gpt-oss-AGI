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


def test_add_episode_query_and_summarize_multiple():
    memoria = StrategicMemory()
    ep1 = Episode(
        timestamp=datetime.utcnow(),
        input="i1",
        action="alpha",
        outcome="ok",
        metadata={"tag": 1},
    )
    ep2 = Episode(
        timestamp=datetime.utcnow(),
        input="i2",
        action="beta",
        outcome="fail",
        metadata={"tag": 2},
    )
    memoria.add_episode(ep1)
    memoria.add_episode(ep2)

    assert memoria.query({"tag": 1}) == [ep1]
    assert memoria.query({"action": "beta"}) == [ep2]

    resumen = memoria.summarize()
    assert resumen["total"] == 2
    assert ("alpha", 1) in resumen["actions"]
    assert ("fail", 1) in resumen["outcomes"]


def test_max_episodes_fifo():
    memoria = StrategicMemory(max_episodes=2)
    ep1 = Episode(
        timestamp=datetime.utcnow(),
        input="i1",
        action="a1",
        outcome="o1",
    )
    ep2 = Episode(
        timestamp=datetime.utcnow(),
        input="i2",
        action="a2",
        outcome="o2",
    )
    ep3 = Episode(
        timestamp=datetime.utcnow(),
        input="i3",
        action="a3",
        outcome="o3",
    )
    memoria.add_episode(ep1)
    memoria.add_episode(ep2)
    memoria.add_episode(ep3)

    assert memoria.query({"action": "a1"}) == []
    assert memoria.query({"action": "a2"}) == [ep2]
    assert memoria.query({"action": "a3"}) == [ep3]
    assert memoria.summarize()["total"] == 2


def test_blocked_episode_goes_to_audit_and_rejected_memory():
    memoria = StrategicMemory()
    ep = Episode(
        timestamp=datetime.utcnow(),
        input="bad",
        action="blocked_by_qualia",
        outcome={"blocked": True},
        metadata={"status": "blocked_by_qualia", "task": "t"},
    )

    memoria.add_episode(ep)

    assert memoria.query({"task": "t"}) == []
    assert memoria.query_audit({"task": "t"}) == [ep]
    assert memoria.query_rejected({"task": "t"}) == [ep]


def test_consolidate_from_safe_episodes_creates_inferred_hypothesis():
    memoria = StrategicMemory()
    for idx in range(2):
        memoria.add_episode(
            Episode(
                timestamp=datetime.utcnow(),
                input=f"i{idx}",
                action="expert_a",
                outcome="ok",
                metadata={
                    "task": "analizar",
                    "context": "ctx",
                    "goals": ["done"],
                    "status": "success",
                },
            )
        )

    result = memoria.consolidate_from_episodes(min_support=2)
    inferred = memoria.query_inferred({"task": "analizar"})

    assert result.episodes_used == 2
    assert inferred
    assert inferred[0].confidence == 1.0
    assert inferred[0].pattern["recommended_action"] == "expert_a"
