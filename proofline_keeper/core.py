"""Deterministic safety boundary for KeeperHub on-chain execution.

The model or agent may propose an intent, but this module alone decides whether
the exact simulated transaction is eligible for broadcast. It performs no
network calls and holds no wallet secrets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Literal


DecisionCode = Literal[
    "READY",
    "INVALID_INTENT",
    "LIMIT_EXCEEDED",
    "SIMULATION_REQUIRED",
    "SIMULATION_FAILED",
    "SIMULATION_STALE",
    "APPROVAL_REQUIRED",
    "APPROVAL_EXPIRED",
    "APPROVAL_MISMATCH",
]

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class TransactionIntent:
    chain_id: int
    to_address: str
    amount: str
    token_address: str | None = None
    purpose: str = ""


@dataclass(frozen=True)
class SimulationReceipt:
    intent_hash: str
    success: bool
    would_revert: bool
    observed_at: datetime
    gas_estimate: str
    provider: str = "keeperhub"


@dataclass(frozen=True)
class ApprovalTicket:
    intent_hash: str
    simulation_hash: str
    maximum_amount: str
    approved_at: datetime
    expires_at: datetime
    approval_id: str


@dataclass(frozen=True)
class ExecutionDecision:
    code: DecisionCode
    ready: bool
    reason: str
    intent_hash: str
    simulation_hash: str | None = None
    idempotency_key: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=lambda item: _utc(item).isoformat() if isinstance(item, datetime) else str(item),
    ).encode("utf-8")


def fingerprint_intent(intent: TransactionIntent) -> str:
    return sha256(_canonical(asdict(intent))).hexdigest()


def fingerprint_simulation(simulation: SimulationReceipt) -> str:
    return sha256(_canonical(asdict(simulation))).hexdigest()


def _amount(value: str) -> Decimal | None:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount <= 0:
        return None
    return amount


def authorize(
    intent: TransactionIntent,
    simulation: SimulationReceipt,
    *,
    maximum_amount: str,
    approved_at: datetime,
    ttl_minutes: int,
    approval_id: str,
) -> ApprovalTicket:
    """Bind approval to the exact intent and simulation evidence."""

    if ttl_minutes <= 0:
        raise ValueError("ttl_minutes must be positive")
    if not approval_id.strip():
        raise ValueError("approval_id is required")
    approved = _utc(approved_at)
    return ApprovalTicket(
        intent_hash=fingerprint_intent(intent),
        simulation_hash=fingerprint_simulation(simulation),
        maximum_amount=maximum_amount,
        approved_at=approved,
        expires_at=approved + timedelta(minutes=ttl_minutes),
        approval_id=approval_id,
    )


def evaluate_execution(
    intent: TransactionIntent,
    simulation: SimulationReceipt | None,
    approval: ApprovalTicket | None,
    *,
    now: datetime,
    simulation_max_age_minutes: int = 10,
) -> ExecutionDecision:
    """Return READY only for an unchanged, simulated and approved intent."""

    checked_at = _utc(now)
    intent_hash = fingerprint_intent(intent)
    amount = _amount(intent.amount)
    token_valid = intent.token_address is None or bool(_EVM_ADDRESS.fullmatch(intent.token_address))
    if (
        intent.chain_id <= 0
        or not _EVM_ADDRESS.fullmatch(intent.to_address)
        or amount is None
        or not token_valid
        or not intent.purpose.strip()
    ):
        return ExecutionDecision("INVALID_INTENT", False, "Intent fields are invalid.", intent_hash)

    if simulation is None:
        return ExecutionDecision("SIMULATION_REQUIRED", False, "KeeperHub simulation is missing.", intent_hash)

    simulation_hash = fingerprint_simulation(simulation)
    if simulation.intent_hash != intent_hash:
        return ExecutionDecision(
            "SIMULATION_FAILED", False, "Simulation does not match the current intent.", intent_hash, simulation_hash
        )
    if not simulation.success or simulation.would_revert:
        return ExecutionDecision(
            "SIMULATION_FAILED", False, "KeeperHub preflight did not pass.", intent_hash, simulation_hash
        )
    observed_at = _utc(simulation.observed_at)
    age = checked_at - observed_at
    if age.total_seconds() < 0 or age > timedelta(minutes=simulation_max_age_minutes):
        return ExecutionDecision(
            "SIMULATION_STALE", False, "Simulation evidence is stale.", intent_hash, simulation_hash
        )

    if approval is None:
        return ExecutionDecision(
            "APPROVAL_REQUIRED", False, "Exact simulated intent needs approval.", intent_hash, simulation_hash
        )
    if checked_at > _utc(approval.expires_at):
        return ExecutionDecision(
            "APPROVAL_EXPIRED", False, "Approval has expired.", intent_hash, simulation_hash
        )
    maximum = _amount(approval.maximum_amount)
    if maximum is None or amount > maximum:
        return ExecutionDecision(
            "LIMIT_EXCEEDED", False, "Intent exceeds the approved amount cap.", intent_hash, simulation_hash
        )
    if approval.intent_hash != intent_hash or approval.simulation_hash != simulation_hash:
        return ExecutionDecision(
            "APPROVAL_MISMATCH", False, "Intent or simulation changed after approval.", intent_hash, simulation_hash
        )

    key_material = f"{approval.approval_id}:{intent_hash}:{simulation_hash}"
    idempotency_key = "proofline-" + sha256(key_material.encode("utf-8")).hexdigest()[:32]
    return ExecutionDecision(
        "READY",
        True,
        "Exact intent is simulated, within limits and explicitly approved.",
        intent_hash,
        simulation_hash,
        idempotency_key,
    )

