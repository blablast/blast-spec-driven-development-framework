"""Tests for Task 04 — State Machine."""
import pytest
from state_machine import StateMachine, InvalidTransition


@pytest.fixture
def sm():
    return StateMachine(
        initial="draft",
        transitions={
            "draft": {"submit": "review", "discard": "deleted"},
            "review": {"approve": "published", "reject": "draft"},
            "published": {"archive": "archived"},
        },
    )


def test_initial_state(sm):
    assert sm.current == "draft"


def test_valid_transition(sm):
    new_state = sm.transition("submit")
    assert new_state == "review"
    assert sm.current == "review"


def test_invalid_transition_raises(sm):
    with pytest.raises(InvalidTransition):
        sm.transition("approve")  # not allowed from draft


def test_can_transition(sm):
    assert sm.can_transition("submit") is True
    assert sm.can_transition("approve") is False


def test_full_workflow(sm):
    sm.transition("submit")
    sm.transition("approve")
    sm.transition("archive")
    assert sm.current == "archived"


def test_terminal_state(sm):
    sm.transition("submit")
    sm.transition("approve")
    sm.transition("archive")
    # archived has no defined transitions
    assert sm.can_transition("submit") is False
    with pytest.raises(InvalidTransition):
        sm.transition("anything")


def test_history(sm):
    sm.transition("submit")
    sm.transition("reject")
    h = sm.history()
    assert len(h) == 2
    assert h[0][0] == "draft"
    assert h[0][1] == "submit"
    assert h[0][2] == "review"
    # timestamp should be present and numeric
    assert isinstance(h[0][3], (int, float))


def test_history_immutable(sm):
    sm.transition("submit")
    h1 = sm.history()
    h1_copy = list(h1)
    sm.transition("reject")
    # h1 reference shouldn't be silently mutated under the caller
    assert h1 == h1_copy or h1 != sm.history()
