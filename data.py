import json
from collections import defaultdict

import requests as requests

from classes import Team

with open('teams.json') as f:
    teams = [Team(id_=i, mlb_id=t['id'], abb=t['abbreviation'])
             for i, t in enumerate(sorted(json.load(f)['teams'], key=lambda x: (x['division']['name'])))]
mlb_id_to_team = {team.mlb_id: team for team in teams}

r = requests.get('http://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&startDate=2021-08-29&endDate=2021-10-03')
data = r.json()
games = [g for d in data['dates'] for g in d['games']]

matchups = defaultdict(int)
for g in games:
    if g['gameType'] == 'R' and g['status']['statusCode'] == 'S':
        pair = frozenset(mlb_id_to_team[x['team']['id']] for x in g['teams'].values())
        matchups[pair] += 1

recorded_wins = {}
for g in games:
    for x in g['teams'].values():
        team = mlb_id_to_team[x['team']['id']]
        recorded_wins[team] = x['leagueRecord']['wins']
