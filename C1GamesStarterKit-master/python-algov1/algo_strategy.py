import gamelib
import random
import math
import warnings
from sys import maxsize
import json

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

from building_function_helper import factory_location_helper

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
    def __init__(self):
        super().__init__()
        # OUR INITIAL SETUP BELOW
        self.health_diff = 0
        self.scored_on_locations = []
        self.enemy_units = {}  # Same as above, fo
        # r opponent
        self.units = {}  # Dict mapping unit type to unit objects
        self.regions_attacked = {i : [] for i in range(6)}
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

        # Updating internal values of Defenses
        self.our_defense.update_defense(self.UNIT_ENUM_MAP, game_state)
        self.their_defense.update_defense(self.UNIT_ENUM_MAP, game_state)

        # Refresh units list
        self.units = get_structure_dict(game_state, self.UNIT_ENUM_MAP, player=0)
        self.enemy_units = get_structure_dict(game_state, self.UNIT_ENUM_MAP, player=1)

        # Factory Impact Differential
        (mp_diff, sp_diff) = compute_factory_impact_differential(
            game_state, self.UNIT_ENUM_MAP
        )
        if (mp_diff > 3 and sp_diff > 9) or self.health_diff < 5:
            # Already quite ahead in terms of factories OR losing and need to focus on defense
            self.resolve_factory_impact_diff(game_state, deprioritize=True)
        else:
            self.resolve_factory_impact_diff(game_state)

        # Build Reactive Defense
        self.build_reactive_defense(game_state, turn_state)

        # Perform moves
        self.choose_and_execute_strategy(game_state)  # Main entry point

        game_state.submit_turn()  # Must be called at the end

    #####################################################################
    ####################### OUR ALGO FUNCTIONS ##########################
    #####################################################################

    def resolve_factory_impact_diff(
        self, game_state: GameState, deprioritize: bool = False
    ) -> int:
        """Evaluated the current Factory Impact Differential and accordingly builds/upgrades factories.

        Args:
            game_state (GameState): The current GameState object
            deprioritize (bool): Whether we should deprioritize building/upgrading factories. If True, will build/upgrade maximum 1 factory

        Returns:
            num_improved (int): The number of factories built/upgraded
        """

        # At start of game, won't have any factories
        if FACTORY not in self.units:
            return

        # Factories we build should be a function of how many we can afford
        possible_factories = game_state.number_affordable(FACTORY)
        our_factories = self.units[FACTORY]

        # If can only build 1, do it:
        if possible_factories == 1 or deprioritize:
            # Prioritize upgrading over building
            for factory in our_factories:
                if not factory.upgraded:
                    num = game_state.attempt_upgrade((factory.x, factory.y))
                    if num != 0:
                        return

            # All factories already upgraded
            loc = factory_location_helper(game_state)
            num = game_state.attempt_spawn(FACTORY, loc)
        else:
            # Otherwise, build half of the max possible
            actual_factories = math.floor(possible_factories / 2)
            num = 0  # Don't allow to exceed actual_factories

            # Prioritize upgrading over building
            for factory in our_factories:
                if not factory.upgraded:
                    if num == actual_factories:
                        return

                    num += game_state.attempt_upgrade((factory.x, factory.y))

            # Upgraded all possible ones. Now build any possible remaining
            for _ in range(actual_factories - num):
                loc = factory_location_helper(game_state)
                num += game_state.attempt_spawn(FACTORY, loc)

            return

    def choose_and_execute_strategy(self, game_state: GameState):
        """Wrapper to choose and execute a strategy based on the game state.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO

        # For the first 3 turns, just get set up
        if game_state.turn_number < 3:
            self.starting_strategy(game_state)
            return

        # TODO Temp
        if (game_state.turn_number % 2) == 0:
            self.stall_with_interceptors(game_state)
        else:
            self.demolisher_line_strategy(game_state)

        # Choose a strategy (aggressive, medium, passive)
        aggressive = (game_state.turn_number % 2) == 0
        medium = (game_state.turn_number % 2) == 0
        passive = are_losing(game_state)

        # Execute it
        if aggressive:
            self.aggressive_strategy(game_state)
        elif medium:
            self.medium_strategy(game_state)
        elif passive:
            self.passive_strategy(game_state)

    def aggressive_strategy(self, game_state: GameState):
        """Executes the aggressive strategy.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO

        locs = [[20, 6], [6, 7]]

        OffensiveInterceptorSpam().build_interceptor_spam_multiple_locs(
            game_state,
            self.UNIT_ENUM_MAP,
            game_state.number_affordable(INTERCEPTOR),
            locs,
        )

    def medium_strategy(self, game_state: GameState):
        """Executes the medium strategy.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO

        DefensiveTurretWallStrat().build_turret_wall_pair(
            game_state,
            self.UNIT_ENUM_MAP,
            (13, 12),
            game_state.get_resource(SP),
            above=True,
            right=True,
        )

        OffensiveDemolisherLine().build_demolisher_line(
            game_state, self.UNIT_ENUM_MAP, 1, (5, 5)
        )

        locs = [[20, 6], [6, 7]]

        OffensiveInterceptorSpam().build_interceptor_spam_multiple_locs(
            game_state,
            self.UNIT_ENUM_MAP,
            game_state.number_affordable(INTERCEPTOR),
            locs,
        )

    def passive_strategy(self, game_state: GameState):
        """Executes the passive strategy.

        Args:
            game_state (GameState): The current GameState object
        """

        # TODO

        DefensiveWallStrat().build_h_wall_line(
            game_state, self.UNIT_ENUM_MAP, (0, 13), game_state.ARENA_SIZE, right=True
        )

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
        game_state.attempt_spawn(INTERCEPTOR, [9, 4], num=3)
        game_state.attempt_spawn(INTERCEPTOR, [16, 2], num=2)

    def second_round(self, game_state: GameState):
        """Hard-coded moves for the second turn. Check Miro for what this results in.

        Args:
            game_state (GameState): The current GameState object
        """

        # Place final turret
        game_state.attempt_spawn(TURRET, [16, 12])
        # Save rest of SP for next round to buy Factory

        # 6 Interceptors on defense
        game_state.attempt_spawn(INTERCEPTOR, [10, 3], num=3)
        game_state.attempt_spawn(INTERCEPTOR, [17, 3], num=3)

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
        game_state.attempt_spawn(INTERCEPTOR, [10, 3], num=3)
        game_state.attempt_spawn(INTERCEPTOR, [17, 3], num=3)

    #####################################################################
    ######## FUNCTIONS THEY HAVE GIVEN US AND MAY PROVE USEFUL ##########
    #####################################################################

    def build_reactive_defense(self, game_state: GameState, turn_state: str):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames
        as shown in the on_action_frame function
        """

        # TODO Check this!

        self.on_action_frame(turn_state)

        attacked_region = max(self.regions_attacked, key=self.regions_attacked.get)

        placement = self.regions[attacked_region].random_turret_placement(game_state)

        DefensiveTurretWallStrat().build_turret_wall_pair(game_state, self.UNIT_ENUM_MAP, placement, game_state.get_resource[0])

        for location in self.scored_on_locations:
            build_location = [location[0], location[1]]
            if game_state.can_spawn(TURRET, build_location):
                game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state: GameState):
        """
        Send out interceptors at random locations to defend our base from enemy moving units.
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(
            game_state.game_map.BOTTOM_LEFT
        ) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)

        # Remove locations that are blocked by our own structures
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(friendly_edges, game_state)

        # While we have remaining MP to spend lets send out interceptors randomly.
        while (
            game_state.get_resource(MP) >= game_state.type_cost(INTERCEPTOR)[MP]
            and len(deploy_locations) > 0
        ):
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]

            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def demolisher_line_strategy(self, game_state: GameState):
        """
        Build a line of the cheapest stationary unit so our demolisher can attack from long range.
        """

        # TODO Use if enemy has lots of structures near the top to clean out that part

        # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
        # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
        for x in range(27, 5, -1):
            if game_state.can_spawn(WALL, [x, 11]):
                game_state.attempt_spawn(WALL, [x, 11])

        # Now spawn demolishers next to the line
        game_state.attempt_spawn(
            DEMOLISHER, [24, 10], game_state.number_affordable(DEMOLISHER)
        )

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
            if path.length() < 4:
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

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, action_frame_game_state: str):
        """
        This is the action frame of the game. This function could be called
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """

        # Let's record at what position we get scored on
        state = json.loads(action_frame_game_state)
        events = state["events"]
        breaches = events["breach"]
        self_destructs = events["selfDestruct"]
        p2units = state["p2Units"]
        for unit_num in range(3, 6):
            unit_list = p2units[unit_num]
            for unit in unit_list:
                if unit[1] < 14:
                    region = self.our_defense.get_region([unit[0], unit[1]])
                    self.regions_attacked[region] += 1

        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write(
                    "All locations: {}".format(self.scored_on_locations)
                )


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
