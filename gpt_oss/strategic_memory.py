"""Utilities for managing strategic memory and episodic data."""

from __future__ import annotations

import copy
import pickle
import re
import sqlite3
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List


@dataclass
class Episode:
    """Representa una interacción con información contextual."""

    timestamp: datetime
    input: Any
    action: Any
    outcome: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceHypothesis:
    """Patrón inferido desde episodios seguros ya aprendidos."""

    pattern: Dict[str, Any]
    evidence: List[Episode]
    confidence: float
    ethical_constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryConsolidationResult:
    """Resultado auditable de consolidar memoria episódica en hipótesis."""

    episodes_used: int
    hypotheses_created: List[InferenceHypothesis] = field(default_factory=list)
    hypotheses_updated: List[InferenceHypothesis] = field(default_factory=list)
    discarded_signals: List[Dict[str, Any]] = field(default_factory=list)


class SecretRedactor:
    """Redacta secretos antes de almacenar memoria estratégica."""

    REDACTED = "[REDACTED]"
    SECRET_KEYS = re.compile(r"(api[_-]?key|authorization|bearer|credential(?!s)|password|secret|token)", re.IGNORECASE)
    SECRET_PATTERNS = (
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"(?i)(api[_-]?key|token|credential(?!s)|password|secret)\s*[:=]\s*[^\s,;]+"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    )

    @classmethod
    def redact(cls, value: Any) -> Any:
        if isinstance(value, str):
            redacted = value
            for pattern in cls.SECRET_PATTERNS:
                redacted = pattern.sub(lambda match: cls._redact_match(match), redacted)
            return redacted
        if isinstance(value, dict):
            return {
                key: cls.REDACTED if cls.SECRET_KEYS.search(str(key)) else cls.redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls.redact(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls.redact(item) for item in value)
        return value

    @classmethod
    def _redact_match(cls, match: re.Match[str]) -> str:
        text = match.group(0)
        if text.lower().startswith("bearer "):
            return "Bearer " + cls.REDACTED
        if ":" in text:
            return text.split(":", 1)[0] + ": " + cls.REDACTED
        if "=" in text:
            return text.split("=", 1)[0] + "=" + cls.REDACTED
        return cls.REDACTED


class MemoryBackend(ABC):
    """Interfaz de backend para memoria estratégica persistente y transaccional."""

    LEARNING = "learning"
    AUDIT = "audit"
    REJECTED = "rejected"

    @abstractmethod
    def save(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def get(self, key: str, default: Any | None = None) -> Any: ...

    @abstractmethod
    def update(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def append_episode(self, collection: str, episode: Episode) -> None: ...

    @abstractmethod
    def list_episodes(self, collection: str) -> List[Episode]: ...

    @abstractmethod
    def persist(self) -> None: ...

    @abstractmethod
    @contextmanager
    def transaction(self) -> Iterator[None]: ...


class InMemoryMemoryBackend(MemoryBackend):
    """Backend RAM con límites por colección, TTL opcional y rollback transaccional."""

    def __init__(self, max_episodes: int | None = None, collection_limits: Dict[str, int] | None = None, ttl: timedelta | None = None) -> None:
        self._storage: Dict[str, tuple[datetime, Any]] = {}
        self._collections: Dict[str, List[Episode]] = {self.LEARNING: [], self.AUDIT: [], self.REJECTED: []}
        self._max_episodes = max_episodes
        self._collection_limits = collection_limits or {}
        self._ttl = ttl

    def save(self, key: str, value: Any) -> None:
        self._purge_expired()
        if key in self._storage:
            raise ValueError(f"La clave '{key}' ya existe en la memoria.")
        self._storage[key] = (datetime.utcnow(), SecretRedactor.redact(value))

    def get(self, key: str, default: Any | None = None) -> Any:
        self._purge_expired()
        return self._storage.get(key, (None, default))[1]

    def update(self, key: str, value: Any) -> None:
        self._purge_expired()
        if key not in self._storage:
            raise KeyError(f"La clave '{key}' no se encuentra en la memoria.")
        self._storage[key] = (datetime.utcnow(), SecretRedactor.redact(value))

    def append_episode(self, collection: str, episode: Episode) -> None:
        self._purge_expired()
        redacted = self._redact_episode(episode)
        target = self._collections.setdefault(collection, [])
        limit = self._collection_limits.get(collection, self._max_episodes)
        if limit is not None:
            while len(target) >= limit:
                target.pop(0)
        target.append(redacted)

    def list_episodes(self, collection: str) -> List[Episode]:
        self._purge_expired()
        return list(self._collections.setdefault(collection, []))

    def persist(self) -> None:
        return None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        snapshot = (copy.deepcopy(self._storage), copy.deepcopy(self._collections))
        try:
            yield
        except Exception:
            self._storage, self._collections = snapshot
            raise

    def _purge_expired(self) -> None:
        if self._ttl is None:
            return
        cutoff = datetime.utcnow() - self._ttl
        self._storage = {key: item for key, item in self._storage.items() if item[0] >= cutoff}
        for name, episodes in self._collections.items():
            self._collections[name] = [episode for episode in episodes if episode.timestamp >= cutoff]

    @staticmethod
    def _redact_episode(episode: Episode) -> Episode:
        clone = copy.deepcopy(episode)
        clone.input = SecretRedactor.redact(clone.input)
        clone.action = SecretRedactor.redact(clone.action)
        clone.outcome = SecretRedactor.redact(clone.outcome)
        clone.metadata = SecretRedactor.redact(clone.metadata)
        return clone


class SQLiteMemoryBackend(InMemoryMemoryBackend):
    """Backend SQLite persistente compatible con la interfaz de memoria."""

    def __init__(self, path: str | Path, max_episodes: int | None = None, collection_limits: Dict[str, int] | None = None, ttl: timedelta | None = None) -> None:
        self.path = Path(path)
        self._conn = sqlite3.connect(self.path)
        self._transaction_depth = 0
        self._conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, created_at TEXT NOT NULL, value BLOB NOT NULL)")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, collection TEXT NOT NULL, timestamp TEXT NOT NULL, episode BLOB NOT NULL)"
        )
        self._conn.commit()
        self._max_episodes = max_episodes
        self._collection_limits = collection_limits or {}
        self._ttl = ttl

    def save(self, key: str, value: Any) -> None:
        self._purge_expired()
        try:
            self._conn.execute(
                "INSERT INTO kv(key, created_at, value) VALUES (?, ?, ?)",
                (key, datetime.utcnow().isoformat(), sqlite3.Binary(pickle.dumps(SecretRedactor.redact(value)))),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"La clave '{key}' ya existe en la memoria.") from exc
        self.persist()

    def get(self, key: str, default: Any | None = None) -> Any:
        self._purge_expired()
        row = self._conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return default if row is None else pickle.loads(row[0])

    def update(self, key: str, value: Any) -> None:
        self._purge_expired()
        cur = self._conn.execute(
            "UPDATE kv SET created_at = ?, value = ? WHERE key = ?",
            (datetime.utcnow().isoformat(), sqlite3.Binary(pickle.dumps(SecretRedactor.redact(value))), key),
        )
        if cur.rowcount == 0:
            raise KeyError(f"La clave '{key}' no se encuentra en la memoria.")
        self.persist()

    def append_episode(self, collection: str, episode: Episode) -> None:
        self._purge_expired()
        redacted = self._redact_episode(episode)
        self._conn.execute(
            "INSERT INTO episodes(collection, timestamp, episode) VALUES (?, ?, ?)",
            (collection, redacted.timestamp.isoformat(), sqlite3.Binary(pickle.dumps(redacted))),
        )
        limit = self._collection_limits.get(collection, self._max_episodes)
        if limit is not None:
            self._conn.execute(
                "DELETE FROM episodes WHERE id IN (SELECT id FROM episodes WHERE collection = ? ORDER BY id ASC LIMIT max((SELECT COUNT(*) FROM episodes WHERE collection = ?) - ?, 0))",
                (collection, collection, limit),
            )
        self.persist()

    def list_episodes(self, collection: str) -> List[Episode]:
        self._purge_expired()
        rows = self._conn.execute("SELECT episode FROM episodes WHERE collection = ? ORDER BY id ASC", (collection,)).fetchall()
        return [pickle.loads(row[0]) for row in rows]

    def persist(self) -> None:
        if self._transaction_depth == 0:
            self._conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self._transaction_depth += 1
        if self._transaction_depth == 1:
            self._conn.execute("BEGIN")
        try:
            yield
        except Exception:
            self._transaction_depth -= 1
            if self._transaction_depth == 0:
                self._conn.rollback()
            raise
        else:
            self._transaction_depth -= 1
            if self._transaction_depth == 0:
                self._conn.commit()

    def _purge_expired(self) -> None:
        if self._ttl is None:
            return
        cutoff = (datetime.utcnow() - self._ttl).isoformat()
        self._conn.execute("DELETE FROM kv WHERE created_at < ?", (cutoff,))
        self._conn.execute("DELETE FROM episodes WHERE timestamp < ?", (cutoff,))
        self.persist()

    def close(self) -> None:
        self._conn.close()


class StrategicMemory:
    """Almacena memoria estratégica, auditoría y aprendizaje inferencial seguro."""

    def __init__(self, max_episodes: int | None = None, backend: MemoryBackend | None = None, ttl: timedelta | None = None) -> None:
        self._backend = backend or InMemoryMemoryBackend(max_episodes=max_episodes, ttl=ttl)
        self._hypotheses: List[InferenceHypothesis] = []

    def save(self, key: str, value: Any) -> None:
        self._backend.save(key, value)

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._backend.get(key, default)

    def update(self, key: str, value: Any) -> None:
        self._backend.update(key, value)

    def persist(self) -> None:
        self._backend.persist()

    def transaction(self) -> Iterator[None]:
        return self._backend.transaction()

    def add_episode(self, data: Episode) -> None:
        """Añade un episodio utilizable solo si no fue bloqueado por Qualia."""

        if self._is_blocked_or_rejected(data):
            self.add_rejected_learning(data, reason="blocked_or_rejected_by_qualia")
            return
        self._backend.append_episode(MemoryBackend.LEARNING, data)

    def add_audit_episode(self, data: Episode) -> None:
        """Registra trazabilidad sin alimentar aprendizaje inferencial."""

        self._backend.append_episode(MemoryBackend.AUDIT, data)

    def add_rejected_learning(self, data: Episode, reason: str) -> None:
        """Registra una señal que no debe consolidarse como conocimiento."""

        data.metadata = {**data.metadata, "rejection_reason": reason, "status": data.metadata.get("status", "rejected_learning")}
        self._backend.append_episode(MemoryBackend.REJECTED, data)
        self._backend.append_episode(MemoryBackend.AUDIT, data)

    def query(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._backend.list_episodes(MemoryBackend.LEARNING), pattern)

    def query_audit(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._backend.list_episodes(MemoryBackend.AUDIT), pattern)

    def query_rejected(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._backend.list_episodes(MemoryBackend.REJECTED), pattern)

    def infer_patterns(self, criteria: Dict[str, Any] | None = None) -> List[InferenceHypothesis]:
        if criteria:
            return self.query_inferred(criteria)
        if not self._hypotheses:
            self.consolidate_from_episodes()
        return list(self._hypotheses)

    def consolidate_from_episodes(self, min_support: int = 2, max_hypotheses: int = 20) -> MemoryConsolidationResult:
        groups: dict[tuple[Any, Any, Any], list[Episode]] = defaultdict(list)
        discarded: list[dict[str, Any]] = []
        for episode in self._backend.list_episodes(MemoryBackend.LEARNING):
            if self._is_blocked_or_rejected(episode):
                discarded.append({"reason": "blocked_or_rejected", "episode": episode})
                continue
            key = (
                episode.metadata.get("task", episode.action),
                episode.metadata.get("context"),
                self._hashable(episode.metadata.get("goals")),
            )
            groups[key].append(episode)

        created: list[InferenceHypothesis] = []
        updated: list[InferenceHypothesis] = []
        for (task, context, goals), evidence in groups.items():
            if len(evidence) < min_support:
                continue
            successes = sum(1 for ep in evidence if ep.metadata.get("status") in {"success", "accepted", None})
            confidence = round(min(1.0, successes / len(evidence)), 3)
            constraints = sorted({str(item) for ep in evidence for item in ep.metadata.get("violated_constraints", [])})
            hypothesis = InferenceHypothesis(
                pattern={"task": task, "context": context, "goals": goals, "recommended_action": evidence[-1].action},
                evidence=list(evidence),
                confidence=confidence,
                ethical_constraints=constraints,
            )
            previous = self._find_hypothesis(hypothesis.pattern)
            if previous is None:
                created.append(hypothesis)
                self._hypotheses.append(hypothesis)
            else:
                previous.evidence = hypothesis.evidence
                previous.confidence = hypothesis.confidence
                previous.ethical_constraints = hypothesis.ethical_constraints
                updated.append(previous)
            if len(created) + len(updated) >= max_hypotheses:
                break
        return MemoryConsolidationResult(
            episodes_used=sum(len(eps) for eps in groups.values()),
            hypotheses_created=created,
            hypotheses_updated=updated,
            discarded_signals=discarded,
        )

    def query_inferred(self, pattern: Dict[str, Any]) -> List[InferenceHypothesis]:
        return [hypothesis for hypothesis in self._hypotheses if all(hypothesis.pattern.get(key) == value for key, value in pattern.items())]

    def summarize(self) -> Dict[str, Any]:
        episodes = self._backend.list_episodes(MemoryBackend.LEARNING)
        acciones = Counter(ep.action for ep in episodes)
        resultados = Counter(ep.outcome for ep in episodes)
        return {
            "total": len(episodes),
            "audit_total": len(self._backend.list_episodes(MemoryBackend.AUDIT)),
            "rejected_total": len(self._backend.list_episodes(MemoryBackend.REJECTED)),
            "hypotheses_total": len(self._hypotheses),
            "actions": acciones.most_common(),
            "outcomes": resultados.most_common(),
        }

    @staticmethod
    def _query_collection(collection: List[Episode], pattern: Dict[str, Any]) -> List[Episode]:
        resultados: List[Episode] = []
        for episodio in collection:
            coincide = True
            for clave, valor in pattern.items():
                attr = getattr(episodio, clave, episodio.metadata.get(clave))
                if attr != valor:
                    coincide = False
                    break
            if coincide:
                resultados.append(episodio)
        return resultados

    @staticmethod
    def _is_blocked_or_rejected(episode: Episode) -> bool:
        status = episode.metadata.get("status")
        if status in {"blocked_by_qualia", "rejected_learning"}:
            return True
        if episode.metadata.get("qualia_policy_action") == "blocked_by_ontoethical_policy":
            return True
        if episode.metadata.get("qualia_legal_policy_action") == "blocked_illegal_or_unsafe_decision":
            return True
        if isinstance(episode.outcome, dict) and episode.outcome.get("blocked"):
            return True
        return False

    @staticmethod
    def _hashable(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, dict):
            return tuple(sorted(value.items()))
        return value

    def _find_hypothesis(self, pattern: Dict[str, Any]) -> InferenceHypothesis | None:
        for hypothesis in self._hypotheses:
            if hypothesis.pattern == pattern:
                return hypothesis
        return None
