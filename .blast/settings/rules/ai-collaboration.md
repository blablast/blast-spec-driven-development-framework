# AI Collaboration — blast Core AI Rules

> Source of truth for how AI collaborates with the developer on every blast phase.
> Referenced by: `CLAUDE.md`, agent prompts (requirements, design, tasks, impl, review).

These four rules take precedence over default model "helpful" behavior. They apply from steering through impl — no phase is exempt. Break one only with explicit user approval.

## 1./ Think before coding

Don't assume. Don't hide confusion. State ambiguity explicitly. Present multiple interpretations rather than silently picking one. Push back if a simpler approach exists. Stop and ask rather than guess.

**Apply at:** requirements gathering, design trade-offs, task breakdown, impl when spec is underspecified.

**Fails when:** AI "fills in the blank" with a plausible-looking assumption that quietly diverges from intent.

## 2./ Simplicity first

No features beyond what was asked. No abstractions for single-use code. No "flexibility" that wasn't requested. No error handling for impossible scenarios. The test: would a senior engineer say this is overcomplicated? If yes, rewrite it.

**Apply at:** design (reject speculative layers), tasks (no gold-plating), impl (YAGNI > DRY for single-use).

**Fails when:** AI adds configuration, generics, or "future-proofing" the user did not ask for.

## 3./ Surgical changes

Don't "improve" adjacent code. Don't refactor things that aren't broken. Match the existing style even if you'd do it differently. If you notice unrelated dead code, mention it, don't delete it. Every changed line should trace directly to the request.

**Apply at:** impl, review (with `--fix`), any edit to existing files.

**Fails when:** diff contains changes unrelated to the stated task — style tweaks, renames, "while I'm here" cleanups.

## 4./ Goal-driven execution

Transform "fix the bug" into "write a test that reproduces it, then make it pass." Transform "add validation" into "write tests for invalid inputs, then make them pass." Give it success criteria and watch it loop until done.

**Apply at:** impl (TDD is the default), review (measure against explicit criteria), validate-impl (pass/fail on concrete tests).

**Fails when:** task ends with "it probably works now" instead of a passing test or measurable outcome.
