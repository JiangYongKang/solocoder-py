from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Optional

from .exceptions import (
    DuplicatePlayerError,
    MatchNotFoundError,
    NoCandidateError,
)
from .models import (
    Match,
    MatchStatus,
    MatchRequest,
    Player,
    Team,
    TeamSize,
)


@dataclass
class MatchmakingConfig:
    relax_step: float = 50.0
    relax_interval: float = 10.0
    max_skill_range: float = 500.0
    confirmation_timeout: float = 30.0


@dataclass
class MatchmakingEngine:
    config: MatchmakingConfig = field(default_factory=MatchmakingConfig)

    _wait_queue: dict[TeamSize, list[MatchRequest]] = field(default_factory=lambda: {
        TeamSize.ONE_V_ONE: [],
        TeamSize.TWO_V_TWO: [],
        TeamSize.THREE_V_THREE: [],
    })
    _forming_teams: dict[TeamSize, list[Team]] = field(default_factory=lambda: {
        TeamSize.ONE_V_ONE: [],
        TeamSize.TWO_V_TWO: [],
        TeamSize.THREE_V_THREE: [],
    })
    _ready_teams: dict[TeamSize, list[Team]] = field(default_factory=lambda: {
        TeamSize.ONE_V_ONE: [],
        TeamSize.TWO_V_TWO: [],
        TeamSize.THREE_V_THREE: [],
    })
    _active_matches: dict[str, Match] = field(default_factory=dict)
    _backup_queue: list[MatchRequest] = field(default_factory=list)
    _player_index: set[str] = field(default_factory=set)

    def enqueue(
        self,
        player: Player,
        team_size: TeamSize,
        initial_skill_range: float,
        enqueue_time: Optional[float] = None,
    ) -> MatchRequest:
        if player.player_id in self._player_index:
            raise DuplicatePlayerError(
                f"Player {player.player_id} is already in the matchmaking system"
            )

        req_time = enqueue_time if enqueue_time is not None else time()
        request = MatchRequest(
            player=player,
            team_size=team_size,
            initial_skill_range=initial_skill_range,
            enqueue_time=req_time,
        )

        self._wait_queue[team_size].append(request)
        self._player_index.add(player.player_id)
        return request

    def cancel_request(self, player_id: str) -> None:
        if player_id not in self._player_index:
            raise MatchNotFoundError(
                f"No active matchmaking request found for player {player_id}"
            )

        for ts in TeamSize:
            self._wait_queue[ts] = [
                r for r in self._wait_queue[ts] if r.player.player_id != player_id
            ]

        for ts in TeamSize:
            for team in self._forming_teams[ts]:
                to_remove = [
                    p for p in team.members if p.player_id == player_id
                ]
                for p in to_remove:
                    team.remove_player(p)
            self._forming_teams[ts] = [
                t for t in self._forming_teams[ts] if t.members
            ]

        for ts in TeamSize:
            self._ready_teams[ts] = [
                t for t in self._ready_teams[ts]
                if not any(p.player_id == player_id for p in t.members)
            ]

        self._backup_queue = [
            r for r in self._backup_queue if r.player.player_id != player_id
        ]

        self._player_index.discard(player_id)

    def _current_window(self, request: MatchRequest, now: float) -> tuple[float, float]:
        return request.current_skill_window(
            self.config.relax_step,
            self.config.relax_interval,
            self.config.max_skill_range,
            now,
        )

    def _in_window(
        self,
        skill: float,
        window: tuple[float, float],
    ) -> bool:
        return window[0] <= skill <= window[1]

    def _form_teams(self, now: float) -> None:
        for ts in TeamSize:
            if ts == TeamSize.ONE_V_ONE:
                for r in self._wait_queue[ts]:
                    t = Team(team_size=ts)
                    t.add_player(r.player, r)
                    self._ready_teams[ts].append(t)
                self._wait_queue[ts].clear()
                continue

            queue = self._wait_queue[ts]
            still_waiting: list[MatchRequest] = []

            for req in queue:
                placed = False

                for team in self._forming_teams[ts]:
                    if not team.is_complete:
                        window = self._current_window(req, now)
                        if self._in_window(team.avg_skill, window):
                            team.add_player(req.player, req)
                            placed = True
                            break

                if not placed:
                    for other_req in still_waiting:
                        other_window = self._current_window(other_req, now)
                        req_window = self._current_window(req, now)
                        if (
                            self._in_window(req.player.skill_rating, other_window)
                            and self._in_window(other_req.player.skill_rating, req_window)
                        ):
                            new_team = Team(team_size=ts)
                            new_team.add_player(other_req.player, other_req)
                            new_team.add_player(req.player, req)
                            if new_team.is_complete:
                                self._ready_teams[ts].append(new_team)
                            else:
                                self._forming_teams[ts].append(new_team)
                            still_waiting.remove(other_req)
                            placed = True
                            break

                if not placed:
                    new_team = Team(team_size=ts)
                    new_team.add_player(req.player, req)
                    self._forming_teams[ts].append(new_team)

            self._wait_queue[ts] = still_waiting

            complete_from_forming = [
                t for t in self._forming_teams[ts] if t.is_complete
            ]
            self._ready_teams[ts].extend(complete_from_forming)
            self._forming_teams[ts] = [
                t for t in self._forming_teams[ts] if not t.is_complete
            ]

    def _match_ready_teams(self, now: float) -> list[Match]:
        matches: list[Match] = []

        for ts in TeamSize:
            ready = self._ready_teams[ts]
            unmatched: list[Team] = []

            while ready:
                team_a = ready.pop(0)
                paired = False

                window_a = team_a.effective_skill_window(
                    self.config.relax_step,
                    self.config.relax_interval,
                    self.config.max_skill_range,
                    now,
                )

                for i, team_b in enumerate(ready):
                    window_b = team_b.effective_skill_window(
                        self.config.relax_step,
                        self.config.relax_interval,
                        self.config.max_skill_range,
                        now,
                    )
                    if self._in_window(
                        team_b.avg_skill, window_a
                    ) and self._in_window(team_a.avg_skill, window_b):
                        ready.pop(i)
                        match = Match(
                            team_size=ts,
                            team_a=team_a,
                            team_b=team_b,
                            status=MatchStatus.MATCHED,
                            created_at=now,
                            original_skill_range=(
                                min(window_a[0], window_b[0]),
                                max(window_a[1], window_b[1]),
                            ),
                        )
                        self._active_matches[match.match_id] = match
                        for p in team_a.members + team_b.members:
                            self._player_index.discard(p.player_id)
                        matches.append(match)
                        paired = True
                        break

                if not paired:
                    unmatched.append(team_a)

            self._ready_teams[ts] = unmatched

        return matches

    def _check_confirmation_timeouts(self, now: float) -> list[Match]:
        timed_out_match_ids: list[str] = []

        for match_id, match in list(self._active_matches.items()):
            if match.status != MatchStatus.MATCHED:
                continue
            if now - match.created_at > self.config.confirmation_timeout:
                timed_out_match_ids.append(match_id)

        resolved: list[Match] = []
        for match_id in timed_out_match_ids:
            if match_id not in self._active_matches:
                continue
            match = self._active_matches[match_id]
            timed_out_player_id = match.team_a.members[0].player_id
            try:
                updated = self.handle_player_cancellation(match_id, timed_out_player_id)
                updated.confirm()
                resolved.append(updated)
            except NoCandidateError:
                pass

        return resolved

    def tick(self, now: Optional[float] = None) -> list[Match]:
        current_time = now if now is not None else time()
        self._form_teams(current_time)
        new_matches = self._match_ready_teams(current_time)
        timeout_resolved = self._check_confirmation_timeouts(current_time)
        return new_matches + timeout_resolved

    def add_to_backup(self, request: MatchRequest) -> None:
        if request.player.player_id in self._player_index:
            raise DuplicatePlayerError(
                f"Player {request.player.player_id} is already in the system"
            )
        self._backup_queue.append(request)
        self._player_index.add(request.player.player_id)

    def _find_backup_candidate(
        self,
        team_size: TeamSize,
        skill_window: tuple[float, float],
    ) -> Optional[MatchRequest]:
        for i, req in enumerate(self._backup_queue):
            if req.team_size != team_size:
                continue
            if self._in_window(req.player.skill_rating, skill_window):
                return self._backup_queue.pop(i)
        return None

    def handle_player_cancellation(
        self,
        match_id: str,
        cancelled_player_id: str,
    ) -> Match:
        if match_id not in self._active_matches:
            raise MatchNotFoundError(f"Match {match_id} not found")

        match = self._active_matches[match_id]
        all_players = match.all_players

        if cancelled_player_id not in {p.player_id for p in all_players}:
            raise MatchNotFoundError(
                f"Player {cancelled_player_id} not in match {match_id}"
            )

        for p in all_players:
            if p.player_id != cancelled_player_id:
                self._player_index.add(p.player_id)

        cancelled_team = (
            match.team_a
            if any(p.player_id == cancelled_player_id for p in match.team_a.members)
            else match.team_b
        )
        remaining_team = match.team_b if cancelled_team is match.team_a else match.team_a

        backup_req = self._find_backup_candidate(
            match.team_size, match.original_skill_range
        )

        if backup_req is None:
            for p in remaining_team.members:
                self._player_index.discard(p.player_id)
                requeue_req = MatchRequest(
                    player=p,
                    team_size=match.team_size,
                    initial_skill_range=self.config.max_skill_range * 0.5,
                    enqueue_time=time(),
                )
                self._wait_queue[match.team_size].append(requeue_req)
                self._player_index.add(p.player_id)
            match.fail()
            del self._active_matches[match_id]
            raise NoCandidateError(
                f"No backup candidate available for match {match_id}"
            )

        self._player_index.discard(backup_req.player.player_id)

        if match.team_size == TeamSize.ONE_V_ONE:
            new_cancelled_team = Team(team_size=match.team_size)
            new_cancelled_team.add_player(backup_req.player, backup_req)
        else:
            new_cancelled_team = Team(team_size=match.team_size)
            remaining_requests = [
                r for r in cancelled_team.requests
                if r.player.player_id != cancelled_player_id
            ]
            for r in remaining_requests:
                new_cancelled_team.add_player(r.player, r)
            new_cancelled_team.add_player(backup_req.player, backup_req)

        if new_cancelled_team.is_complete:
            match.team_a = remaining_team
            match.team_b = new_cancelled_team
            match.status = MatchStatus.MATCHED
        else:
            for p in remaining_team.members + new_cancelled_team.members:
                self._player_index.discard(p.player_id)
                requeue_req = MatchRequest(
                    player=p,
                    team_size=match.team_size,
                    initial_skill_range=self.config.max_skill_range * 0.5,
                    enqueue_time=time(),
                )
                self._wait_queue[match.team_size].append(requeue_req)
                self._player_index.add(p.player_id)
            match.fail()
            del self._active_matches[match_id]
            raise NoCandidateError(
                f"Backup candidate insufficient to form complete team"
            )

        return match

    def get_active_match(self, match_id: str) -> Match:
        if match_id not in self._active_matches:
            raise MatchNotFoundError(f"Match {match_id} not found")
        return self._active_matches[match_id]

    @property
    def total_waiting(self) -> int:
        count = sum(len(q) for q in self._wait_queue.values())
        for ts in TeamSize:
            for t in self._forming_teams[ts]:
                count += len(t.members)
            count += len(self._ready_teams[ts]) * ts.value
        count += len(self._backup_queue)
        return count
