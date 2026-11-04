# GUI model provider — SOURCE_ONLY research component

This portable component studies a single explicitly authorized model request through a foreground desktop GUI. It is **not an installed model route or working Windows automation service**. No provider credentials, private history, production database, runtime account identifier or host configuration is included.

The provider has typed request, source, app-pin, attachment and result contracts. It checks immutable request provenance, the expected model, current trusted authority, and durable effect state. A stable host-issued `operation_id` survives retry UUIDs. The SQLite effect ledger records UNKNOWN before the sole Send attempt and preserves uncertain effects for explicit reconciliation. It is an adapter audit journal, not a Core, memory store or task queue. A saved result can be recovered without another Send.

Three model labels are supported by the source contract: GPT-6 Astra, GPT-6.1 Terra and GPT-6.1 Sol. These labels are UI observations rather than provider API attestations. The code verifies an explicitly selected expected model; actual native selector automation is not implemented. Subscription entitlement and automation permission must be independently verified by the host. No API or paid fallback exists.

## Reproduce the portable checks

Python 3.11 and Node.js 22, with no additional packages:

```sh
python -B verify_manifest.py
python -B run_checks.py
```

Run from this directory. The test runner writes an ignored receipt with source hashes, outputs and exit codes. The baseline has 43 Python tests and 20 JavaScript tests. UI, identity, N1, provider response and clipboard are synthetic ports; local files, SQLite transactions and an abrupt child process exit are real isolated fixtures. This does not prove actual desktop automation, account authorization, hardware power-loss recovery, or production acceptance.

Negative cases cover app/process/window/DPI/layout/model drift, wrong foreground/locked session, expired login (`REQUIRES_OWNER_LOGIN`), unknown entitlement/terms, private source kind, rejected/tampered attachments, STOP/revocation/cancellation, concurrent writers, clipboard races/contention/restore failure, stale replies, uncertain Sends and duplicate result recovery. All three model labels are exercised only in synthetic contracts.

## Required trusted integrations — currently absent

- Current host Person/ACL/N1/STOP/revoke/budget authority and a shared, per-input GUI admission fence. The host must preserve the stable logical-operation key across retries and bind all callers to one canonical effect ledger. A new key requires a distinct trusted intent.
- A trustworthy fresh native observer for app package/signer/executable/process/session/window/DPI/layout, actual model/chat, file acceptance and reply identity. The included CUA port refuses an unavailable accessibility tree. It has no coordinate or shell input fallback.
- A native clipboard custodian that snapshots current content immediately before Copy, identifies its own write, preserves all formats, restores with CAS and verifies restoration even across caller failure. The provided protocol is a requirement, not that implementation.
- A reviewed Python-to-async-CUA binding and verified terms allowing the intended provider interaction. No daemon is supplied.

The only supplied real-host authority **denies dispatch**. Synthetic ports in tests cannot substitute for it. PUBLIC_SOURCE and SYNTHETIC labels do not self-authorize content: the real host must attest provenance and scope. Output is untrusted model data, never authority.

Each actual CUA input owns the host fence independently. The expected dialog path is revalidated inside the Open fence before its click; the real host must also keep staged bytes immutable through attachment. Send rechecks the exact attachment and empty composer inside its input fence. Copy requires explicit positive reply verification. Python holds no fence across a GUI observation or compound UI operation. A bounded local result commit is serialized with revoke; saved-result delivery rechecks current authority and logical-operation cancellation, including retry aliases. Cancellation before the first call binds the stable operation ID, independently of retry UUID, payload or size limits. Failed-transition annotations reload the last committed row and never retry an uncommitted result. A cooperative file lock does not replace host-wide authority. Durability assumes SQLite's OS/VFS/storage synchronization contract, not arbitrary disk or database tampering protection.

The clipboard contract distinguishes trusted proof of NO_WRITE or RESTORED from unknown cleanup. The CUA step marks a rejection before attempting input; the future trusted async binding must map only that marker to `InputNotAdmitted`. Arbitrary errors, timeouts after attempted input and unverified restoration remain potentially dirty and require an alert. This classification is contract-tested, not native clipboard implementation proof. The SQLite prototype schema is version 1; an existing unversioned ledger is refused read-only with `LEDGER_SCHEMA_UPGRADE_REQUIRED`. Reconcile and explicitly migrate old journals before reuse, preserving cancellations and UNKNOWN effects; this component performs no automatic migration.

Do not register this component as a production route from a green CI result. Do not remove UNKNOWN ledgers or stale locks to enable retries. Reconcile the original operation, request, effect and chat first. New runtime integration requires its own privacy, consent, recovery, release and real-device acceptance gates. No Core database rollback is part of this component.

## Review history and origin

Independent static reviews found durability, clipboard-snapshot, nested-fence and duplicate-retry defects in earlier candidates. A PR review also found a failed-result-save retry after revoke/cancel and a stale dialog-path check. The current candidate fixes those paths and adds pre-commit failure/control-intervention and in-fence dialog regressions. The latest whole revision has root review and synthetic tests; it has no independent production acceptance. Runtime hard blockers are preserved.

This new portable source was authored for REYA and uses documented CUA APIs by name. It imports no private HOME source and copies no upstream implementation. The repository's existing DeepSeek Harness MIT attribution and license are retained. This is not a claim of a formal provider partnership, guaranteed unlimited service or API access.
