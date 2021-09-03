from typing import Iterable

import z3 as z

from classes import Team

MatchupCounts = dict[frozenset[Team], int]
RecordedWins = dict[Team, int]
TotalWins = dict[Team, z.ArithRef]


def matchup_counts_to_matchup_wins(matchup_counts: MatchupCounts) -> dict[tuple[Team, Team], z.ArithRef]:
    d = {}
    for (a, b), n in matchup_counts.items():
        for winner, loser in [(a, b), (b, a)]:
            d[(winner, loser)] = z.Int(f'{winner} beats {loser}')
    return d


def matchup_counts_to_constraints(matchup_counts: MatchupCounts) -> Iterable[z.AstRef]:
    d = matchup_counts_to_matchup_wins(matchup_counts)
    non_negative = [0 <= x for x in d.values()]
    total_properly = [d[(a, b)] + d[(b, a)] == n for (a, b), n in matchup_counts.items()]
    return tuple(non_negative + total_properly)


def matchup_counts_to_possible_wins(matchup_counts: MatchupCounts) -> dict[Team, z.ArithRef]:
    by_winner = {}
    for (winner, loser), w in matchup_counts_to_matchup_wins(matchup_counts).items():
        by_winner.setdefault(winner, []).append(w)
    return {team: z.Sum(ws) for team, ws in by_winner.items()}  # team: possible wins


def make_solver(schedule_constraints: Iterable[z.AstRef]) -> z.Solver:
    s = z.Solver()
    s.add(schedule_constraints)
    return s


def matchup_counts_to_solver(matchup_counts: MatchupCounts) -> z.Solver:
    return make_solver(matchup_counts_to_constraints(matchup_counts))
