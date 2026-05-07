import time
from typing import List, Tuple, Dict, Any

class InvalidTransition(Exception):
    pass

class StateMachine:
    def __init__(self, initial: str, transitions: dict):
        self._current = initial
        self._transitions = transitions
        self._history: List[Tuple[str, str, str, float]] = []
    
    @property
    def current(self) -> str:
        return self._current
    
    def can_transition(self, event: str) -> bool:
        return event in self._transitions.get(self._current, {})
    
    def transition(self, event: str) -> str:
        if not self.can_transition(event):
            raise InvalidTransition(f"Cannot transition from {self._current} with event {event}")
        
        from_state = self._current
        to_state = self._transitions[from_state][event]
        timestamp = time.monotonic()
        
        self._history.append((from_state, event, to_state, timestamp))
        self._current = to_state
        
        return to_state
    
    def history(self) -> list:
        return list(self._history)