import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP, UNIT_TYPE_TO_INDEX, INDEX_TO_UNIT_TYPE
        UNIT_TYPE_TO_INDEX = {}
        WALL = config["unitInformation"][0]["shorthand"]
        UNIT_TYPE_TO_INDEX[WALL] = 0
        FACTORY = config["unitInformation"][1]["shorthand"]
        UNIT_TYPE_TO_INDEX[FACTORY] = 1
        TURRET = config["unitInformation"][2]["shorthand"]
        UNIT_TYPE_TO_INDEX[TURRET] = 2
        SCOUT = config["unitInformation"][3]["shorthand"]
        UNIT_TYPE_TO_INDEX[SCOUT] = 3
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        UNIT_TYPE_TO_INDEX[DEMOLISHER] = 4
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        UNIT_TYPE_TO_INDEX[INTERCEPTOR] = 5
        REMOVE = config["unitInformation"][6]["shorthand"]
        UNIT_TYPE_TO_INDEX[REMOVE] = 6
        UPGRADE = config["unitInformation"][7]["shorthand"]
        UNIT_TYPE_TO_INDEX[UPGRADE] = 7
        MP = 1
        SP = 0
        UNITS = [WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR]
        INDEX_TO_UNIT_TYPE = {v:k for k,v in UNIT_TYPE_TO_INDEX.items()}
        




        # AR = Attack Range, AD = Attack Damage
        global TURRET_AR, TURRET_AD, SCOUT_AR, SCOUNT_AD, DEMOLISHER_AR, DEMOLISHER_AD, INTERCEPTOR_AR, INTERCEPTOR_AD
        TURRET_AR = config["unitInformation"][2]["attackRange"]
        TURRET_AD = config["unitInformation"][2]["attackDamageWalker"]
        SCOUT_AR = config["unitInformation"][3]["attackRange"]
        SCOUT_AD = config["unitInformation"][3]["attackDamageWalker"] 
        DEMOLISHER_AR = config["unitInformation"][4]["attackRange"]
        DEMOLISHER_AD = config["unitInformation"][4]["attackDamageWalker"] 
        INTERCEPTOR_AR = config["unitInformation"][5]["attackRange"]
        INTERCEPTOR_AD = config["unitInformation"][5]["attackDamageWalker"] 

        # UP = Upgraded
        # global TURRET_UP_AR, TURRET_UP_ADo
        # TURRET_UP_AR = config["unitInformation"][2]["upgrade"]["attackRange"]
        # TURRET_UP_AD = config["unitInformation"][2]["upgrade"]["attackDamageWalker"]

        # records the latest factory location been placed on arena
        # index 0 for left wing, 1 for right wind
    

        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.defenders_damaged_on_location = {} ## * record what position our denfenders got damaged, key is location and val is unity string type
        self.defenders_dead_on_location = {} ## * record what position our denfenders got destroyed, key is location and val is unity string type
        self.factory_left_wing = [12,3]
        self.factory_right_wing = [14,3]
        self.factory_locations = []
        ## * self.units with 
        ## * key: Unit type
        ## * val: Number of units in our arena
        self.units = {unit: 0 for unit in UNITS}
        self.structure_point = 0 ## * our sp on each turn
        self.mobile_points = 0 ## * our mp on each turn
        self.health = 0 ## * our health each turn
        

        
    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.
        self.starter_strategy(game_state)
        game_state.submit_turn()
        


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    """
    ## todo 
    algo based on Raffel boss 4
    1. 30 structure points : 
        - 2 upgraded factories, cost -> 24
        - 2 turrects, cost -> 4
        - 1 wall in fornt of each turrect, cost -> 2
    
    Advantages: 
    1. to have a row of upgraded walls + upgraded turrects for protection.
    this also help demolishers clear enemy's units/structures at the frontier.

    2. Deploying interceptors at locations [[11,2], [16,2], [6,7], [21,7]] 
    in earlier stage will gain mobile points if units damaged enemy's base. 
    It also potentially destroy enemy's factories by self-destruction

    Placing Structures:
    At each turn, building factories prioritizes bulding turrects and walls. 
    But buliding and upgrading walls + turrects first if our frontier is wrecked.
    
    Place turrects and walls in the middle, if enemy scored on us through a path 
    in the middle.

    
    """        

    def starter_strategy(self, game_state):
    
        # First, setup initial mobiles and units:
        if game_state.turn_number == 0:
            self.init_setup(game_state)

        ## * DEFENSE AND PRODUCTION
        # Walls and Turrects or Factories decisions:
        self.production_or_defense(game_state)
        self.build_reactive_defense(game_state)

        # Now build reactive defenses based on where the enemy scored
        # self.build_reactive_defense(game_state)


        ## * DEPLOY
        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            self.stall_with_interceptors(game_state)
        else:
            # Now let's analyze the enemy base to see where their defenses are concentrated.
            # If they have many units in the front we can build a line for our demolishers to attack them at long range.
            if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
                self.demolisher_line_strategy(game_state)
            else:
                # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

                # Only spawn Scouts every other turn
                # Sending more at once is better since attacks can only hit a single scout at a time
                if game_state.turn_number % 2 == 1:
                    # To simplify we will just check sending them from back left and right
                    scout_spawn_location_options = [[13, 0], [14, 0]]
                    best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
                    game_state.attempt_spawn(SCOUT, best_location, 1000)

                # # Lastly, if we have spare SP, let's build some Factories to generate more resources
                # factory_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                # game_state.attempt_spawn(FACTORY, factory_locations)

    ## * init_setup will set up the units and structures at the begining
    def init_setup(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """


        # Place turrets that attack enemy units
        turret_locations = [[4,12],[23,12],[14,11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        self.units[TURRET] += game_state.attempt_spawn(TURRET, turret_locations)
    
    
        #Place upggraded factories at the deepest location
        self.factory_locations = [[13,2],[14,2],self.factory_left_wing, self.factory_right_wing]
        self.units[FACTORY] += game_state.attempt_spawn(FACTORY, self.factory_locations)

    # calculates the maximum damage a unit will take at location,
    # which is a list with two elements representing x, y coordinates, 
    # returns an integer
    def max_damage(location, game_state):
        x = location[0]
        y = location[1]
        damage = 0

        # Our mobile unit is in enemy‘s half of the arena
        attackers = game_state.get_attackers(location, 0)
        for attacker in attackers:
            damage += attacker.damage_i
        return damage

    ## decides to build factory or defense
    ## * Prioirty:
    ## 1. build defenders if any is destroyed
    ## 2. upgrade defenders if any is damaged
    def production_or_defense(self, game_state):
        # if any denfenders are destoryed, rebuild
        for location in self.defenders_dead_on_location:
            defender = self.defenders_dead_on_location[location]
            self.units[defender] += game_state.attempt_spawn(defender, location)
        
        ## build factory
        threshold = 3
        factory_affordable = game_state.number_affordable(FACTORY)
        gamelib.debug_write("factory affordable:{}".format(game_state.number_affordable(FACTORY)))
        if game_state.number_affordable(FACTORY) > threshold:
            # * alternating factory left and right wing
            # * mod 2 = 0, left wing
            # * mod 2 =1, right wing
            location = None
            for (i in range(fatory_affordable)):
                if len(self.factory_locations) % 2 == 0:
                    x,y = self.factory_left_wing
                    self.factory_left_wing = [x-1,y+1]
                    location = self.factory_left_wing
                else:
                    x,y = self.factory_right_wing
                    self.factory_right_wing = [x+1,y+1]
                    location  = self.factory_right_wing 
                self.factory_locations.append(location)
                if game_state.can_spawn(FACTORY,location):
                    self.units[FACTORY] += game_state.attempt_spawn(FACTORY,location)
            
        
        # if any defenders is damaged, upgrade it
        for location in self.defenders_damaged_on_location:
            defender = self.defenders_damaged_on_location[location]
            upgraded = self.game_state.attempt_upgrade(location)
            if upgraded == 0 and defender == TURRET:
                wall_location = [location[0], location[1] + 1]
                if game_state.can_spawn(WALL, wall_location):
                    self.units[WALL] += game_state.attempt_spawn(WALL, wall_location) 
                
    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)
         
     ## return a list of non-stationary locations   
    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered
    


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)

        # Our turn state stats
        self.health = state["p1Stats"][0]
        self.structure_point = state["p1Stats"][1]
        self.mobile_points = state["p1Stats"][2]

        events = state["events"]
        breaches = events["breach"]
        damages = events["damage"]
        deaths = events["death"]

        defenders = [WALL, TURRET]
        # Record what position our defender gets damaged
        ## * defenders_on_location is a dictionary with 
        ## key: location, key location will always be unique since stationary unit can't occupy the same location
        ## val: unity type
        self.defenders_damaged_on_location = {}
        self.defenders_dead_on_location = {}
        # defender = Nones
        for damaged in damages:
            location = tuple(damaged[0])
            unit_owner_self = True if damaged[4] == 1 else False
            #check if unit is a denfender, return -1 if it's a mobile
            unit = INDEX_TO_UNIT_TYPE[damaged[2]]
            # gamelib.debug_write('hello:{}'.format(type(self.units)))
            if unit_owner_self and unit in defenders :
                self.defenders_damaged_on_location[location] = unit

        # Record what position our defender gets destoryed
        for death in deaths:
            location = tuple(death[0])
            unit_owner_self = False
            # if unit is a defender and not removed by ourself
            unit_owner_self = True if death[3] == 1 else False
            unit = INDEX_TO_UNIT_TYPE[death[1]]
            if  unit in defenders and not death[4]:
                self.defenders_dead_on_location[location] = unit
                self.units[unit] -= 1

        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                # gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        
        # Remove locations that are blocked by our own structures 
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)
        
        # While we have remaining MP to spend lets send out interceptors randomly.
        while game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]
            
            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """
        # First let's figure out the cheapest unit
        # We could just check the game rules, but this demonstrates how to use the GameUnit class
        stationary_units = [WALL, TURRET, FACTORY]
        cheapest_unit = WALL
        for unit in stationary_units:
            unit_class = gamelib.GameUnit(unit, game_state.config)
            if unit_class.cost[game_state.MP] < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]:
                cheapest_unit = unit

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            game_state.attempt_spawn(cheapest_unit, [x, 11])

        # Now spawn demolishers next to the line
        # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def thresh_by_round(self, round_num):
        rst = 0
        if round_num < 10:
            rst = 4 * math.floor(round_num/2.5)
        elif round_num < 20:
            rst = 4 * math.floor(round_num/3)
        elif round_num < 30:
            rst = 4 * math.floor(round_num/4)
        else:
            rst = 36
        return rst

    def thresh_by_dmg(self, game_state, path):
        dmg = 0
        for loc in path:
            dmg += self.max_damage(loc, game_state)
        return dmg

Git
if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
