import json
import math
import random
import gamelib
import warnings
from sys import maxsize

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
        global TURRET_AR, TURRET_AD, SCOUT_AR, SCOUNT_AD, SCOUT_HP, DEMOLISHER_AR, DEMOLISHER_AD, INTERCEPTOR_AR, INTERCEPTOR_AD
        TURRET_AR = config["unitInformation"][2]["attackRange"]
        TURRET_AD = config["unitInformation"][2]["attackDamageWalker"]
        SCOUT_AR = config["unitInformation"][3]["attackRange"]
        SCOUT_AD = config["unitInformation"][3]["attackDamageWalker"]
        SCOUT_HP = config["unitInformation"][3]["startHealth"]
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
        self.turrect_locations = []
        self.defenders_damaged_on_location = {} ## * record what position our denfenders got damaged, key is location and val is unity string type
        self.defenders_dead_on_location = {} ## * record what position our denfenders got destroyed, key is location and val is unity string type
        self.factory_left_wing = [12,3]
        self.factory_right_wing = [15,3]
        self.wall_right_wing = [24,13]
        self.wall_left_wing = [3,13]
        self.factory_locations = []
        self.structure_point = 0 ## * our sp on each turn
        self.mobile_points = 0 ## * our mp on each turn
        self.health = 0 ## * our health each turn

        ## * TURRET
        self.turret_left_wing = [3,12]
        self.turret_right_wing= [24,12]
        # self.remain_turrects = [[8,11],[19,11]]
        # self.additional_turrets = [[12,12], [14,12], [5,11], [22,11], [11,10], [15,10], [16,11]]
        self.loss_on_locations = []

        self.which_edge_damaged = -1 # -1 undamaged, 0: left, 1:right
        self.prev_dmg_src = 0


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

        # Now build reactive defenses based on where the enemy scored
        # self.build_reactive_defense(game_state)


        ## * DEPLOY
        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        # ------------------------------------ original strategy ------------------------------------
        # if game_state.turn_number < 5:
        #     self.stall_with_interceptors(game_state)
        # else:
        #     # Now let's analyze the enemy base to see where their defenses are concentrated.
        #     # If they have many units in the front we can build a line for our demolishers to attack them at long range.
        #     if self.detect_enemy_unit(game_state, unit_type=None, valid_x=None, valid_y=[14, 15]) > 10:
        #         self.demolisher_line_strategy(game_state)
        #     else:
        #         # They don't have many units in the front so lets figure out their least defended area and send Scouts there.

        #         # Only spawn Scouts every other turn
        #         # Sending more at once is better since attacks can only hit a single scout at a time
        #         if game_state.turn_number % 2 == 1:
        #             # To simplify we will just check sending them from back left and right
        #             scout_spawn_location_options = [[13, 0], [14, 0]]
        #             best_location = self.least_damage_spawn_location(game_state, scout_spawn_location_options)
        #             game_state.attempt_spawn(SCOUT, best_location, 1000)

        #         # Lastly, if we have spare SP, let's build some Factories to generate more resources
        #         factory_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        #         game_state.attempt_spawn(FACTORY, factory_locations)

        # ------------------------------------ our naive strategy ------------------------------------
        # Choose a start point from [[13, 0], [14, 0]]
        start_pt_for_scout = self.choose_start_point_for_scout(game_state)
        start_pt_for_interceptor = self.choose_start_point_for_interceptor(game_state)

        # Get the corresponding edge and end location
        edge_for_scout = game_state.game_map.TOP_RIGHT
        if start_pt_for_scout[0] == 14:
            edge_for_scout = game_state.game_map.TOP_LEFT
        path_for_scout = game_state.find_path_to_edge(start_pt_for_scout, edge_for_scout)
        if path_for_scout == None:
            return
        end_pt_for_scout = path_for_scout[-1]

        # Deploy interceptor to dynamically defend
        intcpter_num = self.thresh_intcpter(game_state.turn_number)
        # df_list = [[1,12], [25,11], [13, 0], [2,11], [25,11], [14,0], [3,10], [24,10], [4,9], [23,9]]  df_list = [[26,12], [1,12], [4,9], [23,9], [7,6], [20,6]]

        df_list = [[13,0], [14,0], [12,1], [15,1], [9,4], [18,4]]
        loss_count = 0
        visited_list = []
        locations_rst = []
        loss_rst = []
        for ind in range(0, len(self.scored_on_locations)):
            temp = self.scored_on_locations.count(self.scored_on_locations[ind])
            if visited_list.count(self.scored_on_locations[ind]) == 0:
                visited_list.append(self.scored_on_locations[ind])
                locations_rst.append(self.scored_on_locations[ind])
                loss_rst.append(temp)

        for i in range(0, intcpter_num):
            if len(locations_rst) > i:
                game_state.attempt_spawn(INTERCEPTOR, locations_rst[i],
                math.ceil(loss_rst[i] / 5)+1)
                #gamelib.debug_write("value after ceiling: {}".format(math.ceil(loss_rst[i] / 5)))
                loss_count += 1
            else:
                if i-loss_count < len(df_list):
                    game_state.attempt_spawn(INTERCEPTOR, df_list[i-loss_count], 1)

        self.scored_on_locations = []
        self.loss_on_locations = []


        # Decide whether to deploy scouts or not （Ivy's idea)
        percentage_for_scount = 1  # Assumption: use 80% of MP to deploy scouts
        deploy_threshold = 0.5
        total_MP = game_state.get_resource(1, 0) # MP (1), 0 - us
        MP_for_scounts = math.floor(total_MP * percentage_for_scount)
        total_health_of_scounts = MP_for_scounts * SCOUT_HP
        max_receiveable_damage = self.get_damage_at_location(end_pt_for_scout, game_state)

        # Temporarily hold
        #if max_receiveable_damage < total_health_of_scounts * deploy_threshold:
        #    game_state.attempt_spawn(SCOUT, start_pt, MP_for_scounts)
                # # Lastly, if we have spare SP, let's build some Factories to generate more resources
                # factory_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
                # game_state.attempt_spawn(FACTORY, factory_locations)

        if game_state.turn_number < 6:
            game_state.attempt_spawn(SCOUT, start_pt_for_interceptor, MP_for_scounts)
        # elif game_state.turn_number < 7:
        #     if max_receiveable_damage < total_health_of_scounts * deploy_threshold:
        #         game_state.attempt_spawn(SCOUT, start_pt_for_scout, MP_for_scounts)
        else:
            if MP_for_scounts >= self.thresh_by_round(game_state.turn_number):
                gamelib.debug_write("threshold is : {}".format(game_state.turn_number))
                game_state.attempt_spawn(SCOUT, start_pt_for_scout, math.floor(total_MP))

    ## * init_setup will set up the units and structures at the begining
    def init_setup(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """

        # Place turrets that attack enemy units
        turret_locations = [self.turret_left_wing, self.turret_right_wing,[14,11]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)

        #Place upggraded factories at the deepest location
        factory_locations = [[13,2],[14,2],self.factory_left_wing, self.factory_right_wing]
        game_state.attempt_spawn(FACTORY, factory_locations)


    # calculates the maximum damage a unit will take at location,
    # which is a list with two elements representing x, y coordinates,
    # returns an integer
    def get_damage_at_location(self, location, game_state):
        damage = 0

        # Our mobile unit is in enemy‘s half of the arena
        attackers = game_state.get_attackers(location, 0)
        for attacker in attackers:
            damage += TURRET_AD
        return damage

    def rebuild_defender(self, game_state):
        # if any denfenders are destoryed, rebuild
        for location in self.defenders_dead_on_location:
            defender = self.defenders_dead_on_location[location]
            succeed = game_state.attempt_spawn(defender, location)
            self.structure_point -= game_state.type_cost(defender)[SP] * succeed

    def build_factory(self, game_state, threshold):
        ## build factory
        threshold = 1
        factory_affordable = game_state.number_affordable(FACTORY)
        # gamelib.debug_write("factory affordable:{}".format(game_state.number_affordable(FACTORY)))
        if factory_affordable >= threshold:
            # * alternating factory left and right wing
            # * mod 2 = 0, left wing
            # * mod 2 =1, right wing
            location = None

            if len(self.factory_locations) == 0:
                self.factory_left_wing = [12,3]
                self.factory_right_wing = [15,3]

            for _ in range(threshold):
                if len(self.factory_locations) % 2 == 0:
                    x,y = self.factory_left_wing
                    self.factory_left_wing = [x-1,y+1]
                    location = self.factory_left_wing
                else:
                    x,y = self.factory_right_wing
                    self.factory_right_wing = [x+1,y+1]
                    location  = self.factory_right_wing
                if game_state.can_spawn(FACTORY,location):
                    succeed = game_state.attempt_spawn(FACTORY,location)
                    if succeed != 0:
                        self.factory_locations.append(location)
                    self.structure_point -= game_state.type_cost(FACTORY)[SP] * succeed

    ## reinfore deenders: i.e defenders are damaged and need reinforement
    def reinforce_defenders(self, game_state):
        location = None
    #    gamelib.debug_write("reinforce:{},{}".format(self.turret_left_wing, self.turret_right_wing))
        if tuple(self.turret_left_wing) in self.defenders_damaged_on_location:
            x,y = self.turret_left_wing
            self.turret_left_wing =[x+1,y]
            location = self.turret_left_wing
            self.which_edge_damaged = 0
            # gamelib.debug_write("reinforce:{}".format(location))

        elif tuple(self.turret_right_wing) in self.defenders_damaged_on_location:
            x,y = self.turret_right_wing
            self.turret_right_wing = [x-1,y]
            location = self.turret_right_wing
            self.which_edge_damaged = 1
            # gamelib.debug_write("reinaforce:{}".format(location))
        if location and game_state.can_spawn(TURRET,location):
            succeed = game_state.attempt_spawn(TURRET,location)
            upgraded = game_state.attempt_upgrade(location)
        # gamelib.debug_write("upgraded:{}".format(self.turret_left_wing))

        if self.which_edge_damaged == 0:
            upgraded = game_state.attempt_upgrade(self.turret_left_wing)
        elif self.which_edge_damaged == 1:
            upgraded = game_state.attempt_upgrade(self.turret_right_wing)

        for location in self.defenders_damaged_on_location:
            defender = self.defenders_damaged_on_location[location]
            upgraded = game_state.attempt_upgrade(location)
            if upgraded == 0 and defender == TURRET:
                wall_location = [location[0], location[1] + 1]
                if game_state.can_spawn(WALL, wall_location):
                    game_state.attempt_spawn(WALL, wall_location)





    def reinforce_factory(self, game_state):
        for location in self.factory_locations:
            ## check whether the unit is upgraded or not
            # gamelib.debug_write("upgrade: {},{},{}".format(location, len(self.factory_locations),gamelib.GameUnit(FACTORY,game_state.config,location).upgraded))
            if not gamelib.GameUnit(FACTORY,game_state.config,location).upgraded:
                succeed = game_state.attempt_upgrade(location)
                if succeed != 0:
                    break


    def reinforce_wall_or_turret(self, game_state):
        location = None
        turrect_location = None
        if tuple(self.wall_left_wing) in self.defenders_damaged_on_location:
            x,y = self.wall_left_wing
            self.wall_left_wing =[x+1,y]
            location = self.wall_left_wing
            turrect_location = self.turret_left_wing

        elif tuple(self.wall_right_wing) in self.defenders_damaged_on_location:
            x,y = self.wall_right_wing
            self.wall_right_wing = [x-1,y]
            location = self.wall_right_wing
            turrect_location = self.turret_right_wing

        if location and game_state.can_spawn(WALL,location):
            succeed = game_state.attempt_spawn(WALL,location)
            upgraded = game_state.attempt_upgrade(location)
        if turrect_location:
            game_state.attempt_upgrade(turrect_location)


    ## decides to build factory or defense
    ## * Priority:
    ## 1. build defenders if any is destroyed
    ## 2. upgrade defenders if any is damaged
    def production_or_defense(self, game_state):
       factory_limit = 8
       self.rebuild_defender(game_state)
       top_edge_wall_location = [self.wall_left_wing, self.wall_right_wing]

       if game_state.turn_number  == 1 :
            for location in top_edge_wall_location:
                game_state.attempt_spawn(WALL, location)
                game_state.attempt_upgrade(location)

       elif game_state.turn_number == 2:
           ## spawn one upgraded wall
          self.reinforce_wall_or_turret(game_state)
       else:
            if len(self.factory_locations) < factory_limit:
                self.build_factory(game_state,1)
            else:
                self.reinforce_factory(game_state)

       self.reinforce_defenders(game_state)

            # ## place the factory and reamaining turrect layout alternatively, if possible
            # if self.structure_point % game_state.type_cost(FACTORY)[SP] == 4:
            #     self.build_factory(game_state, 1, 1)
            #     self.structure_point = 4
            # else:
            #     self.build_factory(game_state, math.floor(self.structure_point * 0.8 / 6), 2)
            #     self.structure_point -= math.floor(self.structure_point*0.8)
            #     self.build_remaining_turrect(game_state, max(math.floor(self.structure_point/2),
            #                                                             math.floor(game_state.turn_number/10) * 2), 2)



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
        factories = state["p1Units"][UNIT_TYPE_TO_INDEX[FACTORY]]
        self.factory_locations = [[fact[0],fact[1]] for fact in factories]

        events = state["events"]
        breaches = events["breach"]
        damages = events["damage"]
        deaths = events["death"]

        defenders = [WALL, TURRET]
        # Record what position our defender gets damaged
        ## * defenders_on_location is a dictionary with
        ## key: location, key location will always be unique since stationary unit can't occupy the same location
        ## val: unity type
        # self.defenders_damaged_on_location = {}
        # self.defenders_dead_on_location = {}
        # defender = Nones
        for damaged in damages:
            location = tuple(damaged[0])
            unit_owner_self = True if damaged[4] == 1 else False
            #check if unit is a denfender, return -1 if it's a mobile
            unit = INDEX_TO_UNIT_TYPE[damaged[2]]
            if unit_owner_self and unit in defenders :
                self.defenders_damaged_on_location[location] = unit

        # Record what position our defender gets destoryed
        for death in deaths:
            location = tuple(death[0])
            unit_owner_self = False
            # if unit is a defender and not removed by ourself
            unit_owner_self = True if death[3] == 1 else False
            unit = INDEX_TO_UNIT_TYPE[death[1]]

            # gamelib.debug_write("defenders: {},{}".format(defenders,unit))
            if  unit in defenders and not death[4]:
                # gamelib.debug_write("dead on:{},{}".format(unit,location))
                self.defenders_dead_on_location[location] = unit

        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                # gamelib.debug_write("Got scored on at: {}".format(location))
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
        if round_num < 3:
            rst = 4 * math.floor(round_num)
        elif round_num < 5:
            rst = 4 * math.floor(round_num/1.25)
        elif round_num < 8:
            rst = 4 * math.floor(round_num/1.5)
        elif round_num < 10:
            rst = 4 * math.floor(round_num/1.5)
        else:
            rst = 25
        return rst

    def thresh_by_dmg(self, game_state, path):
        dmg = 0
        for loc in path:
            dmg += self.get_damage_at_location(loc, game_state)
        return dmg

    def thresh_intcpter(self, round):
        if round < 3:
            return 1
        elif 3 <= round < 5:
            return 2
        elif 5 <= round <= 8:
            return 3
        else:
            return 4

    # helper for choose_start_point
    def find_damage_at_endpoint_from_start(self, game_state, start_point):
        edge = game_state.game_map.TOP_RIGHT
        if start_point[0] == 14:
            edge = game_state.game_map.TOP_LEFT
        path = game_state.find_path_to_edge(start_point, edge)
        if path == None:
            return float('inf')
        else:
            return self.get_damage_at_location(path[-1], game_state)

    # choose from either [13,0] or [14,0] to deploy interceptor
    # depending on where we were damaged last round
    # returns starting location
    def choose_start_point_for_interceptor(self, game_state):
        start1 = [13, 0]
        start2 = [14, 0]
        damaged_on_right = 0
        damaged_on_left = 0
        for location in self.defenders_damaged_on_location:
            if location[0] >= 14:
                damaged_on_right += 1
            else:
                damaged_on_left += 1

        if damaged_on_left < damaged_on_right:
            self.prev_dmg_src = -1
            return [13, 0]
        elif damaged_on_left > damaged_on_right:
            self.prev_dmg_src = 1
            return [14, 0]
        else:
            if self.prev_dmg_src == -1:
                return [13,0]
            elif self.prev_dmg_src == 1:
                return [14,0]
            else:
                return [13,0] #RRR



    # choose from either [13,0] or [14,0] to deploy the scouts
    # depending on the defense focus of enemy
    # returns starting location
    def choose_start_point_for_scout(self, game_state):
        start1 = [13, 0]
        start2 = [14, 0]
        damage1 = self.find_damage_at_endpoint_from_start(game_state, start1)
        damage2 = self.find_damage_at_endpoint_from_start(game_state, start2)
        if damage1 <= damage2:
            return [13, 0]
        else:
            return [14, 0]


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
