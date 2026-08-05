# Proofline Keeper

> Developed with AI assistance under human direction. All safety behavior is
> covered by deterministic tests; live transactions require explicit approval.

Proofline Keeper is an evidence-gated execution boundary for AI agents using
KeeperHub. The agent can propose a transaction, but it cannot broadcast unless
the exact intent has passed KeeperHub simulation and a human has approved that
same simulation within an explicit amount cap and time window.

## Why this exists

Agent execution often fails after reasoning succeeds: transaction parameters
change, stale simulations are reused, approvals are interpreted too broadly,
or retries create duplicate writes. Proofline Keeper makes those failure modes
explicit and deterministic.

The repository contains the deterministic safety core and a minimal adapter for
KeeperHub's documented Direct Execution API. It does **not** yet claim a
broadcast transaction, hosted demo, or prize.

## Safety invariants

- Every write must be simulated first.
- A failed, reverting, future-dated, or stale simulation blocks execution.
- Approval is bound to hashes of the exact intent and simulation.
- The approved amount is a hard cap.
- Approval expires.
- Any recipient, amount, token, chain, purpose, or simulation change invalidates
  the approval.
- A stable idempotency key prevents accidental duplicate retries.
- The deterministic core stores no private key and performs no network calls.
- The API key is held only by the adapter and is never returned or logged.
- Broadcast is refused unless the decision is `READY` and still matches the
  exact intent.

## Run locally

```bash
python -m pytest -q
```

No API key is required to run the tests. Live use requires an organization key
whose value starts with `kh_`; keep it in a secret manager or environment
variable and never commit it.

## Planned KeeperHub flow

1. Build a `TransactionIntent` from the requested action.
2. Call `POST /api/execute/transfer` with `simulate: true`.
3. Convert the authoritative preflight response into `SimulationReceipt`.
4. Show the exact intent, gas estimate, amount cap, and expiry for approval.
5. Call `evaluate_execution` immediately before broadcast.
6. Only for `READY`, repeat the same KeeperHub call without `simulate` and with
   the returned `idempotency_key`.
7. Poll `GET /api/execute/{executionId}/status`, honour its poll hint, and
   persist verified receipts, the transaction link, and the audit trail.

The first live demonstration will use Base Sepolia and faucet funds. Mainnet
funds will not be used merely to create a hackathon demo.

## Competition target

Built for the worldwide KeeperHub Agents Onchain Hackathon. The target is the
main agent prize and the separately judged Best Onboarding UX Improvement
bounty. The final submission still requires a public repository, a demo video,
and a real transaction executed through KeeperHub.
