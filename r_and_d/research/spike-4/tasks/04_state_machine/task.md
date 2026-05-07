# Task 04 — Workflow State Machine

Implement a workflow state machine with transition validation in `state_machine.py`.

## Spec

```python
class StateMachine:
    def __init__(self, initial: str, transitions: dict):
        """
        transitions: {from_state: {event_name: to_state}}

        Example: {
            "draft": {"submit": "review", "discard": "deleted"},
            "review": {"approve": "published", "reject": "draft"},
            "published": {"archive": "archived"},
        }
        """

    @property
    def current(self) -> str: ...

    def can_transition(self, event: str) -> bool:
        """True iff `event` is a valid transition from current state."""

    def transition(self, event: str) -> str:
        """Move to next state. Raise InvalidTransition if not allowed."""

    def history(self) -> list:
        """Return list of (from_state, event, to_state, timestamp) tuples."""

class InvalidTransition(Exception): ...
```

## Requirements

- `time.monotonic()` for timestamps in history
- Raise descriptive `InvalidTransition` with current_state + event
- History append-only (no mutations after fact)
- Pure stdlib only

## Acceptance criteria

All tests in `tests.py` must pass.
