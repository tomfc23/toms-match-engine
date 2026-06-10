from pathlib import Path
import json
import random
import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SIM_DATA_DIR = Path(__file__).parent / 'sim_data'

class LineupGen:
    def __init__(self):
        self.formation = {
            'G': 1,
            'D': 4,
            'M': 3,
            'F': 3
        }

        self.position_attrs = {
            'G': ['handling', 'gk_positioning'],
            'D': ['tackling', 'defending', 'positioning', 'aerial'],
            'M': ['passing', 'vision', 'decisions', 'teamwork', 'composure', 'defending'],
            'F': ['shooting', 'dribbling', 'composure', 'decisions']
        }

        self.missing_player_count = 0

        self.load_data()
        
        #self.get_all_lineups()

        #print(f"Total Missing Players: {self.missing_player_count}")


    def __str__(self):
        rand_team_id = random.choice(list(self.lineups.keys()))
        team_name = self.team_data[rand_team_id]['name']
        lineup = self.lineups[rand_team_id]

        data_str = f'{team_name}\n'

        for pos_group in lineup:
            for player in pos_group:
                player_name = self.player_bios[str(player)]['name']
                data_str += f'{player_name}\t'

            data_str += '\n'

        return data_str

    def load_data(self):
        with open(DATA_DIR / 'players.json', 'r') as f:
            self.squad_data = json.load(f)
        
        with open(DATA_DIR / 'player_db.json', 'r') as f:
            self.player_db = json.load(f)

        with open(DATA_DIR / 'team_data.json', 'r') as f:
            self.team_data = json.load(f)

        with open(DATA_DIR / 'player_bios.json', 'r', encoding="utf-8") as f:
            self.player_bios = json.load(f)

        with open(DATA_DIR / 'league_rankings.json', 'r') as f:
            self.league_rankings = json.load(f)

    def league_multiplier(self, player_id):
        player_id = str(player_id)
        league_id = str(self.player_bios[player_id].get('league_id'))
        
        if league_id not in self.league_rankings:
            return 1.0
        
        rank = self.league_rankings[league_id]['position']
        
        multiplier = 1.0 + 0.20 * (1 - math.log(rank) / math.log(len(self.league_rankings)))
        return multiplier

    def get_all_lineups(self):
        self.lineups = {}
        for team_id in self.squad_data:
            self.lineups[team_id] = self.get_single_lineup(team_id)
    
    def get_single_lineup(self, team_id):
        team_id = str(team_id)
        team_player_ids = self.squad_data[team_id]
        weights_data = {}
        position_data = {}
        for player_id in team_player_ids:
            try:
                player_data = self.player_db[str(player_id)]
            except KeyError:
                #print(f"Couldn't find {player_id}")
                self.missing_player_count += 1
                continue
        
            position = player_data['position']
            attributes = player_data['ofm']
            pos_attrs = self.position_attrs[position]

            weight = sum([attributes.get(attr, 0) ** 2 for attr in pos_attrs]) 

            if position in weights_data.keys():
                weights_data[position].append(weight)
                position_data[position].append(player_id)
            else:
                weights_data[position] = [weight]
                position_data[position] = [player_id]


        team_lineup = []

        for position in position_data:                
            players = position_data[position]
            weights = weights_data[position]

            STARTER_THRESHOLD = 0.75  # top 75th percentile of team weights

            max_weight = max(weights)
            for i, w in enumerate(weights):
                if w / max_weight >= STARTER_THRESHOLD:
                    weights[i] = w * 3  # heavily boost near-certain starters

            available_players = players.copy()
            available_weights = weights.copy()
            selected = []

            count = min(self.formation[position], len(players))

            selected = []

            available_players = players.copy()
            available_weights = weights.copy()

            for _ in range(count):
                if not available_players:
                    break

                chosen = random.choices(
                    available_players,
                    weights=available_weights,
                    k=1
                )[0]

                selected.append(chosen)

                idx = available_players.index(chosen)
                available_players.pop(idx)
                available_weights.pop(idx)
                

            team_lineup.append(selected)
        
        return team_lineup

    def print_lineup(self, team_id=None):
        if not team_id:
            print(self)
        else:
            team_id = str(team_id)
            team_name = self.team_data[team_id]['name']
            lineup = self.lineups[team_id]

            data_str = f'{team_name}\n'

            for pos_group in lineup:
                for player in pos_group:
                    player_name = self.player_bios[str(player)]['name']
                    data_str += f'{player_name}\t'

                data_str += '\n'

            print(data_str)

    def load_sim_data(self):
        with open(SIM_DATA_DIR / 'lineup_tracker.json', 'r') as f:
            self.lineup_tracker = json.load(f)

    def write_sim_data(self):
        with open(SIM_DATA_DIR / 'lineup_tracker.json', 'w') as f:
            json.dump(self.lineup_tracker, f, indent=2)

    def gen_game(self, home_id, away_id, home_lineup=None, away_lineup=None):
        self.load_sim_data()

        if home_lineup == None:
            home_lineup = self.get_single_lineup(home_id)
        if away_lineup == None:
            away_lineup = self.get_single_lineup(away_id)

        lineup_data = {
            'home': {},
            'away': {}
        }
        
        positions = ['F','M',"D","G"]

        for pos, pos_group in zip(positions,home_lineup):
            for player_id in pos_group:
                player_id = str(player_id)
                lineup_data['home'][player_id] = self.player_db[player_id]
                lineup_data['home'][player_id]['position'] = pos

                if player_id in self.lineup_tracker['home']:
                    self.lineup_tracker['home'][player_id] += 1
                else:
                    self.lineup_tracker['home'][player_id] = 1
        
        for pos,pos_group in zip(positions, away_lineup):
            for player_id in pos_group:
                player_id = str(player_id)
                lineup_data['away'][player_id] = self.player_db[player_id]
                lineup_data['away'][player_id]['position'] = pos

                if player_id in self.lineup_tracker['away']:
                    self.lineup_tracker['away'][player_id] += 1
                else:
                    self.lineup_tracker['away'][player_id] = 1

        self.write_sim_data()

        return lineup_data

#england = 4713
"""
if __name__ == '__main__':
    num_lineups = 1000
    frequencies = {}
    team_id = 4713
    team_id = str(team_id)

    for _ in range(num_lineups):
        lg = LineupGen()
        lineup = lg.lineups[team_id]
        for pos_group in lineup:
            for player in pos_group:
                player_name = lg.player_bios[str(player)]['name']

                if player_name in frequencies:
                    frequencies[player_name] += 1
                else:
                    frequencies[player_name] = 1

    for player in frequencies:
        print(f"{player} - {round((frequencies[player] / num_lineups) * 100,2)}%")
"""