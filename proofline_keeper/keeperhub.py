"""Minimal KeeperHub Direct Execution API adapter.

The adapter keeps the API key out of payloads and returned objects. Network
transport is injectable so the broadcast gate can be tested without touching a
chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .core import (
    ExecutionDecision,
    SimulationReceipt,
    TransactionIntent,
    fingerprint_intent,
)


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: dict[str, object]
    headers: Mapping[str, str]


class KeeperHubError(RuntimeError):
    """Safe API error that never contains request headers or API keys."""


Transport = Callable[[str, str, dict[str, object] | None, Mapping[str, str]], ApiResponse]


def _urllib_transport(
    method: str,
    url: str,
    body: dict[str, object] | None,
    headers: Mapping[str, str],
) -> ApiResponse:
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=data, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return ApiResponse(response.status, parsed, dict(response.headers.items()))
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": "KeeperHub returned a non-JSON error."}
        message = parsed.get("error", "KeeperHub request failed.")
        raise KeeperHubError(f"KeeperHub HTTP {error.code}: {message}") from None
    except URLError as error:
        raise KeeperHubError(f"KeeperHub connection failed: {error.reason}") from None


class KeeperHubClient:
    """Direct-execution client with simulation-first broadcast enforcement."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://app.keeperhub.com",
        transport: Transport | None = None,
    ) -> None:
        if not api_key.startswith("kh_"):
            raise ValueError("A KeeperHub organization API key is required.")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._transport = transport or _urllib_transport

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        response = self._transport(method, self._base_url + path, body, headers)
        if not 200 <= response.status < 300:
            message = response.body.get("error", "KeeperHub request failed.")
            raise KeeperHubError(f"KeeperHub HTTP {response.status}: {message}")
        return response

    @staticmethod
    def _transfer_body(intent: TransactionIntent) -> dict[str, object]:
        body: dict[str, object] = {
            "chainId": intent.chain_id,
            "recipientAddress": intent.to_address,
            "amount": intent.amount,
        }
        if intent.token_address is not None:
            body["tokenAddress"] = intent.token_address
        return body

    def enabled_testnets(self) -> list[dict[str, object]]:
        response = self._request("GET", "/api/chains")
        chains = response.body.get("chains", response.body)
        if isinstance(chains, list):
            return [
                chain
                for chain in chains
                if isinstance(chain, dict)
                and chain.get("isEnabled") is True
                and chain.get("isTestnet") is True
            ]
        raise KeeperHubError("KeeperHub returned an unexpected chains response.")

    def simulate_transfer(self, intent: TransactionIntent) -> SimulationReceipt:
        body = self._transfer_body(intent)
        body["simulate"] = True
        response = self._request("POST", "/api/execute/transfer", body)
        payload = response.body
        return SimulationReceipt(
            intent_hash=fingerprint_intent(intent),
            success=payload.get("success") is True,
            would_revert=payload.get("wouldRevert") is not False,
            observed_at=datetime.now(timezone.utc),
            gas_estimate=str(payload.get("gasEstimate", "")),
        )

    def broadcast_transfer(
        self,
        intent: TransactionIntent,
        decision: ExecutionDecision,
    ) -> dict[str, object]:
        if not decision.ready or decision.code != "READY" or not decision.idempotency_key:
            raise KeeperHubError("Broadcast blocked: execution decision is not READY.")
        if decision.intent_hash != fingerprint_intent(intent):
            raise KeeperHubError("Broadcast blocked: intent changed after approval.")
        response = self._request(
            "POST",
            "/api/execute/transfer",
            self._transfer_body(intent),
            idempotency_key=decision.idempotency_key,
        )
        return response.body

    def execution_status(self, execution_id: str) -> ApiResponse:
        if not execution_id.startswith("direct_"):
            raise ValueError("Invalid direct execution id.")
        return self._request("GET", f"/api/execute/{execution_id}/status")
