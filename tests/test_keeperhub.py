from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from proofline_keeper import (
    SimulationReceipt,
    TransactionIntent,
    authorize,
    evaluate_execution,
    fingerprint_intent,
)
from proofline_keeper.keeperhub import ApiResponse, KeeperHubClient, KeeperHubError


NOW = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
TO = "0x1111111111111111111111111111111111111111"


@dataclass
class Call:
    method: str
    url: str
    body: dict[str, object] | None
    headers: dict[str, str]


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls: list[Call] = []

    def __call__(self, method, url, body, headers):
        self.calls.append(Call(method, url, body, dict(headers)))
        return next(self.responses)


def tx() -> TransactionIntent:
    return TransactionIntent(84532, TO, "0.001", purpose="Publish proof on Base Sepolia")


def ready_decision(intent: TransactionIntent):
    sim = SimulationReceipt(fingerprint_intent(intent), True, False, NOW, "42000")
    ticket = authorize(
        intent,
        sim,
        maximum_amount="0.001",
        approved_at=NOW,
        ttl_minutes=15,
        approval_id="demo-001",
    )
    return evaluate_execution(intent, sim, ticket, now=NOW)


def test_simulation_uses_strict_boolean_and_no_idempotency_header():
    fake = FakeTransport([ApiResponse(200, {
        "success": True, "wouldRevert": False, "gasEstimate": "42000"
    }, {})])
    client = KeeperHubClient("kh_test_secret", transport=fake)

    receipt = client.simulate_transfer(tx())

    assert receipt.success is True
    assert fake.calls[0].url.endswith("/api/execute/transfer")
    assert fake.calls[0].body["simulate"] is True
    assert "Idempotency-Key" not in fake.calls[0].headers


def test_broadcast_refuses_non_ready_decision_without_network_call():
    fake = FakeTransport([])
    client = KeeperHubClient("kh_test_secret", transport=fake)
    blocked = evaluate_execution(tx(), None, None, now=NOW)

    with pytest.raises(KeeperHubError, match="not READY"):
        client.broadcast_transfer(tx(), blocked)

    assert fake.calls == []


def test_broadcast_reuses_exact_body_and_sets_idempotency_key():
    fake = FakeTransport([ApiResponse(202, {
        "executionId": "direct_123", "status": "completed"
    }, {})])
    intent = tx()
    decision = ready_decision(intent)
    client = KeeperHubClient("kh_test_secret", transport=fake)

    result = client.broadcast_transfer(intent, decision)

    assert result["executionId"] == "direct_123"
    assert "simulate" not in fake.calls[0].body
    assert fake.calls[0].headers["Idempotency-Key"] == decision.idempotency_key


def test_changed_intent_is_blocked_after_ready_decision():
    fake = FakeTransport([])
    original = tx()
    client = KeeperHubClient("kh_test_secret", transport=fake)
    changed = TransactionIntent(84532, TO, "0.002", purpose=original.purpose)

    with pytest.raises(KeeperHubError, match="intent changed"):
        client.broadcast_transfer(changed, ready_decision(original))


def test_status_uses_documented_endpoint_and_preserves_poll_hint():
    fake = FakeTransport([ApiResponse(200, {
        "executionId": "direct_123", "status": "completed", "receipts": []
    }, {"X-Poll-Interval-Hint": "0"})])
    client = KeeperHubClient("kh_test_secret", transport=fake)

    response = client.execution_status("direct_123")

    assert fake.calls[0].url.endswith("/api/execute/direct_123/status")
    assert response.headers["X-Poll-Interval-Hint"] == "0"


def test_api_key_is_not_exposed_by_safe_error():
    fake = FakeTransport([ApiResponse(401, {"error": "Invalid API key"}, {})])
    client = KeeperHubClient("kh_unit", transport=fake)

    with pytest.raises(KeeperHubError) as caught:
        client.enabled_testnets()

    assert "kh_unit" not in str(caught.value)
