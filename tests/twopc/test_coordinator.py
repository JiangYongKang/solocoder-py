import pytest

from solocoder_py.twopc import (
    Coordinator,
    CoordinatorDecision,
    DecisionLog,
    InvalidStateTransitionError,
    Participant,
    ParticipantState,
    TransactionAlreadyExecutedError,
    VoteResult,
)
from .conftest import make_participant, make_participants, make_coordinator


class TestParticipantStateMachine:
    def test_initial_state(self):
        p = make_participant()
        assert p.state == ParticipantState.INITIAL

    def test_prepare_vote_yes_transitions_to_prepared(self):
        p = make_participant(vote_yes=True)
        result = p.prepare()
        assert result == VoteResult.YES
        assert p.state == ParticipantState.PREPARED

    def test_prepare_vote_no_transitions_to_aborted(self):
        p = make_participant(vote_yes=False)
        result = p.prepare()
        assert result == VoteResult.NO
        assert p.state == ParticipantState.ABORTED

    def test_delay_configuration(self):
        p = make_participant()
        assert p.prepare_delay_seconds == 0.0
        p.configure_delay(5.5)
        assert p.prepare_delay_seconds == 5.5

    def test_prepared_can_commit(self):
        p = make_participant(vote_yes=True)
        p.prepare()
        p.commit()
        assert p.state == ParticipantState.COMMITTED

    def test_prepared_can_abort(self):
        p = make_participant(vote_yes=True)
        p.prepare()
        p.abort()
        assert p.state == ParticipantState.ABORTED

    def test_initial_can_abort(self):
        p = make_participant()
        p.abort()
        assert p.state == ParticipantState.ABORTED

    def test_committed_is_terminal_cannot_abort(self):
        p = make_participant(vote_yes=True)
        p.prepare()
        p.commit()
        with pytest.raises(InvalidStateTransitionError):
            p.abort()

    def test_aborted_is_terminal_cannot_commit(self):
        p = make_participant(vote_yes=True)
        p.prepare()
        p.abort()
        with pytest.raises(InvalidStateTransitionError):
            p.commit()

    def test_initial_cannot_commit_directly(self):
        p = make_participant()
        with pytest.raises(InvalidStateTransitionError):
            p.commit()


class TestCallbackTimingConsistency:
    def test_prepare_callback_fires_after_state_transition_yes(self):
        states_seen = []

        def on_prepare(p):
            states_seen.append(p.state)

        p = Participant(id="p-cb-yes", on_prepare=on_prepare)
        p.prepare()
        assert len(states_seen) == 1
        assert states_seen[0] == ParticipantState.PREPARED

    def test_prepare_callback_fires_after_state_transition_no(self):
        states_seen = []

        def on_prepare(p):
            states_seen.append(p.state)

        p = Participant(id="p-cb-no", on_prepare=on_prepare)
        p.configure_vote(False)
        p.prepare()
        assert len(states_seen) == 1
        assert states_seen[0] == ParticipantState.ABORTED

    def test_commit_callback_fires_after_state_transition(self):
        states_seen = []

        def on_commit(p):
            states_seen.append(p.state)

        p = Participant(id="p-cb-commit", on_commit=on_commit)
        p.prepare()
        p.commit()
        assert len(states_seen) == 1
        assert states_seen[0] == ParticipantState.COMMITTED

    def test_abort_callback_fires_after_state_transition(self):
        states_seen = []

        def on_abort(p):
            states_seen.append(p.state)

        p = Participant(id="p-cb-abort", on_abort=on_abort)
        p.prepare()
        p.abort()
        assert len(states_seen) == 1
        assert states_seen[0] == ParticipantState.ABORTED


class TestNormalCommitFlow:
    def test_all_participants_agree_commit_succeeds(self):
        participants = make_participants(3, all_vote_yes=True)
        log = DecisionLog()
        coord = make_coordinator(decision_log=log)
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        assert len(result.participants_voted_yes) == 3
        assert len(result.participants_voted_no) == 0
        assert len(result.participants_timed_out) == 0
        for p in participants:
            assert p.state == ParticipantState.COMMITTED

        assert coord.is_executed is True
        assert log.get_entry(coord.transaction_id) is not None
        assert log.get_entry(coord.transaction_id).executed is True

    def test_single_participant_commit(self):
        p = make_participant(vote_yes=True)
        coord = make_coordinator()
        coord.register_participant(p)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        assert p.state == ParticipantState.COMMITTED

    def test_multiple_participants_all_vote_yes(self):
        participants = make_participants(5, all_vote_yes=True)
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        for p in participants:
            assert p.state == ParticipantState.COMMITTED


class TestAbortFlow:
    def test_some_participants_vote_no_aborts_prepared_only(self):
        participants = make_participants(3, all_vote_yes=True)
        participants[1].configure_vote(False)
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert participants[0].id in result.participants_voted_yes
        assert participants[1].id in result.participants_voted_no
        assert participants[2].id in result.participants_voted_yes

        assert participants[0].state == ParticipantState.ABORTED
        assert participants[1].state == ParticipantState.ABORTED
        assert participants[2].state == ParticipantState.ABORTED

    def test_first_participant_votes_no_rest_yes_aborts_all_prepared(self):
        participants = make_participants(3, all_vote_yes=True)
        participants[0].configure_vote(False)
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert participants[0].state == ParticipantState.ABORTED
        assert participants[1].state == ParticipantState.ABORTED
        assert participants[2].state == ParticipantState.ABORTED

    def test_all_participants_vote_no(self):
        participants = make_participants(3, all_vote_yes=False)
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert len(result.participants_voted_no) == 3
        for p in participants:
            assert p.state == ParticipantState.ABORTED


class TestTimeoutAbort:
    def test_single_participant_timeout_causes_abort_and_keeps_initial(self):
        participants = make_participants(3, all_vote_yes=True, timeout_indexes=[1])
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert len(result.participants_timed_out) == 1
        assert participants[1].id in result.participants_timed_out

        assert participants[0].state == ParticipantState.ABORTED
        assert participants[1].state == ParticipantState.INITIAL
        assert participants[2].state == ParticipantState.ABORTED

    def test_first_participant_times_out(self):
        participants = make_participants(3, all_vote_yes=True, timeout_indexes=[0])
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert participants[0].state == ParticipantState.INITIAL
        assert participants[1].state == ParticipantState.ABORTED
        assert participants[2].state == ParticipantState.ABORTED

    def test_multiple_participants_timeout(self):
        participants = make_participants(4, all_vote_yes=True, timeout_indexes=[0, 2])
        coord = make_coordinator()
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert len(result.participants_timed_out) == 2
        assert participants[0].state == ParticipantState.INITIAL
        assert participants[1].state == ParticipantState.ABORTED
        assert participants[2].state == ParticipantState.INITIAL
        assert participants[3].state == ParticipantState.ABORTED

    def test_timeout_participant_prepare_not_called(self):
        prepare_called = []

        def on_prepare(p):
            prepare_called.append(p.id)

        p_fast = Participant(id="p-fast", on_prepare=on_prepare)
        p_slow = Participant(id="p-slow", prepare_delay_seconds=100.0, on_prepare=on_prepare)

        coord = make_coordinator(prepare_timeout_seconds=10.0)
        coord.register_participants([p_fast, p_slow])
        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert "p-fast" in prepare_called
        assert "p-slow" not in prepare_called
        assert p_slow.state == ParticipantState.INITIAL

    def test_delay_within_timeout_not_treated_as_timeout(self):
        p = Participant(id="p-delay-ok", prepare_delay_seconds=2.0)
        coord = make_coordinator(prepare_timeout_seconds=5.0)
        coord.register_participant(p)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        assert len(result.participants_timed_out) == 0
        assert p.state == ParticipantState.COMMITTED

    def test_delay_exactly_at_timeout_threshold_treated_as_ok(self):
        p = Participant(id="p-delay-exact", prepare_delay_seconds=5.0)
        coord = make_coordinator(prepare_timeout_seconds=5.0)
        coord.register_participant(p)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        assert len(result.participants_timed_out) == 0
        assert p.state == ParticipantState.COMMITTED

    def test_timeout_participant_abort_callback_not_invoked(self):
        abort_called = []

        def on_abort(p):
            abort_called.append(p.id)

        p_ok = Participant(id="p-ok", on_abort=on_abort)
        p_timeout = Participant(id="p-timeout", prepare_delay_seconds=100.0, on_abort=on_abort)

        coord = make_coordinator(prepare_timeout_seconds=5.0)
        coord.register_participants([p_ok, p_timeout])
        coord.execute()

        assert "p-ok" in abort_called
        assert "p-timeout" not in abort_called


class TestEmptyTransaction:
    def test_no_participants_aborts(self):
        coord = make_coordinator()
        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert len(result.participants_voted_yes) == 0
        assert len(result.participants_voted_no) == 0
        assert len(result.participants_timed_out) == 0
        assert coord.is_executed is True


class TestCoordinatorRecovery:
    def test_recovery_replays_commit_decision(self):
        participants = make_participants(3, all_vote_yes=True)
        log = DecisionLog()
        tid = "tx-recover-commit"

        log.record_decision(tid, CoordinatorDecision.COMMIT, [p.id for p in participants])
        entry = log.get_entry(tid)
        assert entry.executed is False

        for p in participants:
            p.prepare()

        coord = Coordinator(
            transaction_id=tid, decision_log=log, prepare_timeout_seconds=10.0
        )
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        for p in participants:
            assert p.state == ParticipantState.COMMITTED
        assert log.get_entry(tid).executed is True

    def test_recovery_replays_abort_decision_only_prepared(self):
        participants = make_participants(3, all_vote_yes=True)
        log = DecisionLog()
        tid = "tx-recover-abort"

        log.record_decision(tid, CoordinatorDecision.ABORT, [p.id for p in participants])

        participants[0].prepare()
        participants[1].prepare()

        coord = Coordinator(
            transaction_id=tid, decision_log=log, prepare_timeout_seconds=10.0
        )
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.ABORT
        assert participants[0].state == ParticipantState.ABORTED
        assert participants[1].state == ParticipantState.ABORTED
        assert participants[2].state == ParticipantState.INITIAL

    def test_recovery_with_already_executed_entry(self):
        participants = make_participants(2, all_vote_yes=True)
        log = DecisionLog()
        tid = "tx-already-executed"

        log.record_decision(tid, CoordinatorDecision.COMMIT, [p.id for p in participants])
        log.mark_executed(tid)

        for p in participants:
            p.prepare()
            p.commit()

        coord = Coordinator(
            transaction_id=tid, decision_log=log, prepare_timeout_seconds=10.0
        )
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        for p in participants:
            assert p.state == ParticipantState.COMMITTED

    def test_recovery_partial_prepared_participants(self):
        participants = make_participants(3, all_vote_yes=True)
        log = DecisionLog()
        tid = "tx-partial-recovery"

        log.record_decision(tid, CoordinatorDecision.COMMIT, [p.id for p in participants])

        participants[0].prepare()
        participants[0].commit()
        participants[1].prepare()

        coord = Coordinator(
            transaction_id=tid, decision_log=log, prepare_timeout_seconds=10.0
        )
        coord.register_participants(participants)

        result = coord.execute()

        assert result.decision == CoordinatorDecision.COMMIT
        assert participants[0].state == ParticipantState.COMMITTED
        assert participants[1].state == ParticipantState.COMMITTED
        assert participants[2].state == ParticipantState.INITIAL


class TestDecisionLog:
    def test_record_and_get_entry(self):
        log = DecisionLog()
        entry = log.record_decision("tx-1", CoordinatorDecision.COMMIT, ["p1", "p2"])

        assert entry.transaction_id == "tx-1"
        assert entry.decision == CoordinatorDecision.COMMIT
        assert entry.participant_ids == ["p1", "p2"]
        assert entry.executed is False
        assert log.has_entry("tx-1") is True

    def test_mark_executed(self):
        log = DecisionLog()
        log.record_decision("tx-1", CoordinatorDecision.COMMIT, ["p1"])
        log.mark_executed("tx-1")
        assert log.get_entry("tx-1").executed is True

    def test_get_nonexistent_returns_none(self):
        log = DecisionLog()
        assert log.get_entry("nonexistent") is None
        assert log.has_entry("nonexistent") is False

    def test_get_pending_entries(self):
        log = DecisionLog()
        log.record_decision("tx-1", CoordinatorDecision.COMMIT, ["p1"])
        log.record_decision("tx-2", CoordinatorDecision.ABORT, ["p2"])
        log.mark_executed("tx-1")

        pending = log.get_pending_entries()
        assert len(pending) == 1
        assert pending[0].transaction_id == "tx-2"

    def test_clear_and_count(self):
        log = DecisionLog()
        log.record_decision("tx-1", CoordinatorDecision.COMMIT, ["p1"])
        log.record_decision("tx-2", CoordinatorDecision.COMMIT, ["p2"])
        assert log.count() == 2
        log.clear()
        assert log.count() == 0


class TestCoordinatorEdgeCases:
    def test_cannot_execute_twice(self):
        p = make_participant(vote_yes=True)
        coord = make_coordinator()
        coord.register_participant(p)
        coord.execute()

        with pytest.raises(TransactionAlreadyExecutedError):
            coord.execute()

    def test_cannot_register_after_execution(self):
        p = make_participant(vote_yes=True)
        coord = make_coordinator()
        coord.register_participant(p)
        coord.execute()

        p2 = make_participant()
        with pytest.raises(TransactionAlreadyExecutedError):
            coord.register_participant(p2)

    def test_participant_callbacks_fire_with_consistent_timing(self):
        events = []

        def on_prepare(p):
            events.append(("prepare", p.id, p.state.value))

        def on_commit(p):
            events.append(("commit", p.id, p.state.value))

        def on_abort(p):
            events.append(("abort", p.id, p.state.value))

        p1 = Participant(id="p-cb-1", on_prepare=on_prepare, on_commit=on_commit, on_abort=on_abort)
        p2 = Participant(id="p-cb-2", on_prepare=on_prepare, on_commit=on_commit, on_abort=on_abort)
        p2.configure_vote(False)

        coord = make_coordinator()
        coord.register_participants([p1, p2])
        coord.execute()

        prepare_events = [e for e in events if e[0] == "prepare"]
        assert ("prepare", "p-cb-1", "PREPARED") in prepare_events
        assert ("prepare", "p-cb-2", "ABORTED") in prepare_events
        assert ("abort", "p-cb-1", "ABORTED") in events
        assert ("commit", "p-cb-1", "COMMITTED") not in events
