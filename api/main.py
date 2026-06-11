import json
from pathlib import Path
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ENGINE_DIR = PROJECT_ROOT / "engine_src"
SIM_DATA_DIR = ENGINE_DIR / "sim_data"

sys.path.append(str(ENGINE_DIR))

import lineup_generator
import match_engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "null"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def reset_sim_data():
    with open(SIM_DATA_DIR / 'duel_tracker.json', 'w') as f:
        duel_tracker = {
            'midfield': {},
            'home_defense': {},
            'away_defense': {},
        }
        json.dump(duel_tracker, f, indent=2)

    with open(SIM_DATA_DIR / 'goal_tracker.json', 'w') as f:
        goal_tracker = {
            'home': {},
            'away': {},
        }

        json.dump(goal_tracker, f, indent=2)

    with open(SIM_DATA_DIR / 'lineup_tracker.json', 'w') as f:
        lineup_tracker = {
            'home': {},
            'away': {}
        }

        json.dump(lineup_tracker, f, indent=2)

# spain - 4698
# england - 4713
# usa - 4724
# ecuador - 4757
# mexico - 4781
# south africa - 4736

@app.get('/init')
def init():
    reset_sim_data()

    return {'success': True}

@app.post('/sim')
def simulate(payload: dict):
    reset_sim_data()

    try:
        home = int(payload.get('home_id')) 
        away = int(payload.get('away_id'))
        num_sims = int(payload.get('num_sims'))
        num_lineups = int(payload.get('num_lineups'))
    except TypeError:
        raise HTTPException(status_code=400, detail="Missing one or more fields in payload")

    custom_lineup = payload.get('custom_lineup', False)

    home_lineup = payload.get('home_lineup', [])
    away_lineup = payload.get('away_lineup', [])


    if custom_lineup:
        invalid_home_players = check_lineup(home_lineup)
        invalid_away_players = check_lineup(away_lineup)
    else:
        invalid_away_players = []
        invalid_home_players = []

    if len(invalid_home_players) > 0 or len(invalid_away_players) > 0:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "One or more players were not found",
                "invalid_home": invalid_home_players,
                "invalid_away": invalid_away_players,
            },
        )

    if home is None or away is None:
        raise HTTPException(status_code=400, detail="Invalid team ID(s)")
    
    if num_sims is None:
        raise HTTPException(status_code=400, detail="Invalid number of simulations")
    
    if num_lineups is None:
        raise HTTPException(status_code=400, detail="Invalid number of lineups")

    lg = lineup_generator.LineupGen()

    results = {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'home_goals': 0, 'away_goals': 0}

    scores = []

    per_lineup_sim = num_sims // num_lineups
    
    for _ in range(num_lineups):
        if not custom_lineup or home_lineup == [] or away_lineup == []:
            lineups = lg.gen_game(home, away)
        else:
            lineups = lg.gen_game(home, away, home_lineup=home_lineup, away_lineup=away_lineup)
  
        for _ in range(per_lineup_sim):
            me = match_engine.MatchEngine(lineups=lineups)
            me.main()
            score = me.score
            scores.append(score)
            results['home_goals'] += score['home']
            results['away_goals'] += score['away']
            if score['home'] > score['away']:
                results['home_wins'] += 1
            elif score['home'] == score['away']:
                results['draws'] += 1
            else:
                results['away_wins'] += 1


    results['scores'] = scores

    return results

@app.get("/teams")
def fetch_teams():
    with open(DATA_DIR / 'team_data.json', 'r') as f:
        return json.load(f)

@app.get("/sim_metrics")
def load_metrics():
    metrics = {}

    try:
        with open(SIM_DATA_DIR / 'duel_tracker.json', 'r') as f:
            metrics['duels'] = json.load(f)

        with open(SIM_DATA_DIR / 'goal_tracker.json', 'r') as f:
            metrics['goals'] = json.load(f)

        with open(SIM_DATA_DIR / 'lineup_tracker.json', 'r') as f:
            metrics['lineups'] = json.load(f)

        with open(SIM_DATA_DIR / 'team_duel_tracker.json', 'r') as f:
            metrics['team_duels'] = json.load(f)
    except:
        raise HTTPException(status_code=500, detail="Unable to load metrics")
    
    return metrics

@app.get("/player_bios")
def load_player_bios():
    try:
        with open(DATA_DIR / 'player_bios.json', 'r') as f:
            return json.load(f)
        
    except:
        raise HTTPException(status_code=500, detail="Unable to load player bios")
    
@app.get("/squads")
def load_squads():
    try:
        with open(DATA_DIR / "players.json", 'r') as f:
            return json.load(f)
        
    except:
        raise HTTPException(status_code=500, detail="Unable to load squads")
    
def check_lineup(lineup):
    with open(DATA_DIR / 'player_db.json', 'r') as f:
        player_db = json.load(f)
    
    invalid_players = []
    for pos_group in lineup:
        for player_id in pos_group:
            player_id = str(player_id)
            if player_id not in player_db.keys():
                invalid_players.append(int(player_id))
    
    return invalid_players

@app.get('/group_teams/{group_id}')
def get_group_teams(group_id):
    with open(DATA_DIR / 'group_schedules.json', 'r') as f:
        group_schedules = json.load(f)

    selected_group_schedule = group_schedules[group_id]

    teams = set()

    for game in selected_group_schedule:
        teams.add(game.get('home_id'))
        teams.add(game.get('away_id'))

    return list(teams)

@app.post("/sim_group")
def sim_group(payload: dict):
    average_standings = {}
    average_game_log = {}

    num_sims = payload.get('num_sims')
    group_id = str(payload.get('group_id'))
    custom_lineups = payload.get('custom_lineups', False)
    
    lineups = payload.get('lineups')

    num_sims = int(num_sims)
    for _ in range(num_sims):
        if custom_lineups:
            sim_data = sim_group_single(group_id, lineups=lineups)
        else:
            sim_data = sim_group_single(group_id)

        standings = sim_data['standings']
        game_log = sim_data['game_log']

        for team_id in standings:
            team_data = standings[team_id]
            points = team_data.get('points')
            gd = team_data.get('gd')

            if team_id in average_standings:
                average_standings[team_id]['points'] += points
                average_standings[team_id]['gd'] += gd
            else:
                average_standings[team_id] = {
                    'points': points,
                    'gd': gd
                }

        for game_id in game_log:
            game_data = game_log[game_id]
            home_goals = game_data.get('home_goals')
            away_goals = game_data.get('away_goals')

            if game_id in average_game_log:
                average_game_log[game_id]['home_goals'] += home_goals
                average_game_log[game_id]['away_goals'] += away_goals

            else:
                average_game_log[game_id] = {
                    'home_goals': home_goals,
                    'away_goals': away_goals
                }

    for team_id in average_standings:
        team_data = average_standings[team_id]

        team_data['points'] = round(team_data['points'] / num_sims,2)
        team_data['gd'] = round(team_data['gd'] / num_sims, 2)

    for game_id in average_game_log:
        game_data = average_game_log[game_id]

        game_data['home_goals'] = round(game_data['home_goals'] / num_sims, 2)
        game_data['away_goals'] = round(game_data['away_goals'] / num_sims, 2)

    return {
        'standings': average_standings,
        'game_log': average_game_log
    }

def sim_group_single(group_id: str, lineups=None):
    with open(DATA_DIR / 'group_schedules.json', 'r') as f:
        group_schedules = json.load(f)

    group_id = str(group_id)
    selected_schedule = group_schedules[group_id]

    standings = {}
    game_log = {}
    for event in selected_schedule:
        home_id = event.get('home_id')
        away_id = event.get('away_id')

        event_id = f'{home_id}_{away_id}'

        if lineups is None:
            payload = {
                'home_id': home_id,
                'away_id': away_id,
                'num_sims': 1,
                'num_lineups': 1,
                'custom_lineup': False
            }
        else:
            payload = {
                'home_id': home_id,
                'away_id': away_id,
                'num_sims': 1,
                'num_lineups': 1,
                'custom_lineup': True,
                'home_lineup': lineups[str(home_id)],
                'away_lineup': lineups[str(away_id)]
            }

        results = simulate(payload)

        if results['home_wins'] == 1:
            home_points = 3
            away_points = 0
        elif results['draws'] == 1:
            home_points = 1
            away_points = 1
        elif results['away_wins'] == 1:
            away_points = 3
            home_points = 0

        home_gd = results['home_goals'] - results['away_goals']
        away_gd = results['away_goals'] - results['home_goals']

        if home_id in standings:
            standings[home_id]['points'] += home_points
            standings[home_id]['gd'] += home_gd
        else:
            standings[home_id] = {}
            standings[home_id]['points'] = home_points
            standings[home_id]['gd'] = home_gd

        if away_id in standings:
            standings[away_id]['points'] += away_points
            standings[away_id]['gd'] += away_gd
        else:
            standings[away_id] = {}
            standings[away_id]['points'] = away_points
            standings[away_id]['gd'] = away_gd

        game_log[event_id] = {
            'home_id': home_id,
            'away_id': away_id,
            'home_goals': results['home_goals'],
            'away_goals': results['away_goals']
        }

    return {
        'standings': standings,
        'game_log': game_log
    }

@app.get('/groups')
def load_groups():
    with open(DATA_DIR / 'group_ids.json', 'r') as f:
        return json.load(f)
