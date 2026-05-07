import time


class InvalidTransition(Exception):
    pass


class StateMachine:
    def __init__(self, initial: str, transitions: dict):
        self._current = initial
        self._transitions = transitions
        self._history = []

    @property
    def current(self) -> str:
        return self._current

    def can_transition(self, event: str) -> bool:
        return event in self._transitions.get(self._current, {})

    def transition(self, event: str) -> str:
        if not self.can_transition(event):
            raise InvalidTransition(f"Cannot transition from '{self._current}' via '{event}'")
        from_state = self._current
        to_state = self._transitions[self._current][event]
        self._history.append((from_state, event, to_state, time.monotonic()))
        self._current = to_state
        return self._current

    def history(self) -> list:
        return list(self._history)