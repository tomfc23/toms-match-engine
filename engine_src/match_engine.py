import json
import random
from pathlib import Path
import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SIM_DATA_DIR = Path(__file__).parent / 'sim_data'

class MatchEngine:
    def __init__(self, lineups = None):
        # initialize variables
        self.possession_ticks = {
            'home': 0,
            'away': 0
        }
        self.score = {
            'home': 0,
            'away': 0
        }
        self.in_possession = 'home' if random.random() < 0.5 else 'away'
        self.out_possession = 'away' if self.in_possession == 'home' else 'home'
        self.minute = 1
        self.current_zone = 'midfield' # home_box, home_defense, midfield, away_defense, away_box
        self.load_data()
        self.load_lineups(lineups)
    
    def load_data(self):
        with open(DATA_DIR / 'nation_rankings.json', 'r') as f:
            self.nation_rankings = json.load(f)
        
        try:
            with open(SIM_DATA_DIR / 'duel_tracker.json', 'r') as f:
                self.duel_tracker = json.load(f)
        except:
            self.duel_tracker = {
                'midfield': {},
                'home_box': {},
                'home_defense': {},
                'away_defense': {},
                'away_box': {}
            }

        try:
            with open(SIM_DATA_DIR / 'goal_tracker.json', 'r') as f:
                self.goal_tracker = json.load(f)
        except:
            self.goal_tracker = {
                'home': {},
                'away': {},
            }

        try:
            with open(SIM_DATA_DIR / 'team_duel_tracker.json', 'r') as f:
                self.team_duel_tracker = json.load(f)
        except:
            self.team_duel_tracker = {
                zone: {'home': {'wins': 0, 'total': 0}, 'away': {'wins': 0, 'total': 0}}
                for zone in ['midfield', 'home_defense', 'away_defense']
            }

    def load_lineups(self, lineup_data = None):
        if lineup_data is None:
            with open('lineups.json', 'r') as f:
                lineup_data = json.load(f)

        self.lineups = {}

        for team in lineup_data:
            team_data = lineup_data[team]
            lineup = {}
            for player_id in team_data:
                player_data = team_data[player_id]

                position = player_data['position']
                attributes = player_data['ofm']

                nation_id = player_data['nation_id']

                if position in lineup.keys():
                    lineup[position].append({
                        'player_id': int(player_id),
                        'attributes': attributes,
                        'nation_id': nation_id
                    })
                else:
                    lineup[position] = [{
                        'player_id': int(player_id),
                        'attributes': attributes,
                        'nation_id': nation_id
                    }]
            
            self.lineups[team] = lineup

    def nation_multiplier(self, team_id):
        team_id = str(team_id)
        
        if team_id not in self.nation_rankings:
            return 1.0
        
        rank = self.nation_rankings[team_id]['position']
        total = len(self.nation_rankings)

        multiplier = 1.0 + 0.15 * (1 - math.log(rank) / math.log(total))
        return multiplier

    def pick_random_player(self, position, team):
        possible_players = self.lineups[team][position]
        return random.choice(possible_players)  

    def flip_possession(self):
        if self.in_possession == 'home':
            self.in_possession = 'away'
            self.out_possession = 'home'
        else:
            self.in_possession = 'home'
            self.out_possession = 'away'

        self.current_zone = 'midfield'

    def record_team_duel(self, zone, winning_team):
        if zone not in self.team_duel_tracker:
            return
        for team in ['home', 'away']:
            self.team_duel_tracker[zone][team]['total'] += 1
        self.team_duel_tracker[zone][winning_team]['wins'] += 1

    def roll_duel(self):
        if self.current_zone == 'midfield':
            att_player = self.pick_random_player('M', self.in_possession)
            def_player = self.pick_random_player('M', self.out_possession)

            attacking_attribute_names = ['dribbling', 'passing', 'vision', 'teamwork']
            defending_attribute_names = ['tackling', 'positioning', 'decisions', 'aggression', 'defending']
            
            att_attributes = [att_player['attributes'][att] for att in attacking_attribute_names]
            def_attributes = [def_player['attributes'][att] for att in defending_attribute_names]

            att_mult = self.nation_multiplier(att_player['nation_id'])
            def_mult = self.nation_multiplier(def_player['nation_id'])

            att_rating = sum(att_attributes) / len(att_attributes) * att_mult
            def_rating = sum(def_attributes) / len(def_attributes) * def_mult

            success_chance = att_rating / (att_rating + def_rating)

            if random.random() < success_chance:
                winning_player = att_player
                winning_id = str(winning_player.get('player_id'))
                if winning_id in self.duel_tracker[self.current_zone]:
                    self.duel_tracker[self.current_zone][winning_id] += 1
                else:
                    self.duel_tracker[self.current_zone][winning_id] = 1

                winning_team = self.in_possession

                if self.in_possession == 'home':
                    self.current_zone = 'away_defense'
                else:
                    self.current_zone = 'home_defense'

            else:
                winning_player = def_player
                winning_id = str(winning_player.get('player_id'))
                if winning_id in self.duel_tracker[self.current_zone]:
                    self.duel_tracker[self.current_zone][winning_id] += 1
                else:
                    self.duel_tracker[self.current_zone][winning_id] = 1

                winning_team = self.out_possession

                self.flip_possession()
            
            self.record_team_duel('midfield', winning_team)

        elif 'defense' in self.current_zone:
            if self.in_possession in self.current_zone:
                # trying to build out

                att_player = self.pick_random_player('D', self.in_possession) # home defender
                def_player = self.pick_random_player('F', self.out_possession) # away attacker

                attacking_attribute_names = ['passing', 'vision', 'composure', 'teamwork']
                defending_attribute_names = ['tackling', 'aggression', 'defending', 'positioning']
                
                att_attributes = [att_player['attributes'][att] for att in attacking_attribute_names]
                def_attributes = [def_player['attributes'][att] for att in defending_attribute_names]

                att_mult = self.nation_multiplier(att_player['nation_id'])
                def_mult = self.nation_multiplier(def_player['nation_id'])

                att_rating = sum(att_attributes) / len(att_attributes) * att_mult
                def_rating = sum(def_attributes) / len(def_attributes) * def_mult

                success_chance = att_rating / (att_rating + def_rating)

                if random.random() < success_chance:
                    winning_player = att_player
                    winning_id = str(winning_player.get('player_id'))
                    if winning_id in self.duel_tracker[self.current_zone]:
                        self.duel_tracker[self.current_zone][winning_id] += 1
                    else:
                        self.duel_tracker[self.current_zone][winning_id] = 1

                    self.record_team_duel(self.current_zone, self.in_possession)

                    self.current_zone = 'midfield'                        
                else:
                    winning_player = def_player
                    winning_id = str(winning_player.get('player_id'))
                    if winning_id in self.duel_tracker[self.current_zone]:
                        self.duel_tracker[self.current_zone][winning_id] += 1
                    else:
                        self.duel_tracker[self.current_zone][winning_id] = 1

                    self.record_team_duel(self.current_zone, self.out_possession)

                    self.flip_possession()
            
            else:
                # attacking towards the box 

                att_player = self.pick_random_player('F', self.in_possession)
                def_player = self.pick_random_player('D', self.out_possession)

                attacking_attribute_names = ['dribbling', 'teamwork', 'composure', 'decisions']
                defending_attribute_names = ['tackling', 'defending', 'positioning', 'aerial']

                att_attributes = [att_player['attributes'][att] for att in attacking_attribute_names]
                def_attributes = [def_player['attributes'][att] for att in defending_attribute_names]

                att_mult = self.nation_multiplier(att_player['nation_id'])
                def_mult = self.nation_multiplier(def_player['nation_id'])

                att_rating = sum(att_attributes) / len(att_attributes) * att_mult
                def_rating = sum(def_attributes) / len(def_attributes) * def_mult

                success_chance = att_rating / (att_rating + def_rating)

                if random.random() < success_chance:
                    winning_player = att_player
                    winning_id = str(winning_player.get('player_id'))
                    if winning_id in self.duel_tracker[self.current_zone]:
                        self.duel_tracker[self.current_zone][winning_id] += 1
                    else:
                        self.duel_tracker[self.current_zone][winning_id] = 1

                    self.record_team_duel(self.current_zone, self.in_possession)

                    self.current_zone = 'home_box' if self.in_possession == 'away' else 'away_box'                        
                else:
                    winning_player = def_player
                    winning_id = str(winning_player.get('player_id'))
                    if winning_id in self.duel_tracker[self.current_zone]:
                        self.duel_tracker[self.current_zone][winning_id] += 1
                    else:
                        self.duel_tracker[self.current_zone][winning_id] = 1

                    self.record_team_duel(self.current_zone, self.out_possession)

                    self.flip_possession()
        
        elif 'box' in self.current_zone:
            att_pos = random.choices(['F','M'], weights=[.75,.25], k=1)[0]

            att_player = self.pick_random_player(att_pos, self.in_possession)
            def_player = self.pick_random_player('G', self.out_possession)
        
            attacking_attribute_names = ['shooting', 'decisions']
            defending_attribute_names = ['handling', 'gk_positioning']

            att_attributes = [att_player['attributes'][att] for att in attacking_attribute_names]
            def_attributes = [def_player['attributes'][att] for att in defending_attribute_names]

            att_mult = self.nation_multiplier(att_player['nation_id'])
            def_mult = self.nation_multiplier(def_player['nation_id'])

            att_rating = sum(att_attributes) / len(att_attributes) * att_mult
            def_rating = sum(def_attributes) / len(def_attributes) * def_mult

            accuracy = max(0.15, min(0.85, 0.45 + (att_rating - 65) / 200))
            conversion = max(0.10, min(0.70, 0.30 + (att_rating - def_rating) / 150))

            if random.random() < accuracy:
                # shot on target
                att_id = str(att_player.get('player_id'))

                if att_id in self.goal_tracker[self.in_possession]:
                        self.goal_tracker[self.in_possession][att_id]['sog'] += 1
                else:
                    self.goal_tracker[self.in_possession][att_id] = {
                        'sog': 1,
                        'goals': 0
                    }
                if random.random() < conversion:
                    # goal
                    self.score[self.in_possession] += 1

                    if att_id in self.goal_tracker[self.in_possession]:
                        self.goal_tracker[self.in_possession][att_id]['goals'] += 1
                    else:
                        self.goal_tracker[self.in_possession][att_id]['goals'] = 1
                
            self.flip_possession()

    def midfield_contest(self):
        mid_ratings = {}

        attributes = ['passing', 'vision', 'teamwork', 'decisions']
        for team in self.lineups:
            team_total = 0
            midfielders = self.lineups[team]['M']
            for midfielder in midfielders:
                player_avg = sum(midfielder['attributes'][attr] for attr in attributes) / len(attributes)

                team_total += player_avg

            mid_ratings[team] = team_total / len(midfielders)

        home_rating = mid_ratings['home']
        away_rating = mid_ratings['away']

        if self.in_possession == 'home':
            lose_chance = away_rating / (home_rating + away_rating)
        else:
            lose_chance = home_rating / (home_rating + away_rating)

        if random.random() < lose_chance:
            self.flip_possession()

    def write_sim_data(self):
        with open(SIM_DATA_DIR / 'duel_tracker.json', 'w') as f:
            json.dump(self.duel_tracker, f, indent=2)

        with open(SIM_DATA_DIR / 'goal_tracker.json', 'w') as f:
            json.dump(self.goal_tracker, f, indent=2)

        team_duel_summary = {}
        for zone, teams in self.team_duel_tracker.items():
            team_duel_summary[zone] = {}
            for team, stats in teams.items():
                total = stats['total']
                team_duel_summary[zone][team] = {
                    **stats,
                    'win_pct': round(stats['wins'] / total, 3) if total > 0 else 0.0
                }

        with open(SIM_DATA_DIR / 'team_duel_tracker.json', 'w') as f:
            json.dump(team_duel_summary, f, indent=2)

    def main(self):
        while self.minute <= 90:
            self.possession_ticks[self.in_possession] += 1

            num_actions = random.randint(1,3)

            for _ in range(num_actions):
                """
                Possible events:
                    - Duel 
                    - Shot accuracy
                """
                
                self.roll_duel()

            self.midfield_contest()

            self.minute += 1

        self.write_sim_data()        