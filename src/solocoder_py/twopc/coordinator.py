from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .logger import DecisionLog
from .participant import Participant
from .states import CoordinatorDecision, ParticipantState, VoteResult


class TransactionAlreadyExecutedError(Exception):
    pass


@dataclass
class TransactionResult:
    transaction_id: str
    decision: CoordinatorDecision
    participants_voted_yes: List[str]
    participants_voted_no: List[str]
    participants_timed_out: List[str]


@dataclass
class Coordinator:
    transaction_id: str
    decision_log: DecisionLog
    prepare_timeout_seconds: float = 10.0
    _participants: Dict[str, Participant] = field(default_factory=dict)
    _executed: bool = False
    _result: Optional[TransactionResult] = None

    @property
    def is_executed(self) -> bool:
        return self._executed

    @property
    def result(self) -> Optional[TransactionResult]:
        return self._result

    def register_participant(self, participant: Participant) -> None:
        if self._executed:
            raise TransactionAlreadyExecutedError(
                f"Transaction {self.transaction_id} already executed"
            )
        self._participants[participant.id] = participant

    def register_participants(self, participants: List[Participant]) -> None:
        for p in participants:
            self.register_participant(p)

    def get_participant(self, participant_id: str) -> Optional[Participant]:
        return self._participants.get(participant_id)

    def list_participants(self) -> List[Participant]:
        return list(self._participants.values())

    def execute(self) -> TransactionResult:
        if self._executed:
            raise TransactionAlreadyExecutedError(
                f"Transaction {self.transaction_id} already executed"
            )

        if self.decision_log.has_entry(self.transaction_id):
            return self._recover_from_log()

        voted_yes: List[str] = []
        voted_no: List[str] = []
        timed_out: List[str] = []

        all_votes_yes = self._run_prepare_phase(voted_yes, voted_no, timed_out)

        if all_votes_yes:
            decision = CoordinatorDecision.COMMIT
        else:
            decision = CoordinatorDecision.ABORT

        self.decision_log.record_decision(
            self.transaction_id, decision, list(self._participants.keys())
        )

        self._run_decision_phase(decision)

        self.decision_log.mark_executed(self.transaction_id)

        self._executed = True
        self._result = TransactionResult(
            transaction_id=self.transaction_id,
            decision=decision,
            participants_voted_yes=voted_yes,
            participants_voted_no=voted_no,
            participants_timed_out=timed_out,
        )
        return self._result

    def _run_prepare_phase(
        self,
        voted_yes: List[str],
        voted_no: List[str],
        timed_out: List[str],
    ) -> bool:
        all_yes = True

        for participant in self._participants.values():
            if participant.prepare_delay_seconds > self.prepare_timeout_seconds:
                timed_out.append(participant.id)
                all_yes = False
                continue

            vote = participant.prepare()
            if vote == VoteResult.YES:
                voted_yes.append(participant.id)
            else:
                voted_no.append(participant.id)
                all_yes = False

        return all_yes and len(self._participants) > 0

    def _run_decision_phase(self, decision: CoordinatorDecision) -> None:
        for participant in self._participants.values():
            if decision == CoordinatorDecision.COMMIT:
                if participant.state == ParticipantState.PREPARED:
                    participant.commit()
            else:
                if participant.state == ParticipantState.PREPARED:
                    participant.abort()

    def _recover_from_log(self) -> TransactionResult:
        entry = self.decision_log.get_entry(self.transaction_id)
        assert entry is not None

        voted_yes: List[str] = []
        voted_no: List[str] = []
        timed_out: List[str] = []

        for pid in entry.participant_ids:
            participant = self._participants.get(pid)
            if participant is None:
                continue
            if participant.state == ParticipantState.PREPARED:
                voted_yes.append(pid)
            elif participant.state == ParticipantState.ABORTED:
                voted_no.append(pid)

        self._run_decision_phase(entry.decision)

        if not entry.executed:
            self.decision_log.mark_executed(self.transaction_id)

        self._executed = True
        self._result = TransactionResult(
            transaction_id=self.transaction_id,
            decision=entry.decision,
            participants_voted_yes=voted_yes,
            participants_voted_no=voted_no,
            participants_timed_out=timed_out,
        )
        return self._result
