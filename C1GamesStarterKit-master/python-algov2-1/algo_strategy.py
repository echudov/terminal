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
    find_paths_through_coordinates,
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
    # If breached, SP minumum threshold to place a second turret
    DOUBLE_TURRET_THRESHOLD = 10
    # Min threshold to assume enemy is saving for a barrage as ratio of MP (lastturn/thisturn)
    ENEMY_SAVING_FOR_BARRAGE = 1.5  # eg. 1.5 is 150%
    # Testing arbitrary scaling number for when they have too much MP to know what to do with
    BARRAGE_TURN_SCALING = 1.3  # In later turns, start to get more MP
    # How much of the enemy's scout cost to spend on interceptors
    SCOUT_INTERCEPTOR_COUNTER_COST_RATIO = 0.5
    # Turn to consider the back region as a weak region
    BACK_REGION_CONSIDERATION = 12
    # Threshold past which scouts are dangerous
    SCOUT_DANGER_THRESHOLD = 15

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
        self.enemy_resource_history.append(
            (game_state.get_resource(0, 1), game_state.get_resource(1, 1))
        )
        # Updating internal Defense values
        self.our_defense.update_defense(self.UNIT_ENUM_MAP, game_state)
        self.their_defense.update_defense(self.UNIT_ENUM_MAP, game_state)

        # Refresh units list for both players
        self.units = self.our_defense.units
        self.enemy_units = self.their_defense.units

        # Refresh scored on locations, enemy unit breaches, attacks, & self-destructs
        if game_state.turn_number >= 1:
            self.regions_attacked.append({i: 0 for i in range(6)})
            self.on_action_frame(turn_state)
            gamelib.util.debug_write("OUR LAST ATTACK: " + str(self.our_attacks[-1]))
            gamelib.util.debug_write(
                "THEIR LAST ATTACK: " + str(self.their_attacks[-1])
            )

        # Initialize attack tracking for this turn
        self.their_attacks.append(Attack(player_id=1, attack_type="OPPONENT", cost=0))
        self.our_attacks.append(Attack(player_id=0, attack_type=None, cost=0))

        # Perform moves - MAIN ENTRY POINT
        self.choose_and_execute_strategy(game_state, turn_state)
        # Reset scored_on_locations
        self.scored_on_locations = []

        game_state.submit_turn()  # Must be called at the end

    #####################################################################
    ####################### OUR ALGO FUNCTIONS ##########################
    #####################################################################

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
                # They are doing a SCOUT barrage
                self.their_attacks[-1].attack_type = "SCOUT"

            self.their_attacks[-1].total_cost += 1 * scouts  # num scouts on board
            self.their_attacks[-1].total_cost += 3 * demolishers  # num dems on board
            self.their_attacks[-1].total_cost += 1 * interceptors

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

        # Record attack successes (both ours and enemy's)
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

    def choose_and_execute_strategy(self, game_state: GameState, turn_state: str):
        """Wrapper to choose and execute a strategy based on the game state.

        Args:
            game_state (GameState): The current GameState object
            turn_state (str): Turn state (for frame analysis)
        """

        # For the first 3 turns, just get set up (hard-coded functions)
        if game_state.turn_number < 3:
            self.starting_strategy(game_state)
            return

        if len(self.scored_on_locations) == 0:
            # BASE CASE (NORMAL)

            # Keep upgrading/building factories (max 50% of SP)
            gamelib.debug_write("RESOLVING FACTORY IMPACT DIFF")
            t0 = time.time()
            self.resolve_factory_impact_diff(game_state)
            gamelib.util.debug_write(
                "FACTORY IMPACT DIFF RESOLVED IN: " + str(time.time() - t0)
            )

            # Fortify regions that enemy units breached the most
            gamelib.debug_write("REINFORCING MOST ATTACKED REGION")
            t0 = time.time()
            self.reinforce_most_attacked_region(game_state)
            gamelib.util.debug_write(
                "REINFORCED MOST ATTACK REGION IN: " + str(time.time() - t0)
            )

            # Deal with any structures blocking our units last turn
            gamelib.util.debug_write("RESOLVING BLOCKADES")
            t0 = time.time()
            self.resolve_existing_blocks(game_state)
            gamelib.util.debug_write("BLOCKADES RESOLVED IN: " + str(time.time() - t0))

            # If two or fewer reachable locations for enemy, assume they will bombard us
            # Protect ourselves by placing turrets near that edge
            gamelib.util.debug_write("CALCULATING ENDPOINTS")
            t0 = time.time()
            possible_enemy_endpoints = self.calculate_all_possible_endpoints(game_state)
            if len(possible_enemy_endpoints) <= 2:
                for endpoint in possible_enemy_endpoints:
                    self.place_turrets_near_coord(game_state, endpoint)
            gamelib.util.debug_write(
                "ENDPOINTS CALCULATED IN: " + str(time.time() - t0)
            )
            # General defense fortification
            # TODO- Still need this?
            t0 = time.time()
            gamelib.util.debug_write("FORTIFYING DEFENSES")
            self.our_defense.fortify_defenses(game_state, self.UNIT_ENUM_MAP)
            gamelib.util.debug_write("DEFENSES FORTIFIED IN: " + str(time.time() - t0))
            # ATTACKS BELOW THIS LINE

            # Which regions should we consider?
            if game_state.turn_number > self.BACK_REGION_CONSIDERATION:
                regions_to_consider = [0, 1, 2, 3, 5]
            else:
                regions_to_consider = [0, 1, 2, 3]
            gamelib.util.debug_write("EXECUTING ATTACK STRATEGY")
            t0 = time.time()
            self.execute_attack_strategy(game_state, regions_to_consider)
            gamelib.util.debug_write(
                "ATTACK STRATEGY EXECUTED IN: " + str(time.time() - t0)
            )
        else:
            # EMERGENCY CASE - We got scored on - Fortify immediately
            t0 = time.time()
            gamelib.util.debug_write("EMERGENCY FORTIFICATIONS STARTING")
            # Reinforce scored on locations
            self.reinforce_after_scored_on(game_state)

            # Factory Impact Diff deprioritized
            self.resolve_factory_impact_diff(game_state, deprioritize=True)

            # General defense fortification
            # TODO- Still need this?
            self.our_defense.fortify_defenses(game_state, self.UNIT_ENUM_MAP)

            # Send interceptors through our weakest regions
            self.defend_strategically_with_interceptors(game_state)
            gamelib.util.debug_write(
                "FINISHED EMERGENCY FORTIFICATIONS IN: " + str(time.time() - t0)
            )
            # WE DON'T SPEND ANY MP ON ATTACKS - ONLY DEFENSE

    def resolve_factory_impact_diff(
        self, game_state: GameState, deprioritize: bool = False
    ):
        """Evaluated the current Factory Impact Differential and accordingly builds/upgrades factories (max 50% of SP). Prioritizes UPGRADING over building!

        Args:
            game_state (GameState): The current GameState object
            deprioritize (bool): Whether we should deprioritize building/upgrading factories. If True, will build/upgrade maximum 30% of SP

        Returns:
            num_improved (int): The number of factories built/upgraded
        """

        # At start of game, won't have any factories
        if FACTORY not in self.units:
            return

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
                    return

                num += game_state.attempt_upgrade((factory.x, factory.y))

        # Upgraded all possible ones. Now build any possible remaining
        possible_remaining = actual_factories_int - num
        for _ in range(possible_remaining):
            loc = factory_location_helper(game_state)
            if loc is None:
                return  # Impossible to build a factory - probably reached max rows

            game_state.attempt_spawn(FACTORY, loc)

    #####################################################################
    ####################### DEFENSE HELPER FUNCTIONS ####################
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
            self.our_attacks[-1].total_cost += num_interceptors

    def reinforce_most_attacked_region(self, game_state: GameState):
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

    def reinforce_after_scored_on(self, game_state: gamelib.GameState):
        """
        Reinforce scored on section by placing walls at the top of our defense and turrets near the scored on location
        @param game_state: Game State
        """

        for loc, unit_type in set(self.scored_on_locations):
            loc = list(loc)

            # If we got scored on at top-ish edges, add walls there
            if loc[1] > 9:
                for i in range(4):
                    game_state.attempt_spawn(
                        self.UNIT_ENUM_MAP["WALL"],
                        locations=[[i, 13], [27 - i, 13]],
                    )

            # If the unit was a scout, send interceptors to the location next round
            # 3 is the frame_state id for a scout
            if unit_type == 3:
                loc2 = [27 - loc[0], loc[1]]
                self.our_attacks[-1].total_cost += game_state.attempt_spawn(
                    self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=loc2, num=3
                )
                self.our_attacks[-1].total_cost += game_state.attempt_spawn(
                    self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=loc, num=3
                )

            # Place turrets near this location
            self.place_turrets_near_coord(game_state, loc)

    def place_turrets_near_coord(
        self, game_state: gamelib.GameState, coord: (int, int) or [int, int]
    ):
        """
        Places turrets near a given coord
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
                game_state.attempt_upgrade(locations=potential_turret)
                break

        # If we still have lots of resources, place another turret
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
                    game_state.attempt_upgrade(locations=potential_turret)

    def defend_against_potential_barrage(self, game_state: gamelib.GameState):
        """
        Defends against a potential barrage of troops by putting interceptors close to the edge
        @param game_state: Game State
        """
        enemy_mp = game_state.get_resource(1, 1)
        interceptors_to_place = min(
            game_state.get_resource(1, 0),
            int(math.floor(self.SCOUT_INTERCEPTOR_COUNTER_COST_RATIO * enemy_mp)),
        )
        # split only in half
        # might also need to add the option to split in fourths if there's enough MP
        left = [4, 9]
        path_to_edge = game_state.find_path_to_edge(left)
        while left[1] > 0 and (
            path_to_edge is None or len(path_to_edge) < self.MIN_PATH_LENGTH
        ):
            left = [left[0] + 1, left[1] - 1]
            path_to_edge = game_state.find_path_to_edge(left)
        placed = game_state.attempt_spawn(
            unit_type=self.UNIT_ENUM_MAP["INTERCEPTOR"],
            locations=left,
            num=int(interceptors_to_place / 2),
        )

        self.our_attacks[-1].total_cost += placed

        right = [23, 9]
        path_to_edge = game_state.find_path_to_edge(right)
        while right[1] > 0 and (
            path_to_edge is None or len(path_to_edge) < self.MIN_PATH_LENGTH
        ):
            right = [right[0] - 1, right[1] - 1]
            path_to_edge = game_state.find_path_to_edge(right)

        self.our_attacks[-1].total_cost += game_state.attempt_spawn(
            unit_type=self.UNIT_ENUM_MAP["INTERCEPTOR"],
            locations=right,
            num=int(interceptors_to_place - placed),
        )
        self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"

    def saving_up_for_barrage(self, game_state: GameState):
        """
        Determines whether or not the opponent is saving up for a barrage strategy
        @param game_state: Game State
        @return: above statement
        """

        return game_state.get_resource(1, 1) > min(
            self.ENEMY_SAVING_FOR_BARRAGE * self.enemy_resource_history[-1][1],
            self.BARRAGE_TURN_SCALING * game_state.turn_number,
        )

    #####################################################################
    ####################### OFFENSE HELPER FUNCTIONS ####################
    #####################################################################

    def execute_attack_strategy(
        self, game_state: GameState, regions_to_consider: [int]
    ):
        """
        Logic for executing the attack strategy
        @todo MAKE THE STRATEGY MORE DYNAMIC
        @param game_state: Game State
        @param regions_to_consider: Which regions to consider
        """

        # PRECOMPUTATIONS FOR LATER LOGIC FLOW:

        # find the weakest region to use in calculations

        gamelib.util.debug_write("BEGINNING ATTACK STRAT PRECOMPUTATIONS")
        t0 = time.time()
        open_region = False
        if any(
            self.their_defense.regions[i].states["TURRET COUNT"] == 0
            for i in regions_to_consider
        ):
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

        # finds the boundary of the weakest region
        weakest_region_boundary = list(
            self.their_defense.regions[weakest_region_id].all_boundaries
        )
        # finds all possible paths from starting coordinates
        all_possible_paths = {
            tuple(coord): game_state.find_path_to_edge(coord)
            for coord in self.our_defense.spawn_coordinates
        }
        # Remove all paths with length less than or equal to 3
        to_delete = []
        for coord, path in all_possible_paths.items():
            if path is None or len(path) <= 3:
                to_delete.append(coord)
        [all_possible_paths.pop(coord) for coord in to_delete]
        # All possible starting coordinates
        all_possible_starts = [path[0] for path in all_possible_paths]

        all_possible_paths = list(all_possible_paths.values())

        # whether or not THEY have a concentrated frontal area
        concentrated_frontal_area = demolisher_location_helper(
            game_state, self.UNIT_ENUM_MAP, self.their_defense.units
        )
        gamelib.util.debug_write(
            "ATTACK STRATEGY PRECOMPUTATIONS FINISHED IN: " + str(time.time() - t0)
        )
        # LOGIC FLOW STARTS HERE:

        # if the opponent seems like they're saving up to barrage us
        if (
            self.saving_up_for_barrage(game_state)
            and self.their_attacks[-1].attack_type != "SCOUTS"
        ):
            if (
                any(
                    self.our_defense.regions[i].states["TURRET COUNT"] < 4
                    for i in regions_to_consider
                )
                or game_state.get_resource(1, 1) > self.SCOUT_DANGER_THRESHOLD
            ):
                gamelib.util.debug_write("DEFENDING AGAINST POTENTIAL BARRAGE")
                t0 = time.time()
                self.defend_against_potential_barrage(game_state)
                gamelib.util.debug_write(
                    "PART 1 OF DEFENSE DONE IN: " + str(time.time() - t0)
                )
                self.spawn_units_least_damage_path(
                    game_state,
                    weakest_region_boundary,
                    all_possible_paths,
                    "INTERCEPTOR",
                    game_state.number_affordable(self.UNIT_ENUM_MAP["INTERCEPTOR"]),
                )
                self.our_attacks[-1].attack_type = "INTERCEPTOR DEFENSE"
                gamelib.util.debug_write(
                    "TIME TO FULLY DEFEND AGAINST POTENTIAL BARRAGE: "
                    + str(time.time() - t0)
                )
                return

        # if there's an open region, split demolisher/interceptor
        if open_region:
            gamelib.util.debug_write("DEMOLISHER INTERCEPTOR PAIR")
            t0 = time.time()
            self.demolisher_interceptor_pairs(
                game_state, weakest_region_boundary, all_possible_paths, interceptors=2
            )
            self.our_attacks[-1].attack_type = "DEMOLISHER INTERCEPTOR"
            gamelib.util.debug_write(
                "TIME TO PLACE DEMOLISHERS & INTERCEPTORS: " + str(time.time() - t0)
            )

        if concentrated_frontal_area is not None:
            gamelib.util.debug_write("DEALING WITH CONCENTRATED FRONTAL AREA")
            t0 = time.time()
            # Target that frontal area (row + left/right half)
            if self.spam_demolisher_line(game_state, concentrated_frontal_area):
                self.our_attacks[-1].attack_type = "DEMOLISHER LINE"
                gamelib.util.debug_write(
                    "TIME FOR DEMOLISHER LINE: " + str(time.time() - t0)
                )
                return

        if game_state.get_resource(1, 0) > 5:
            gamelib.util.debug_write("DEFAULTING TO DEMOLISHER INTERCEPTOR PAIRS")
            t0 = time.time()
            self.demolisher_interceptor_pairs(
                game_state, weakest_region_boundary, all_possible_paths, interceptors=2
            )
            gamelib.util.debug_write(
                "TIME TO PLACE DEM INT PAIRS: " + str(time.time() - t0)
            )
            self.our_attacks[-1].attack_type = "DEMOLISHER INTERCEPTOR"

        gamelib.util.debug_write("DEFENDING STRATEGICALLY WITH INTERCEPTORS")
        t0 = time.time()
        self.defend_strategically_with_interceptors(game_state)
        gamelib.util.debug_write(
            "DEFENDED STRATEGICALLY WITH INTERCEPTORS IN: " + str(time.time() - t0)
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
                # Path leads to our half of the arena
                endpoints.add(tuple(path[-1]))

        return list(endpoints)

    def resolve_existing_blocks(self, game_state: gamelib.GameState):
        """
        Removes any of our structures that resulted in self-destructs last turn
        @param game_state: Game State
        """

        for coord in self.our_self_destructs:
            if coord[1] > 12:
                # Don't remove front-line defenses
                continue

            left = self.our_defense.grid_unit[coord[0] - 1, coord[1]]
            right = self.our_defense.grid_unit[coord[0] + 1, coord[1]]
            if left is not None:
                game_state.attempt_remove(locations=[left.x, left.y])
            if right is not None:
                game_state.attempt_remove(locations=[right.x, right.y])

        # Reset our self_destructs
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
        if game_state.game_map[demolisher_x_coord, demolisher_y_coord]:
            game_state.attempt_remove([demolisher_x_coord, demolisher_y_coord])
            return False
        gamelib.util.debug_write(
            "TRYING TO PLACE DEMOLISHERS AT: "
            + str([demolisher_x_coord, demolisher_y_coord])
        )
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
        return True

    def demolisher_interceptor_pairs(self, game_state, boundary, paths, interceptors=2):
        """
        Function to build a pair of demolishers/interceptors on the same coordinate
        @param game_state: Game State
        @param boundary: Boundary of the region we want to enter
        @param paths: all possible paths to consider
        @param interceptors: quantity of interceptors to demolishers
        """

        pairs = int(game_state.get_resource(1, 0) / (3 + interceptors))
        if pairs < 1:
            return
        gamelib.util.debug_write("CALCULATING LEAST DAMAGE PATH")
        t0 = time.time()
        loc = self.spawn_units_least_damage_path(
            game_state, boundary, paths, "DEMOLISHER", pairs
        )
        gamelib.util.debug_write("CALCULATED IN: " + str(time.time() - t0))
        if loc is None:
            return
        spawned = game_state.attempt_spawn(
            self.UNIT_ENUM_MAP["INTERCEPTOR"], locations=loc, num=(2 * pairs)
        )
        self.our_attacks[-1].total_cost += spawned

    def spawn_units_least_damage_path(
        self,
        game_state: GameState,
        region_boundary,
        possible_paths,
        unit_type: str,
        num: int,
    ):
        """
        Finds best location to spawn units and spawns them
        @param game_state: Game State
        @param region_boundary: boundary of the region we want
        @param possible_paths: all the paths to consider
        @param unit_type: unit type from self.UNIT_ENUM_MAP
        @param num: number of units
        @return: Best location to spawn (none if none exist)
        """
        if num < 1:
            return None
        # From all possible paths, find the one with least theoretical damage to our units
        viable_paths = find_paths_through_coordinates(
            paths=possible_paths, desired_coordinates=region_boundary
        )
        best_path, dmg = self.least_damage_path(game_state, viable_paths)

        if best_path is not None:
            # places interceptors on best possible location
            spawned = game_state.attempt_spawn(
                self.UNIT_ENUM_MAP[unit_type], locations=best_path[0], num=num
            )
            if spawned != 0:
                if unit_type == "DEMOLISHER":
                    self.our_attacks[-1].total_cost += 3 * spawned
                else:
                    self.our_attacks[-1].total_cost += spawned
            return best_path[0]
        else:
            None

    def least_damage_path(
        self, game_state: gamelib.GameState, paths: list
    ) -> (list, int):
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
                least_damage = damage

        return best_path, least_damage

    #####################################################################
    ########## HARD-CODED FUNCTIONS FOR THE FIRST FEW ROUNDS ############
    #####################################################################

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


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
