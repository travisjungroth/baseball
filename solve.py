from dataclasses import dataclass, field
from datetime import datetime
from functools import cache, reduce
from itertools import chain
from operator import gt, ge, or_

from z3 import Array, IntSort, Store, ArrayRef, AstRef, And, Or, Not, Int, sat, simplify, AtMost

from classes import Team
from data import matchups, recorded_wins
from sched import matchup_counts_to_solver, matchup_counts_to_possible_wins

s = matchup_counts_to_solver(matchups)
pw = matchup_counts_to_possible_wins(matchups)
total_wins = {team: p + recorded_wins[team] for team, p in pw.items()}
wins = Array('a', IntSort(), IntSort())
for team in Team.teams:
    wins = Store(wins, team.id_, total_wins[team])


def simp(f):
    def inner(*args, **kwargs):
        return simplify(f(*args, **kwargs), local_ctx=True)

    return inner


@dataclass(frozen=True)
class GroupStandings:
    name: str
    wins: ArrayRef = field(compare=False)
    teams: tuple[int] = field(compare=False)

    def __str__(self):
        return self.name

    @cache
    def in_group(self, team) -> AstRef:
        return And(self.teams[0] <= team, team <= self.teams[-1])


@dataclass(frozen=True)
class DivisionStandings(GroupStandings):
    @cache
    def win_division(self, team) -> AstRef:
        return And([Or(team == other_team, self.wins[team] > self.wins[other_team]) for other_team in self.teams])

    @cache
    def win_or_tie_division(self, team) -> AstRef:
        return And([Or(team == other_team, self.wins[team] >= self.wins[other_team]) for other_team in self.teams])

    @cache
    def tie_division(self, team) -> AstRef:
        return And(self.win_or_tie_division(team), Not(self.win_division(team)))


@dataclass(frozen=True)
class LeagueStandings(GroupStandings):
    divisions: tuple[DivisionStandings] = field(compare=False)

    @cache
    def in_group(self, team):
        return And(self.teams[0] <= team, team <= self.teams[-1])

    @cache
    def teams_divisions(self):
        return tuple((other_team, self.divisions[(other_team % 15) // 5]) for other_team in self.teams)

    @simp
    def _place_first_wildcard(self, team, op):
        rules = []
        for division in self.divisions:
            rules.append(Not(division.win_division(team)))
        for other_team, division in self.teams_divisions():
            rules.append(
                Or(other_team == team,
                   division.win_division(other_team),
                   op(self.wins[team], self.wins[other_team]),
                   And(division.in_group(team), division.tie_division(team)),
                   ))
        return And(rules)

    @cache
    def win_first_wildcard(self, team):
        return self._place_first_wildcard(team, gt)

    @cache
    def win_or_tie_first_wildcard(self, team):
        return self._place_first_wildcard(team, ge)

    @cache
    def tie_first_wildcard(self, team):
        return And(self.win_or_tie_first_wildcard(team), Not(self.win_first_wildcard(team)))

    @simp
    def _place_second_wildcard(self, team, op):
        rules = []
        for division in self.divisions:
            rules.append(Not(division.win_division(team)))
            rules.append(Not(self.win_or_tie_first_wildcard(team)))
        rules.append(AtMost(*[self.wins[team] < self.wins[other_team] for other_team in self.teams], 4))
        for other_team, division in self.teams_divisions():
            rules.append(
                Or(other_team == team,
                   division.win_division(other_team),
                   op(self.wins[team], self.wins[other_team]),
                   And(division.in_group(team), division.tie_division(team)),
                   self.win_first_wildcard(other_team))),
        return And(rules)

    @cache
    def win_second_wildcard(self, team):
        return self._place_second_wildcard(team, gt)

    @cache
    def win_or_tie_second_wildcard(self, team):
        return self._place_second_wildcard(team, ge)

    @cache
    def tie_second_wildcard(self, team):
        return And(self.win_or_tie_second_wildcard(team), Not(self.win_second_wildcard(team)))


def f(solver, groups, methods):
    for group in groups:
        for method in methods:
            solver.push()
            teams = set()
            title = f'{group} {method.__name__}'
            team = Int(title)
            solver.add(group.in_group(team))
            solver.add(method(group, team))
            # solver.add(team == 27)
            while solver.check() == sat:
                m = solver.model()
                # for i in range(25, 30):
                #     print(i, m.eval(wins[i]))
                w = m[team].as_long()
                teams.add(w)
                solver.add(team != w)
            yield method.__name__, teams
            solver.pop()


teams = tuple(range(30))
division_names = ('ALC', 'ALE', 'ALW', 'NLE', 'NLE', 'NLW')
divisions = tuple([DivisionStandings(name, wins, teams[5 * i: 5 * i + 5]) for i, name in enumerate(division_names)])
league_names = ['AL', 'NL']

leagues = [LeagueStandings(name, wins, teams[15 * i:15 * i + 15], divisions[i * 3: i * 3 + 3])
           for i, name in enumerate(league_names)]

d = {}
for m, ts in f(s, divisions, [
    DivisionStandings.win_division,
    DivisionStandings.tie_division,
]):
    d.setdefault(m, set()).update(ts)
for m, ts in f(s, leagues, [
    LeagueStandings.win_first_wildcard,
    LeagueStandings.tie_first_wildcard,
    LeagueStandings.win_second_wildcard,
    LeagueStandings.tie_second_wildcard,
]):
    d.setdefault(m, set()).update(ts)

d['make_postseason'] = tuple(reduce(or_, chain(d.values())))

rows = ['<tr><td></td>' + ''.join([f'<td>{Team.teams[n]}</td>' for n in range(30)]) + '</tr>']
for title, vale in d.items():
    row = f'<tr><td>{title}</td>' + ''.join([f'<td>{"O" if n in vale else "X"}</td>' for n in range(30)]) + '</tr>'
    rows.append(row)

table = '<table>' + '\n'.join(rows) + '</table>'
rest = f'<p>Updated {datetime.utcnow()} UTC</p>'
with open('index.html', 'w+') as f:
    f.write(table + rest)
