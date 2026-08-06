# Proofline Keeper — submission draft

## One-line pitch

Proofline Keeper is an evidence-gated execution boundary that lets an AI agent use KeeperHub while preventing stale approvals, changed transaction intent, and duplicate broadcasts.

## What it solves

An agent can reason correctly and still execute the wrong transaction when parameters change after simulation, an approval is interpreted too broadly, or a retry creates a duplicate write. Proofline Keeper binds approval to the exact simulated intent, amount cap, expiry, and idempotency key.

## How KeeperHub is used

1. Discover the enabled testnet and simulate the exact transfer through KeeperHub.
2. Convert the response into a deterministic `SimulationReceipt`.
3. Refuse broadcast unless the decision is `READY` and a holder approval matches the same intent and simulation hashes.
4. Broadcast once with a stable idempotency key.
5. Poll KeeperHub for final status and save a secret-free evidence packet containing the execution ID, transaction hash, and explorer link.

## Why it is useful

- Makes the approval boundary visible before any write.
- Rejects stale, reverting, future-dated, or mutated simulations.
- Keeps private keys out of the deterministic core.
- Produces a reproducible audit receipt instead of an unverifiable success claim.
- Gives first-time KeeperHub users a simulation-first path with a clear transition to an approved broadcast.

## Evidence

- Public repository: https://github.com/ceodaradigu/proofline-keeper
- Tests: 22 focused deterministic tests passing.
- AI-assistance disclosure: visible in the repository README.
- Live transaction: https://sepolia.basescan.org/tx/0x1772f39f5beb7bfeb6813124bccd3854bf31d956b65ac9becf8541c83867e040
- KeeperHub evidence: execution `wl0b2ni7142qluy0qvvko`, status `completed`, verified receipt in block `45139083`, sponsored gas, and secret-free packet at `evidence/base-sepolia-live.json`.
- Demo video: **PENDING — record after the real evidence packet exists.**

## Final submission gate

- [x] Public MIT-licensed repository
- [x] Safety core, KeeperHub adapter, and evidence CLI
- [x] Deterministic test coverage
- [x] AI-assistance disclosure
- [x] Finish KeeperHub 2FA
- [x] Obtain the organization API key without recording it in the repository
- [x] Fund the organization wallet with free Base Sepolia faucet ETH
- [x] Run the simulation-only evidence command
- [x] Approve the exact testnet intent and execute one Base Sepolia transaction
- [x] Verify the transaction receipt and explorer link
- [ ] Record a short demo using the real evidence packet
- [ ] Replace both `PENDING` fields above and submit to DoraHacks

No transaction, prize, or award is claimed until the corresponding authoritative evidence exists.
