from typing import List, Any

import gamelib
import random
import math
import warnings
from sys import maxsize
import json
import time

from attack import Attack

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from offensive_building_functions import (
    OffensiveInterceptorSpam,
    OffensiveDemolisherLine,
)

from defensive_building_functions import (
    DefensiveWallStrat,
    DefensiveTurretWallStrat,
)

from building_function_helper import (
    factory_location_helper,
    demolisher_location_helper,
    coordinate_path_location_helper,
    find_paths_through_coordinates
)

from defense import Defense
from region import Region

from meta_info_util import (
    are_losing,
    health_differential,
    resource_differential,
    get_structure_objects,
    get_structure_dict,
    compute_factory_impact_differential,
)


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
    # CONSTANTS

    # SP fraction dedicated to factories during normal times
    NORM_FACTORY_SP_PERCENT = 0.5
    # SP fraction dedicated to factories during bad times
    DEPRIORITIZE_FACTORY_SP_PERCENT = 0.3
    # Enforced to not choose a spawn loc resulting in too short of a path
    MIN_PATH_LENGTH = 5
    # If breached, SP threshold to place a second turret
    DOUBLE_TURRET_THRESHOLD = 10
    # When to be worried about scouts by what fraction of their MP the enemy saved
    ENEMY_SAVING_FOR_BARRAGE = 1.5
    # Testing arbitrary scaling number for when they have too much MP to know what to do with
    BARRAGE_TURN_SCALING = 1.3
    # How much of the enemy's scout cost to spend on interceptors
    SCOUT_INTERCEPTOR_COUNTER_COST_RATIO = 0.5
    # Turn to consider the back region as a weak region
    BACK_REGION_CONSIDERATION = 12
    # Threshold past which scouts are dangerous
    SCOUT_DANGER_THRESHOLD = 20


    def __init__(self):
        super().__init__()
        # OUR INITIAL SETUP BELOW
        self.health_diff = 0
        self.scored_on_locations = []
        self.enemy_units = {}
        self.units = {}  # Dict mapping unit type to unit objects
        self.regions_attacked = [{i: 0 for i in range(6)}]
        self.our_attacks = []
        self.their_attacks = []
        self.our_self_destructs = set()
        self.their_self_destructs = set()
        self.enemy_resource_history = []
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write("Random seed: {}".format(seed))

    def on_game_start(self, config):
        """
        Read in config and perform any initial setup here
        """
        gamelib.debug_write("Configuring your custom algo strategy...")
        self.config = config
        global WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        FACTORY = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0

        # Maps name as str to its actual enum - Used anywhere involving Units
        self.UNIT_ENUM_MAP = {
            "WALL": WALL,
            "FACTORY": FACTORY,
            "TURRET": TURRET,
            "SCOUT": SCOUT,
            "DEMOLISHER": DEMOLISHER,
            "INTERCEPTOR": INTERCEPTOR,
        }

        self.our_defense = Defense(self.UNIT_ENUM_MAP, 0)
        self.their_defense = Defense(self.UNIT_ENUM_MAP, 1)

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """

        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write(
            "Performing turn {} of your custom algo strategy".format(
                game_state.turn_number
            )
        )
        # Comment or remove this line to enable warnings.
        game_state.suppress_warnings(True)

        # OUR TURN-DECISION-MAKING HERE
        # Refresh meta-info
        self.health_diff = health_differential(game_state)
        self.enemy_resource_history.append((game_state.get_resource(1, 0), game_state.get_resource(1, 1)))
        # Updating internal Defense values
        self.our_defense.update_defense(self.UNIT_ENUM_MAP, game_state)
        self.their_defense.update_defense(self.UNIT_ENUM_MAP, game_state)

        # Refresh units list for both players
        self.units = self.our_defense.units
        self.enemy_units = self.their_defense.units

        # Refresh scored on locations & enemy unit breaches
        if game_state.turn_number >= 1:
            self.regions_attacked.append({i: 0 for i in range(6)})
            self.on_action_frame(turn_state)
        gamelib.util.debug_write("SCORED ON LOCATIONS: " + str(self.scored_on_locations))
        self.their_attacks.append(Attack(player_id=1, attack_type="OPPONENT", cost=0))
        # Perform moves - MAIN ENTRY POINT
        self.choose_and_execute_strategy(game_state, turn_state)
        self.scored_on_locations = []
        game_state.submit_turn()  # Must be called at the end

    #####################################################################
    ####################### OUR ALGO FUNCTIONS ##########################
    #####################################################################

    def choose_and_execute_strategy(self, game_state: GameState, turn_state: str):
        """Wrapper to choose and execute a strategy based on the game state.

        Args:
            game_state (GameState): The current GameState object
            turn_state (str): Turn state (for frame analysis)
        """
        self.our_attacks.append(Attack(player_id=0, attack_type=None, cost=0))
        # For the first 3 turns, just get set up
        if game_state.turn_number < 3:
            self.starting_strategy(game_state)
            return

        if not self.scored_on_locations:
            # BASE CASE (NORMAL)

            # Keep upgrading/building factories (max 50% of SP)
            self.resolve_factory_impact_diff(game_state)

            # Fortify regions that enemy units breached
            self.reinforce_most_attacked_region(game_state)

            # deal with blockade
            self.deal_with_blockade(game_state)

            # if there are only two or less locations the enemy can get to assume they will try to bombard us
            # protect ourselves by placing turrets near that edge
            possible_enemy_endpoints = self.calculate_all_possible_endpoints(game_state)
            if len(possible_enemy_endpoints) <= 2:
                for endpoint in possible_enemy_endpoints:
                    self.place_turrets_near_edge(game_state, endpoint)

            # General defense fortification
            self.our_defense.fortify_defenses(game_state, self.UNIT_ENUM_MAP)

            # ATTACKS BELOW THIS LINE

            # check to see if we should consider the back region in our evaluation of the weakest region
            if game_state.turn_number > self.BACK_REGION_CONSIDERATION:
                regions_to_consider = [0, 1, 2, 3, 5]
            else:
                regions_to_consider = [0, 1, 2, 3]

            self.execute_attack_strategy(game_state, regions_to_consider)
        else:
            # EMERGENCY CASE - Fortify immediately

            # Fortify regions scored on locations
            self.reinforce_after_breach(game_state)

            # Factory Impact Diff deprioritized
            self.resolve_factory_impact_diff(game_state, deprioritize=True)

            # General defense fortification
            self.our_defense.fortify_defenses(game_state, self.UNIT_ENUM_MAP)

            # Send interceptors through our weakest regions
            self.defend_strategically_with_interceptors(game_state)

    def resolve_factory_impact_diff(
        self, game_state: GameState, deprioritize: bool = False
    ) -> int:
        """Evaluated the current Factory Impact Differential and accordingly builds/upgrades factories (max 50% of SP). Prioritizes UPGRADING over building!

        Args:
            game_state (GameState): The current GameState object
            deprioritize (bool): Whether we should deprioritize building/upgrading factories. If True, will build/upgrade maximum 30% of SP

        Returns:
            num_improved (int): The number of factories built/upgraded
        """

        # At start of game, won't have any factories
        if FACTORY not in self.units:
            return 0

        # Factories we build should be a function of how many we can afford
        possible_factories = game_state.number_affordable(FACTORY)
        actual_factories = (
            self.DEPRIORITIZE_FACTORY_SP_PERCENT * possible_factories
            if deprioritize
            else self.NORM_FACTORY_SP_PERCENT * possible_factories
        )
        actual_factories_int = math.ceil(actual_factories)

        num = 0  # Counter: Don't allow to exceed actual_factories_int

        # Prioritize upgrading over building
        our_factories = self.units[FACTORY]
        for factory in our_factories:
            if not factory.upgraded:
                if num == actual_factories_int:
                    return 0

                num += game_state.attempt_upgrade((factory.x, factory.y))

        # Upgraded all possible ones. Now build any possible remaining
        possible_remaining = actual_factories_int - num
        for _ in range(possible_remaining):
            loc = factory_location_helper(game_state)
            if loc is None:
                return 0 # Impossible to build a factory! (????)

            game_state.attempt_spawn(FACTORY, loc)

    def starting_strategy(self, game_state: GameState):
        """Wrapper for executing a strategy for the first 3 rounds of the game.

        Args:
            game_state (GameState): The current GameState object
        """

        if game_state.turn_number == 0:
            self.first_round(game_state)
        elif game_state.turn_number == 1:
            self.second_round(game_state)
        elif game_state.turn_number == 2:
            self.third_round(game_state)

    #####################################################################
    ########## HARD-CODED FUNCTIONS FOR THE FIRST FEW ROUNDS ############
    #####################################################################

    def first_round(self, game_state: GameState):
        """Hard-coded moves for the first turn. Check Miro for what this results in.

        Args:
            game_state (GameState): The current GameState object
        """

        # 2 Walls on top edges
        game_state.attempt_spawn(WALL, [[0, 13], [27, 13]])

        # 4 Turrets
        game_state.attempt_spawn(TURRET, [[3, 12], [7, 9], [24, 12], [20, 9], [11, 12]])

        # 1 Factory and upgrade it
        game_state.attempt_spawn(FACTORY, [13, 1])
        game_state.attempt_upgrade([13, 1])

        # 5 Interceptors on defense
        attack_cost = 0
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [9, 4], num=3)
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [16, 2], num=2)
        self.our_attacks[-1].total_cost = attack_cost
        self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"

    def second_round(self, game_state: GameState):
        """Hard-coded moves for the second turn. Check Miro for what this results in.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO - If past turrets destroyed, replace

        # Place final turret
        game_state.attempt_spawn(TURRET, [16, 12])
        # Save rest of SP for next round to buy Factory

        # 6 Interceptors on defense
        attack_cost = 0
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [10, 3], num=3)
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [17, 3], num=3)

        self.our_attacks[-1].total_cost = attack_cost
        self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"

    def third_round(self, game_state: GameState):
        """Hard-coded moves for the third turn. Check Miro for what this results in.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO - If past turrets destroyed, replace

        # Build 2nd Factory
        game_state.attempt_spawn(FACTORY, [14, 1])
        # Save rest of SP

        # Build wall in front of every turret
        our_turrets = self.units[TURRET]
        for turret in our_turrets:
            wall_loc = (turret.x, turret.y + 1)
            game_state.attempt_spawn(WALL, wall_loc)

        # 6 Interceptors on defense
        attack_cost = 0
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [10, 3], num=3)
        attack_cost += game_state.attempt_spawn(INTERCEPTOR, [17, 3], num=3)
        self.our_attacks[-1].total_cost = attack_cost
        self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"

    #####################################################################
    ######################### HELPER FUNCTIONS ##########################
    #####################################################################

    def defend_strategically_with_interceptors(self, game_state: GameState):
        """
        Send out interceptors to pass through our weakest region as defense!

        @return: returns cost of interceptors placed
        """

        # Pass interceptors through OUR weakest region
        w_region_id = self.our_defense.weakest_region(
            self.UNIT_ENUM_MAP,
            criteria="UNDEFENDED TILES",
            regions_to_consider=range(4),
        )
        w_region_coords = self.our_defense.regions[w_region_id].coordinates

        # Find where to place Interceptor to pass through 1 of those coords
        interceptor_loc = coordinate_path_location_helper(game_state, w_region_coords)
        if interceptor_loc is not None:
            num_interceptors = math.floor(game_state.number_affordable(INTERCEPTOR))
            OffensiveInterceptorSpam().build_interceptor_spam_single_loc(
                game_state,
                self.UNIT_ENUM_MAP,
                num_interceptors,
                interceptor_loc,
            )

        return num_interceptors * 1

    def on_action_frame(self, turn_string: str):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.

        This sets our regions_attacked and scored_on_locations lists
        """

        state = json.loads(turn_string)
        events = state["events"]

        # if the turn is in deploy phase
        if state["turnInfo"] == 0:
            scouts = state["p2Units"][3]
            demolishers = state["p2Units"][4]
            interceptors = state["p2Units"][5]
            if scouts > 0 and demolishers == 0 and interceptors == 0:
                self.their_attacks[-1].attack_type = "SCOUT"

            self.their_attacks[-1].total_cost += 1 * scouts # amount of scouts on board
            self.their_attacks[-1].total_cost += 3 * demolishers # amount of demolishers on board
            self.their_attacks[-1].total_cost += 1 * interceptors # amount of interceptors on board


        # Record which regions got attacked (had enemy units inside)
        p2units = state["p2Units"]
        for unit_num in range(3, 6):
            unit_list = p2units[unit_num]
            for unit in unit_list:
                if unit[1] < 14:
                    region = self.our_defense.get_region((unit[0], unit[1]))
                    if region != -1:
                        self.regions_attacked[-1][region] += 1

        # Record locations we got scored on
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            unit_type = breach[2]
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                # gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append((tuple(location), unit_type))
                # gamelib.debug_write("All locations: {}".format(self.scored_on_locations))
                self.their_attacks[-1].breaches.append((tuple(location), unit_type))
            else:
                self.our_attacks[-1].breaches.append((tuple(location), unit_type))
        # Record attack successes
        attacks = events["attack"]
        for atk in attacks:
            unit_owner = atk[6]
            unit_attacked = atk[5]
            dmg = atk[2]
            if unit_attacked == 0 or unit_attacked == 1 or unit_attacked == 2:
                if unit_owner == 1:
                    self.our_attacks[-1].damage_dealt_to_defense += dmg
                else:
                    self.their_attacks[-1].damage_dealt_to_defense += dmg
            else:
                if unit_owner == 1:
                    self.our_attacks[-1].damage_dealt_to_troops += dmg
                else:
                    self.their_attacks[-1].damage_dealt_to_troops += dmg
        # record self destructs
        self_destructs = events["selfDestruct"]
        for sd in self_destructs:
            unit_owner = sd[5]
            damage = sd[2]
            loc = sd[0]
            if unit_owner == 1:
                self.our_attacks[-1].self_destructs.append((loc, damage))
                self.our_self_destructs.add(tuple(loc))
                self.our_attacks[-1].damage_dealt_to_defense += damage
            else:
                self.their_attacks[-1].self_destructs.append((loc, damage))
                self.their_self_destructs.add(tuple(loc))
                self.their_attacks[-1].damage_dealt_to_defense += damage

    #####################################################################
    ########### USEFUL BUT UNUSED FUNCTIONS THEY'VE PROVIDED ############
    #####################################################################

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
            if path.length() < self.MIN_PATH_LENGTH:
                continue
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += (
                    len(game_state.get_attackers(path_location, 0))
                    * gamelib.GameUnit(TURRET, game_state.config).damage_i
                )
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def least_damage_path(self, game_state: gamelib.GameState, paths: list) -> (list, int):
        """
        Finds path that takes the least damage among the paths passed in
        @param game_state: Game State
        @param paths: list of potential paths
        @return: path that takes the least amount of damage, damage taken on the path
        """
        least_damage = 100000000000
        if not paths:
            return None, least_damage
        best_path = paths[0]
        for path in paths:
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += (
                        len(game_state.get_attackers(path_location, 0))
                        * gamelib.GameUnit(TURRET, game_state.config).damage_i
                )
            if damage < least_damage:
                best_path = path
        return best_path, least_damage


    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)

        return filtered

    def reinforce_most_attacked_region(self, game_state):
        """
        Logic to find and reinforce the region that was attacked most last turn
        @param game_state: Game State
        """
        attacked_region = None
        max_attacks = 0
        for i in range(6):
            if self.regions_attacked[-1][i] > max_attacks:
                max_attacks = self.regions_attacked[-1][i]
                attacked_region = i
        if attacked_region is not None:
            self.our_defense.regions[i].fortify_region_defenses(
                game_state, self.UNIT_ENUM_MAP
            )

    def reinforce_after_breach(self, game_state: gamelib.GameState):
        """
        Reinforce breached section by placing walls at the top of our defense and turrets near the breach location
        @param game_state: Game State
        """
        for loc, unit_type in set(self.scored_on_locations):
            # If we got scored on at top-ish edges, add walls there
            loc = list(loc)
            if loc[1] > 9:
                for i in range(4):
                    game_state.attempt_spawn(
                        self.UNIT_ENUM_MAP["WALL"],
                        locations=[[i, 13], [27 - i, 13]],
                    )
            # if the unit was a scout, send interceptors to the location
            # 3 is the frame_state id for a scout
            if unit_type == 3:
                self.our_attacks[-1].total_cost += game_state.attempt_spawn(self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=loc, num=5)

            self.place_turrets_near_edge(game_state, loc)

    def place_turrets_near_edge(self, game_state: gamelib.GameState, coord):
        """
        Places turrets near a breach edge at radius 2 apart
        @param game_state: Game State
        @param coord: (x, y) to place the turrets near
        """
        for potential_turret in game_state.game_map.get_locations_in_range(
                coord, radius=2
        ):
            if game_state.can_spawn(
                    self.UNIT_ENUM_MAP["TURRET"], location=potential_turret
            ):
                game_state.attempt_spawn(
                    self.UNIT_ENUM_MAP["TURRET"], locations=potential_turret
                )
                game_state.attempt_upgrade(
                    locations=potential_turret
                )
                break
        if game_state.get_resource(0, 0) >= self.DOUBLE_TURRET_THRESHOLD:
            for potential_turret in game_state.game_map.get_locations_in_range(
                    coord, radius=2
            ):
                if game_state.can_spawn(
                        self.UNIT_ENUM_MAP["TURRET"], location=potential_turret
                ):
                    game_state.attempt_spawn(
                        self.UNIT_ENUM_MAP["TURRET"], locations=potential_turret
                    )
                    game_state.attempt_upgrade(
                        locations=potential_turret
                    )

    def calculate_all_possible_endpoints(self, game_state: gamelib.GameState):
        """
        Calculates all possible endpoints of an enemy's spawn
        @param game_state: Game State
        @return: list of unique endpoints
        """
        endpoints = set()
        for coord in self.their_defense.spawn_coordinates:
            path = game_state.find_path_to_edge(coord)
            if path is not None and path[-1][1] < 13:
                endpoints.add(tuple(path[-1]))
        return list(endpoints)

    def defend_against_potential_barrage(self, game_state: gamelib.GameState):
        """
        Defends against a potential barrage of troops by putting interceptors close to the edge
        @param game_state: Game State
        """
        enemy_mp = game_state.get_resource(1, 1)
        interceptors_to_place = min(game_state.get_resource(1, 0),
                                    int(math.floor(self.SCOUT_INTERCEPTOR_COUNTER_COST_RATIO * enemy_mp)))
        # split only in half
        # might also need to add the option to split in fourths if there's enough MP
        left = [4, 9]
        path_to_edge = game_state.find_path_to_edge(left)
        while path_to_edge is None or len(path_to_edge) < 3:
            left = [left[0] + 1, left[1] - 1]
            path_to_edge = game_state.find_path_to_edge(left)
        placed = game_state.attempt_spawn(unit_type=self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=left,
                                          num=int(interceptors_to_place / 2))

        self.our_attacks[-1].total_cost += placed

        right = [23, 9]
        path_to_edge = game_state.find_path_to_edge(right)
        while path_to_edge is None or len(path_to_edge) < 3:
            right = [right[0] - 1, right[1] - 1]
            path_to_edge = game_state.find_path_to_edge(right)

        self.our_attacks[-1].total_cost += game_state.attempt_spawn(unit_type=self.UNIT_ENUM_MAP["INTERCEPTOR"],
                                                              locations=right, num=int(interceptors_to_place - placed))
        self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"

    def deal_with_blockade(self, game_state: gamelib.GameState):
        """
        Deals with blockades that we encountered last round by destroying the buildings to the left and right
        @param game_state: Game State
        """
        for coord in self.our_self_destructs:
            if coord[1] > 12:
                continue
            left = self.our_defense.grid_unit[coord[0] - 1, coord[1]]
            right = self.our_defense.grid_unit[coord[0] + 1, coord[1]]
            if left is not None:
                game_state.attempt_remove(locations=[left.x, left.y])
            if right is not None:
                game_state.attempt_remove(locations=[right.x, right.y])
        self.our_self_destructs = set()

    def spam_demolisher_line(self, game_state, concentrated_frontal_area):
        """
        Spams a line of demolishers
        @param game_state: Game State
        @param concentrated_frontal_area: Concentrated Frontal Area object
        """
        # Target that frontal area (row + left/right half)

        y_coord = concentrated_frontal_area[0]
        x_half = concentrated_frontal_area[1]  # If True, LEFT, else RIGHT

        # Place demolishers such that they are JUST far enough to target y_coord
        # Demolishers range is 4.5
        if x_half:
            # Concentration on LEFT HALF
            wall_x_coord = 13 - (y_coord - 3)
            wall_y_coord = y_coord - 3
            length = wall_y_coord
            demolisher_x_coord = wall_x_coord + 1
            demolisher_y_coord = wall_y_coord - 1
        else:
            # Concentration on RIGHT HALF
            wall_x_coord = 27 - (13 - (y_coord - 3))
            wall_y_coord = y_coord - 3
            length = 18
            demolisher_x_coord = wall_x_coord - 1
            demolisher_y_coord = wall_y_coord - 1

        num_demolishers = math.floor(game_state.number_affordable(DEMOLISHER))
        OffensiveDemolisherLine().build_demolisher_line(
            game_state,
            self.UNIT_ENUM_MAP,
            num_demolishers,
            length,
            [wall_x_coord, wall_y_coord],
            [demolisher_x_coord, demolisher_y_coord],
            x_half,
        )
        self.our_attacks[-1].total_cost += 3 * num_demolishers
        self.our_attacks[-1].attack_type = "DEMOLISHER LINE"

    def execute_attack_strategy(self, game_state, regions_to_consider):
        """
        Logic for executing the attack strategy
        @todo MAKE THE STRATEGY MORE DYNAMIC
        @param game_state: Game State
        @param regions_to_consider: Which regions to consider
        """
        # find the weakest region to use in calculations
        open_region = False
        if any(self.our_defense.regions[i].states["TURRET COUNT"] == 0 for i in regions_to_consider):
            open_region = True
            weakest_region_id = self.their_defense.weakest_region(
                self.UNIT_ENUM_MAP,
                criteria="TURRET COUNT",
                regions_to_consider=regions_to_consider,
            )
        else:
            weakest_region_id = self.their_defense.weakest_region(
                self.UNIT_ENUM_MAP,
                criteria="AVG TILE DMG",
                regions_to_consider=regions_to_consider,
            )

        # IMPORTANT CONSTANTS FOR IF STATEMENTS:
        # finds the boundary of the weakest region
        weakest_region_boundary = list(self.their_defense.regions[weakest_region_id].all_boundaries)
        # finds all possible paths from starting coordinates
        all_possible_paths = {tuple(coord): game_state.find_path_to_edge(coord) for coord in
                              self.our_defense.spawn_coordinates}
        # Removes all paths with length less than or equal to 3
        to_delete = []
        for coord, path in all_possible_paths.items():
            if path is None or len(path) <= 3:
                to_delete.append(coord)
        [all_possible_paths.pop(coord) for coord in to_delete]
        # All possible starting coordinates
        all_possible_starts = [path[0] for path in all_possible_paths]

        all_possible_paths = list(all_possible_paths.values())

        # whether or not we have a concentrated frontal area
        concentrated_frontal_area = demolisher_location_helper(
            game_state, self.UNIT_ENUM_MAP, self.their_defense.units
        )

        # if the opponent seems like they're saving up to barrage us
        if self.saving_up_for_barrage(game_state) and self.their_attacks[-1].attack_type != "SCOUTS":
            if (any(self.our_defense.regions[i].states["TURRET COUNT"] < 4 for i in regions_to_consider)
                    or game_state.get_resource(1, 1) > self.SCOUT_DANGER_THRESHOLD):
                self.defend_against_potential_barrage(game_state)
                self.find_and_spawn_units(game_state, weakest_region_boundary, all_possible_paths, "INTERCEPTOR", game_state.number_affordable(
                                                                            self.UNIT_ENUM_MAP["INTERCEPTOR"]))
                return

        # if there's an open region, split demolisher/interceptor
        if open_region:
            self.demolisher_interceptor_pairs(game_state, weakest_region_boundary, all_possible_paths, interceptors=2)

        if concentrated_frontal_area is not None:
            # Target that frontal area (row + left/right half)
            self.spam_demolisher_line(game_state, concentrated_frontal_area)
        if game_state.get_resource(1, 0) > 5:
            self.demolisher_interceptor_pairs(game_state, weakest_region_boundary, all_possible_paths, interceptors=2)
        else:
            self.defend_strategically_with_interceptors(game_state)

    def saving_up_for_barrage(self, game_state):
        """
        Determines whether or not the opponent is saving up for a barrage strategy
        @param game_state: Game State
        @return: above statement
        """
        return (game_state.get_resource(1, 1) >
                    min(self.ENEMY_SAVING_FOR_BARRAGE * self.enemy_resource_history[-1][1],
                    self.BARRAGE_TURN_SCALING * game_state.turn_number))

    def demolisher_interceptor_pairs(self, game_state, boundary, paths, interceptors=2):
        """
        Function to build a pair of demolishers/interceptors on the same coordinate
        @param game_state: Game State
        @param boundary: Boundary of the region we want to enter
        @param paths: all possible paths to consider
        @param interceptors: quantity of interceptors to demolishers
        """
        pairs = int(game_state.get_resource(1, 0) / (3 + interceptors))
        loc = self.find_and_spawn_units(game_state, boundary, paths, "DEMOLISHER", pairs)
        if loc is None:
            return
        gamelib.debug_write(self.our_attacks[-1].total_cost)
        spawned = game_state.attempt_spawn(self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=loc, num=(2 * pairs))
        gamelib.util.debug_write(spawned)
        # self.our_attacks[-1].total_cost +=

    def find_and_spawn_units(self, game_state, region_boundary, possible_paths, unit_type, num):
        """
        Finds best location to spawn units and spawns them
        @param game_state: Game State
        @param region_boundary: boundary of the region we want
        @param possible_paths: all the paths to consider
        @param unit_type: unit type from self.UNIT_ENUM_MAP
        @param num: number of units
        @return: Best location to spawn (none if none exist)
        """
        viable_paths = find_paths_through_coordinates(paths=possible_paths, desired_coordinates=region_boundary)
        best_path, dmg = self.least_damage_path(game_state, viable_paths)
        if best_path is not None:
            # places interceptors on best possible location
            spawned = game_state.attempt_spawn(self.UNIT_ENUM_MAP[unit_type], locations=best_path[0], num=num)
            if spawned is not None:
                if unit_type == "DEMOLISHER":
                    self.our_attacks[-1].total_cost += 3 * spawned
            return best_path[0]
        else:
            None

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
