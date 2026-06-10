import lineup_generator
import match_engine
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SIM_DATA_DIR = Path(__file__).parent / 'sim_data'

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

    with open(SIM_DATA_DIR / 'team_duel_tracker.json', 'w') as f:
        team_duel_tracker = {
            zone: {'home': {'wins': 0, 'total': 0}, 'away': {'wins': 0, 'total': 0}}
            for zone in ['midfield', 'home_defense', 'away_defense']
        }

# spain - 4698
# england - 4713
# usa - 4724
# ecuador - 4757
# mexico - 4781
# south africa - 4736

reset_sim_data()

home = 4781 # 
away = 4736 #

lg = lineup_generator.LineupGen()

results = {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'home_goals': 0, 'away_goals': 0}

scores = []

num_sims = 10_000
num_lineups = 1000

per_lineup_sim = num_sims // num_lineups

for _ in range(num_sims):
    lineups = lg.gen_game(home, away)
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

with open('scores.txt', 'w') as f:
    for score in scores:
        f.write(f'{score['home']} - {score['away']}\n')

with open(DATA_DIR / 'team_data.json', 'r') as f:
    team_data = json.load(f)

home_name = team_data[str(home)].get('name')
away_name = team_data[str(away)].get('name')

print(f"{home_name} wins: {results['home_wins']/num_sims * 100:.1f}%")
print(f"Draws: {results['draws']/num_sims * 100:.1f}%")
print(f"{away_name} wins: {results['away_wins']/num_sims * 100:.1f}%")
print(f"Avg goals: {results['home_goals']/num_sims:.2f} - {results['away_goals']/num_sims:.2f}")