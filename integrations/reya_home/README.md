# REYA HOME system engineering candidate

This integration extends the existing HOME durable task host with a bounded engineering task and a personal display name. Core, TaskContinuation, Work, Control Plane, N1 and the current permission grant remain authoritative. The local model and owner-authenticated code proposal are replaceable executors.

Status: **isolated Windows acceptance passed; production deployment not performed**. This directory is a source integration candidate for an existing HOME gen104 checkout, not a standalone HOME distribution. Its imports require that host. It does not start a second DeepSeek runtime, database or permission issuer.

## Reproducible GitHub checks

Run `python integrations/reya_home/check_contracts.py` and `node --check integrations/reya_home/candidate/web/genesis.js`. The workflow runs these portable source/contract checks with no credentials, model calls, package installation or deployment. It does not reproduce Windows CP/N1 integration, the real model run or browser acceptance. Those scopes are explicitly separated in `verification.json`.

## Engineering behavior

The first adapter, `python.admission-replay-repair/1`, addresses a real gen104 duplicate-task defect: the same task ID previously returned an old task even when input scope, budget or destination changed. The adapter pins the complete baseline at admission, reads two scoped inputs, records model proposals, writes separate patch/report artifacts through the existing CP, checks the exact permitted AST, source and output hashes, write receipts, syntax and request behavior, and commits one final transactionally in the same Core.

A rejected proposal can be replaced through the authenticated `/api/genesis/engineering/revise` seam. The saved mandate and previous attempts remain unchanged. Revision, deadline, budgets, STOP/revoke, current grant, source and writer fence still apply. UNKNOWN attempts cannot use this path. Revisions write new filenames and do not replay an earlier effect. This is deliberately a narrow repair profile, not unrestricted Python execution or arbitrary autonomous software development.

The integrated admission function also contains the verified scope repair, retaining its task-type comparison. The staged output repair targets the older gen104 baseline; it must not be applied blindly over this candidate.

## Identity and readiness

The technical label is **Системный агент REYA**, profile **Системная инженерия**. Personal names default to empty, support save/reset, use a compare-and-set update in the owner's existing profile, and never affect Person IDs, permissions, routing or budgets. UI text is rendered with `textContent`. HOME links to `/genesis`.

The card references the existing `backend.durable_goal.DurableGoals` implementation. Evidence is tied to implementation bytes and the recorded environment. The model route used in the recorded result is distinct from the current default route. A disk source change requires restart before new implementation claims. Historical registration REYA-JUNIOR-001 has no verified runtime mapping here; no historical identity or receipt is reassigned.

## Review and rollout

Two bounded Fable consultations were completed: pinned architecture comparison and final-diff review. The latter found mandatory checks implemented with `assert`, ambiguous current/default model attribution and an unpinned full baseline. These were corrected; targeted fault injection checks explicit failure under normal and optimized Python, source/output tampering, STOP before commit, deadline and admission replay conflicts. No independent runtime PASS is attributed to the reviewer.

Before production: reconcile current HOME source and active effects; use the existing release route, fresh authorization and writer fences; preserve current Core/history on rollback. A CI result or model report never authorizes merge or deployment. This PR deliberately has no auto-merge or deployment job.

## Attribution

Design reference: DeepSeek Harness / dsh-superagent at commit `6337fc823ce20251c8de8085948165c81aaa701e`, especially domain, authorization, execution and architecture documents. The upstream MIT license and copyright remain in the repository root. The adaptation reuses assignment/result separation and one domain writer while retaining REYA's verifier and reconciliation boundaries. This does not assert a formal partnership or upstream endorsement.
