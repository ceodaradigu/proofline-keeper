"""Capture a secret-free KeeperHub Base Sepolia evidence packet.

Simulation is the default. Broadcasting requires both ``--broadcast`` and a
non-empty ``--approval-id`` so an accidental invocation cannot create a write.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .core import TransactionIntent, authorize, evaluate_execution
from .keeperhub import KeeperHubClient, KeeperHubError


BASE_SEPOLIA_CHAIN_ID = 84532


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Unsupported evidence value: {type(value).__name__}")


def _require_stable_base_sepolia(client: KeeperHubClient) -> dict[str, object]:
    for chain in client.enabled_testnets():
        try:
            chain_id = int(str(chain.get("chainId", "")))
        except ValueError:
            continue
        if chain_id != BASE_SEPOLIA_CHAIN_ID:
            continue
        status = str(chain.get("status", "stable")).lower()
        if status != "stable":
            raise KeeperHubError(f"Base Sepolia is not stable (status={status}).")
        return chain
    raise KeeperHubError("Stable Base Sepolia is not enabled by KeeperHub.")


def capture_evidence(
    client: KeeperHubClient,
    *,
    recipient: str,
    amount: str,
    approval_id: str | None = None,
) -> dict[str, object]:
    """Simulate an exact intent and optionally broadcast that same intent once."""

    chain = _require_stable_base_sepolia(client)
    intent = TransactionIntent(
        chain_id=BASE_SEPOLIA_CHAIN_ID,
        to_address=recipient,
        amount=amount,
        purpose="Proofline Keeper hackathon evidence on Base Sepolia",
    )
    simulation = client.simulate_transfer(intent)
    checked_at = datetime.now(timezone.utc)
    decision = evaluate_execution(intent, simulation, None, now=checked_at)
    evidence: dict[str, object] = {
        "schema": "proofline-keeper-evidence/v1",
        "captured_at": checked_at,
        "network": {
            "chain_id": BASE_SEPOLIA_CHAIN_ID,
            "name": chain.get("name", "Base Sepolia"),
            "status": chain.get("status", "stable"),
        },
        "intent": asdict(intent),
        "simulation": asdict(simulation),
        "decision": decision.to_dict(),
        "broadcast": None,
        "status": None,
    }

    if approval_id is None:
        return evidence

    ticket = authorize(
        intent,
        simulation,
        maximum_amount=amount,
        approved_at=checked_at,
        ttl_minutes=15,
        approval_id=approval_id,
    )
    ready = evaluate_execution(intent, simulation, ticket, now=checked_at)
    broadcast = client.broadcast_transfer(intent, ready)
    evidence["broadcast"] = broadcast
    execution_id = broadcast.get("executionId")
    if not isinstance(execution_id, str):
        raise KeeperHubError("Broadcast response did not include an executionId.")
    evidence["decision"] = ready.to_dict()
    try:
        status = client.execution_status(execution_id)
    except (KeeperHubError, ValueError) as error:
        # A broadcast may already be final and carry its authoritative hash.
        # Preserve that response instead of losing all evidence merely because
        # a follow-up status lookup is temporarily unavailable.
        evidence["status"] = {
            "body": {"status": "unavailable", "error": str(error)},
            "poll_interval_hint": None,
        }
    else:
        evidence["status"] = {
            "body": status.body,
            "poll_interval_hint": status.headers.get("X-Poll-Interval-Hint"),
        }
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recipient", required=True, help="Base Sepolia recipient address"
    )
    parser.add_argument(
        "--amount", default="0.000001", help="Native testnet ETH amount"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="New JSON evidence file"
    )
    parser.add_argument(
        "--broadcast", action="store_true", help="Broadcast after a passing simulation"
    )
    parser.add_argument(
        "--approval-id", help="Holder approval reference; required with --broadcast"
    )
    args = parser.parse_args()

    if args.broadcast != bool(args.approval_id):
        parser.error("--broadcast and --approval-id must be supplied together")
    api_key = os.environ.get("KH_API_KEY", "")
    if not api_key.startswith("kh_"):
        parser.error("KH_API_KEY must contain a KeeperHub organization key")

    packet = capture_evidence(
        KeeperHubClient(api_key),
        recipient=args.recipient,
        amount=args.amount,
        approval_id=args.approval_id if args.broadcast else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(packet, handle, indent=2, sort_keys=True, default=_json_safe)
        handle.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
