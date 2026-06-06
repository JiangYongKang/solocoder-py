from typing import List
import uuid

from solocoder_py.twopc import (
    Coordinator,
    DecisionLog,
    Participant,
)

_TIMEOUT_DELAY_SECONDS: float = 999.0


def make_participant(
    vote_yes: bool = True,
    should_timeout: bool = False,
    name: str = "",
) -> Participant:
    pid = str(uuid.uuid4())
    participant = Participant(id=pid, name=name or f"participant-{pid[:8]}")
    participant.configure_vote(vote_yes)
    if should_timeout:
        participant.configure_delay(_TIMEOUT_DELAY_SECONDS)
    return participant


def make_participants(
    count: int,
    all_vote_yes: bool = True,
    timeout_indexes: List[int] | None = None,
) -> List[Participant]:
    participants = []
    timeout_indexes = timeout_indexes or []
    for i in range(count):
        vote_yes = all_vote_yes
        should_timeout = i in timeout_indexes
        participants.append(
            make_participant(
                vote_yes=vote_yes,
                should_timeout=should_timeout,
                name=f"participant-{i}",
            )
        )
    return participants


def make_coordinator(
    transaction_id: str | None = None,
    decision_log: DecisionLog | None = None,
    prepare_timeout_seconds: float = 10.0,
) -> Coordinator:
    tid = transaction_id or str(uuid.uuid4())
    log = decision_log or DecisionLog()
    return Coordinator(
        transaction_id=tid,
        decision_log=log,
        prepare_timeout_seconds=prepare_timeout_seconds,
    )
