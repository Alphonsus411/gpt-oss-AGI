import pytest

from datetime import datetime, timezone

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
        timestamp=datetime.now(timezone.utc),
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
            timestamp=datetime.now(timezone.utc),
            input="uno",
            action="a",
            outcome="exito",
        )
    )
    memoria.add_episode(
        Episode(
            timestamp=datetime.now(timezone.utc),
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
        timestamp=datetime.now(timezone.utc),
        input="i1",
        action="alpha",
        outcome="ok",
        metadata={"tag": 1},
    )
    ep2 = Episode(
        timestamp=datetime.now(timezone.utc),
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
        timestamp=datetime.now(timezone.utc),
        input="i1",
        action="a1",
        outcome="o1",
    )
    ep2 = Episode(
        timestamp=datetime.now(timezone.utc),
        input="i2",
        action="a2",
        outcome="o2",
    )
    ep3 = Episode(
        timestamp=datetime.now(timezone.utc),
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
        timestamp=datetime.now(timezone.utc),
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
                timestamp=datetime.now(timezone.utc),
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

from datetime import timedelta

from gpt_oss.strategic_memory import InMemoryMemoryBackend, MemoryBackend, SQLiteMemoryBackend


def test_ram_backend_with_collection_limits():
    backend = InMemoryMemoryBackend(collection_limits={MemoryBackend.LEARNING: 1, MemoryBackend.AUDIT: 2})
    memoria = StrategicMemory(backend=backend)
    ep1 = Episode(datetime.now(timezone.utc), "i1", "a1", "o1")
    ep2 = Episode(datetime.now(timezone.utc), "i2", "a2", "o2")

    memoria.add_episode(ep1)
    memoria.add_episode(ep2)
    memoria.add_audit_episode(ep1)
    memoria.add_audit_episode(ep2)

    assert memoria.query({}) == [ep2]
    assert memoria.query_audit({}) == [ep1, ep2]


def test_sqlite_backend_persists_with_temp_file(tmp_path):
    db_path = tmp_path / "memory.sqlite"
    memoria = StrategicMemory(backend=SQLiteMemoryBackend(db_path))
    ep = Episode(datetime.now(timezone.utc), "hola", "saludo", "ok", {"tema": "sqlite"})

    memoria.save("plan", {"step": 1})
    memoria.add_episode(ep)
    memoria.persist()

    reloaded = StrategicMemory(backend=SQLiteMemoryBackend(db_path))
    assert reloaded.get("plan") == {"step": 1}
    assert reloaded.query({"tema": "sqlite"})[0].action == "saludo"


def test_ttl_expiration_removes_old_episodes_and_keys():
    old = datetime.now(timezone.utc) - timedelta(seconds=60)
    memoria = StrategicMemory(backend=InMemoryMemoryBackend(ttl=timedelta(seconds=1)))
    memoria.save("token_info", "visible")
    memoria.add_episode(Episode(old, "old", "expired", "no"))

    assert memoria.query({"action": "expired"}) == []


def test_ttl_accepts_legacy_naive_episode_timestamps():
    now = datetime.now(timezone.utc)
    memoria = StrategicMemory(backend=InMemoryMemoryBackend(ttl=timedelta(seconds=30)))
    memoria.add_episode(Episode((now - timedelta(seconds=60)).replace(tzinfo=None), "old", "expired", "no"))
    memoria.add_episode(Episode(now.replace(tzinfo=None), "new", "retained", "yes"))

    episodes = memoria.query({})

    assert [episode.action for episode in episodes] == ["retained"]
    assert episodes[0].timestamp.tzinfo is timezone.utc


def test_transaction_rollback_discards_changes():
    memoria = StrategicMemory(backend=InMemoryMemoryBackend())

    with pytest.raises(RuntimeError):
        with memoria.transaction():
            memoria.save("plan", "temporal")
            memoria.add_episode(Episode(datetime.now(timezone.utc), "i", "a", "o"))
            raise RuntimeError("rollback")

    assert memoria.get("plan") is None
    assert memoria.query({}) == []


def test_sqlite_transaction_rollback_discards_changes(tmp_path):
    memoria = StrategicMemory(backend=SQLiteMemoryBackend(tmp_path / "tx.sqlite"))

    with pytest.raises(RuntimeError):
        with memoria.transaction():
            memoria.save("plan", "temporal")
            memoria.add_episode(Episode(datetime.now(timezone.utc), "i", "a", "o"))
            raise RuntimeError("rollback")

    assert memoria.get("plan") is None
    assert memoria.query({}) == []


def test_secret_redaction_in_prompts_tokens_credentials_and_api_keys():
    memoria = StrategicMemory()
    memoria.save(
        "secrets",
        {
            "prompt": "usa token=tok_123456789012345 y api_key: abcdefghijklmnop",
            "credentials": {"password": "super-secret", "nested": "Bearer abcdefghijklmnop"},
            "openai_api_key": "sk-abcdefghijklmnop123456",
        },
    )
    memoria.add_episode(
        Episode(
            datetime.now(timezone.utc),
            "prompt con sk-abcdefghijklmnop123456",
            "call",
            {"credential": "abcdef"},
            {"api_key": "secret", "token_hint": "Bearer abcdefghijklmnop"},
        )
    )

    stored = memoria.get("secrets")
    episode = memoria.query({"action": "call"})[0]

    assert "tok_123456789012345" not in str(stored)
    assert "abcdefghijklmnop" not in str(stored)
    assert stored["credentials"]["password"] == "[REDACTED]"
    assert stored["openai_api_key"] == "[REDACTED]"
    assert "sk-abcdefghijklmnop123456" not in episode.input
    assert episode.outcome["credential"] == "[REDACTED]"
    assert episode.metadata["api_key"] == "[REDACTED]"


def test_learning_audit_and_rejected_collections_remain_separated():
    memoria = StrategicMemory()
    learned = Episode(datetime.now(timezone.utc), "learn", "learn_action", "ok", {"kind": "learned"})
    audit = Episode(datetime.now(timezone.utc), "audit", "audit_action", "ok", {"kind": "audit"})
    rejected = Episode(datetime.now(timezone.utc), "reject", "reject_action", {"blocked": True}, {"kind": "rejected"})

    memoria.add_episode(learned)
    memoria.add_audit_episode(audit)
    memoria.add_episode(rejected)

    assert memoria.query({"kind": "learned"}) == [learned]
    assert memoria.query({"kind": "audit"}) == []
    assert memoria.query({"kind": "rejected"}) == []
    assert [ep.metadata["kind"] for ep in memoria.query_audit({})] == ["audit", "rejected"]
    assert memoria.query_rejected({})[0].metadata["kind"] == "rejected"
