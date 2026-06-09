# Approval check — shared rule

Single source of truth for phase-approval verification in orchestrator commands
(full, quick, tasks, impl). Commands reference this rule instead of restating it.

## ensure_phase_approved(feature, phase)

1. Read `.blast/specs/{feature}/spec.json`.
2. Approved when ANY of:
   - `approvals.{phase}.approved == true`
   - invocation carries `-y` → inject `Auto-approve: true` into the agent prompt
   - `tiny == true` (tiny specs self-approve)
   - `autonomy` is `low`/`medium` AND `approvals.{phase}.generated == true`
     AND NOT (`security_critical` OR `risk_level == "high"`) — risk-tiered
     autonomy, Constitution Art. I; gate-enforced by blast-approval-gate.py
3. Not approved → STOP with remediation: review artifact → `/blast:approve {feature} {phase}`
   → re-run; or `-y` bypass.

The SDK-level enforcement lives in `.claude/hooks/blast-approval-gate.py` (exit 2 = hard
block) — the command-level check exists only to fail fast with a friendlier message.
