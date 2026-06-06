from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .states import (
    ParticipantState,
    ParticipantStateMachine,
    VoteResult,
)


@dataclass
class Participant:
    id: str
    name: str = ""
    prepare_delay_seconds: float = 0.0
    _should_vote_yes: bool = True
    _state_machine: ParticipantStateMachine = field(
        default_factory=ParticipantStateMachine
    )
    on_prepare: Optional[Callable[["Participant"], None]] = None
    on_commit: Optional[Callable[["Participant"], None]] = None
    on_abort: Optional[Callable[["Participant"], None]] = None

    @property
    def state(self) -> ParticipantState:
        return self._state_machine.state

    def prepare(self) -> VoteResult:
        if not self._should_vote_yes:
            self._state_machine.transition_to(ParticipantState.ABORTED)
            if self.on_prepare is not None:
                self.on_prepare(self)
            return VoteResult.NO

        self._state_machine.transition_to(ParticipantState.PREPARED)
        if self.on_prepare is not None:
            self.on_prepare(self)
        return VoteResult.YES

    def commit(self) -> None:
        self._state_machine.transition_to(ParticipantState.COMMITTED)
        if self.on_commit is not None:
            self.on_commit(self)

    def abort(self) -> None:
        self._state_machine.transition_to(ParticipantState.ABORTED)
        if self.on_abort is not None:
            self.on_abort(self)

    def configure_vote(self, vote_yes: bool) -> None:
        self._should_vote_yes = vote_yes

    def configure_delay(self, seconds: float) -> None:
        self.prepare_delay_seconds = seconds
