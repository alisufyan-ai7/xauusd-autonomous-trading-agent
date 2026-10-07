from __future__ import annotations

import pytest

from xauusd_agent.core.errors import IntegrityError
from xauusd_agent.core.model import ExecutionCapability, RuntimeMode
from xauusd_agent.storage import integrity
from xauusd_agent.storage.integrity import IntegrityReport, verify_startup
from xauusd_agent.storage.schema import APPLICATION_ID, SCHEMA_VERSION


class _Cursor:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def fetchall(self) -> list[object]:
        return self._rows

    def fetchone(self) -> object | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _Connection:
    def __init__(
        self,
        *,
        quick: list[object] | None = None,
        foreign: object | None = None,
        user_version: int = SCHEMA_VERSION,
        application_id: int = APPLICATION_ID,
        metadata: dict[str, object] | None = None,
        triggers: set[str] | None = None,
    ) -> None:
        self.quick = [("ok",)] if quick is None else quick
        self.foreign = foreign
        self.user_version = user_version
        self.application_id = application_id
        self.metadata = (
            {
                "schema_version": SCHEMA_VERSION,
                "runtime_mode": "EXECUTION_DISABLED",
                "execution_capability": "ABSENT",
            }
            if metadata is None
            else metadata
        )
        self.triggers = set(integrity._REQUIRED_TRIGGERS) if triggers is None else triggers

    def execute(self, sql: str) -> _Cursor:
        normalized = " ".join(sql.casefold().split())
        if normalized == "pragma integrity_check":
            return _Cursor(self.quick)
        if normalized == "pragma foreign_key_check":
            return _Cursor([] if self.foreign is None else [self.foreign])
        if normalized == "pragma user_version":
            return _Cursor([(self.user_version,)])
        if normalized == "pragma application_id":
            return _Cursor([(self.application_id,)])
        if normalized == "select * from storage_metadata where singleton=1":
            return _Cursor([] if self.metadata is None else [self.metadata])
        if normalized == "select name from sqlite_schema where type='trigger'":
            return _Cursor([(name,) for name in sorted(self.triggers)])
        raise AssertionError(f"unexpected SQL: {sql}")


@pytest.fixture(autouse=True)
def _journal_and_outbox_oracles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integrity, "verify_journal", lambda connection: 7)
    monkeypatch.setattr(integrity, "verify_outbox", lambda connection: 9)


def test_valid_startup_report_is_exact() -> None:
    assert verify_startup(_Connection()) == IntegrityReport(
        schema_version=SCHEMA_VERSION,
        journal_entries=7,
        outbox_entries=9,
        runtime_mode=RuntimeMode.EXECUTION_DISABLED,
        execution_capability=ExecutionCapability.ABSENT,
    )


@pytest.mark.parametrize(
    "quick",
    [[], [("bad",)], [("ok",), ("ok",)]],
)
def test_every_integrity_check_shape_fails_closed(quick: list[object]) -> None:
    with pytest.raises(IntegrityError) as exc_info:
        verify_startup(_Connection(quick=quick))
    assert str(exc_info.value) == "SQLite integrity_check failed"


def test_foreign_key_violation_fails_closed() -> None:
    with pytest.raises(IntegrityError) as exc_info:
        verify_startup(_Connection(foreign=("child", 1, "parent", 0)))
    assert str(exc_info.value) == "SQLite foreign key check failed"


@pytest.mark.parametrize(
    ("connection", "message"),
    [
        (_Connection(user_version=SCHEMA_VERSION + 1), "unexpected schema version"),
        (_Connection(application_id=APPLICATION_ID + 1), "unexpected SQLite application id"),
        (
            _Connection(
                metadata={
                    "schema_version": SCHEMA_VERSION + 1,
                    "runtime_mode": "EXECUTION_DISABLED",
                    "execution_capability": "ABSENT",
                }
            ),
            "storage metadata is absent or inconsistent",
        ),
        (
            _Connection(
                metadata={
                    "schema_version": SCHEMA_VERSION,
                    "runtime_mode": "UNKNOWN",
                    "execution_capability": "ABSENT",
                }
            ),
            "storage capability metadata is invalid",
        ),
        (
            _Connection(
                metadata={
                    "schema_version": SCHEMA_VERSION,
                    "runtime_mode": "EXECUTION_DISABLED",
                    "execution_capability": "PRESENT",
                }
            ),
            "storage capability metadata is invalid",
        ),
    ],
)
def test_metadata_and_identity_corruption_fails_closed(
    connection: _Connection, message: str
) -> None:
    with pytest.raises(IntegrityError) as exc_info:
        verify_startup(connection)
    assert str(exc_info.value) == message


def test_absent_metadata_fails_closed() -> None:
    connection = _Connection()
    connection.metadata = None
    with pytest.raises(IntegrityError) as exc_info:
        verify_startup(connection)
    assert str(exc_info.value) == "storage metadata is absent or inconsistent"


@pytest.mark.parametrize(
    "metadata",
    [
        {
            "schema_version": SCHEMA_VERSION,
            "runtime_mode": "UNKNOWN",
            "execution_capability": "ABSENT",
        },
        {
            "schema_version": SCHEMA_VERSION,
            "runtime_mode": "EXECUTION_DISABLED",
            "execution_capability": "PRESENT",
        },
    ],
)
def test_each_execution_disabled_identity_dimension_is_independently_required(
    metadata: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    class _OpenEnum:
        EXECUTION_DISABLED = "EXECUTION_DISABLED"
        ABSENT = "ABSENT"

        def __new__(cls, value: str) -> str:
            return value

    monkeypatch.setattr(integrity, "RuntimeMode", _OpenEnum)
    monkeypatch.setattr(integrity, "ExecutionCapability", _OpenEnum)
    with pytest.raises(IntegrityError) as exc_info:
        verify_startup(_Connection(metadata=metadata))
    assert str(exc_info.value) == "storage is not execution-disabled"


def test_each_required_trigger_is_independently_required() -> None:
    for trigger in sorted(integrity._REQUIRED_TRIGGERS):
        present = set(integrity._REQUIRED_TRIGGERS) - {trigger}
        with pytest.raises(IntegrityError) as exc_info:
            verify_startup(_Connection(triggers=present))
        assert str(exc_info.value) == f"required immutability triggers missing: ['{trigger}']"
