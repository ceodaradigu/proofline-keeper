from dataclasses import replace
from datetime import datetime, timedelta, timezone

from proofline_keeper import (
    SimulationReceipt,
    TransactionIntent,
    authorize,
    evaluate_execution,
    fingerprint_intent,
)


NOW = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
TO = "0x1111111111111111111111111111111111111111"


def intent(amount: str = "0.01") -> TransactionIntent:
    return TransactionIntent(84532, TO, amount, purpose="Record verified completion proof")


def simulation(tx: TransactionIntent, **changes: object) -> SimulationReceipt:
    base = SimulationReceipt(fingerprint_intent(tx), True, False, NOW, "42000")
    return replace(base, **changes)


def approval(tx: TransactionIntent, sim: SimulationReceipt, cap: str = "0.01"):
    return authorize(
        tx,
        sim,
        maximum_amount=cap,
        approved_at=NOW,
        ttl_minutes=15,
        approval_id="demo-approval-001",
    )


def test_requires_simulation_before_approval():
    result = evaluate_execution(intent(), None, None, now=NOW)
    assert result.code == "SIMULATION_REQUIRED"


def test_reverting_simulation_is_blocked():
    tx = intent()
    result = evaluate_execution(tx, simulation(tx, would_revert=True), None, now=NOW)
    assert result.code == "SIMULATION_FAILED"


def test_stale_simulation_is_blocked():
    tx = intent()
    sim = simulation(tx, observed_at=NOW - timedelta(minutes=11))
    result = evaluate_execution(tx, sim, None, now=NOW)
    assert result.code == "SIMULATION_STALE"


def test_exact_simulation_requires_approval():
    tx = intent()
    sim = simulation(tx)
    result = evaluate_execution(tx, sim, None, now=NOW)
    assert result.code == "APPROVAL_REQUIRED"


def test_amount_cap_is_enforced():
    tx = intent("0.02")
    sim = simulation(tx)
    result = evaluate_execution(tx, sim, approval(tx, sim, cap="0.01"), now=NOW)
    assert result.code == "LIMIT_EXCEEDED"


def test_change_after_approval_is_blocked():
    original = intent()
    sim = simulation(original)
    ticket = approval(original, sim)
    changed = replace(original, to_address="0x2222222222222222222222222222222222222222")
    result = evaluate_execution(changed, sim, ticket, now=NOW)
    assert result.code in {"SIMULATION_FAILED", "APPROVAL_MISMATCH"}


def test_expired_approval_is_blocked():
    tx = intent()
    sim = simulation(tx)
    result = evaluate_execution(tx, sim, approval(tx, sim), now=NOW + timedelta(minutes=16))
    assert result.code in {"SIMULATION_STALE", "APPROVAL_EXPIRED"}


def test_exact_approved_intent_is_ready_and_idempotent():
    tx = intent()
    sim = simulation(tx)
    ticket = approval(tx, sim)
    first = evaluate_execution(tx, sim, ticket, now=NOW)
    second = evaluate_execution(tx, sim, ticket, now=NOW)
    assert first.code == "READY"
    assert first.ready is True
    assert first.idempotency_key == second.idempotency_key

