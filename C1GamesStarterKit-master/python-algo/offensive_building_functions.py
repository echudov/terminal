"""This file contains functions to build/simulate offensive mechanisms/strategies"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from defensive_building_functions import DefensiveWallStrat

from gamelib.util import debug_write


class OffensiveInterceptorSpam:
    """Contains builder/simulator for intercepter spam attack strategy"""

    # TODO: Simulators for each below

    def build_interceptor_spam_multiple_locs(
        self,
        game_state: GameState,
        num_interceptors: int,
        locations: [(int, int)] or [[[int]]],
    ) -> int:
        """Builds X Interceptors at EACH of the MULTIPLE given locations (stacked)

        Args:
            game_state (GameState): The current GameState object
            num_interceptors (int): How many interceptors
            locations [(int, int)] or [[[int]]]: The coordinates to place them at

        Returns:
            built (int): Number of Interceptors actually successfully placed
        """

        built = 0  # To return

        for loc in locations:
            built += self.build_interceptor_spam_single_loc(
                game_state, num_interceptors, loc
            )

        return built

    def build_interceptor_spam_single_loc(
        self,
        game_state: GameState,
        num_interceptors: int,
        location: (int, int) or [[int]],
    ) -> int:
        """Builds X Interceptors at the given location (stacked)

        Args:
            game_state (GameState): The current GameState object
            num_interceptors (int): How many interceptors
            location (int, int) or [int]: The (x, y) or [x, y] coordinate to place them at

        Returns:
            built (int): Number of Interceptors actually successfully placed
        """

        built = 0  # To return

        for _ in range(num_interceptors):
            if self._build_interceptor_helper(game_state, location):
                built += 1

        return built

    def _build_interceptor_helper(
        self, game_state: GameState, location: (int, int) or [[int]]
    ) -> bool:
        """Private helper to place an interceptor at a given location

        Args:
            game_state (GameState): The current GameState object
            location (int, int) or [int]: The (x, y) or [x, y] coordinates to place it at

        Returns:
            is_successful (bool): Whether the interceptor was able to be placed
        """

        if not game_state.can_spawn(game_state.INTERCEPTOR, location):
            return False

        built = game_state.attempt_spawn(game_state.INTERCEPTOR, location)

        return True if built == 1 else False


class OffensiveDemolisherLine:
    """Contains builder/simulator for Demolisher behind horizontal wall line strat"""

    def build_demolisher_line(
        self,
        game_state: GameState,
        num_demolishers: int,
        location: (int, int) or [[int]],
    ) -> bool:
        """Builds a line of walls starting at the given location and evenly-spaced demolishers 1 tile back

        Args:
            game_state (GameState): The current GameState object
            num_demolishers (int): How many demolishers
            location (int, int) or [int]: The (x, y) or [x, y] coordinate to place them at

        Returns:
            bool (int): Whether this strategy was successfully executed
        """

        # Build a full line towards right of location (might overflow but fine)
        loc = [0, location[1]]  # Start at the beginning artificially
        wall_num = 0
        wall_num = DefensiveWallStrat().build_h_wall_line(
            game_state, loc, game_state.ARENA_SIZE
        )

        # Build demolishers 1 tile behind
        dem_loc = [0, loc[1] - 1]

        # TODO: This should be the actual number of horizontal tiles at this loc
        dem_loc_offset = (
            game_state.number_affordable(game_state.DEMOLISHER) / game_state.HALF_ARENA
        )
        num_locs = game_state.HALF_ARENA / dem_loc_offset
        num_dem_per_loc = num_demolishers / num_locs

        dem_num = 0
        for i in range(num_locs):
            x = dem_loc[0] + (i * dem_loc_offset)
            y = dem_loc[1]

            if not game_state.can_spawn(game_state.DEMOLISHER, [x, y], num_dem_per_loc):
                return False

            dem_num += game_state.attempt_spawn(
                game_state.DEMOLISHER, [x, y], num_dem_per_loc
            )

        if wall_num == 0 or dem_num == 0:
            return False

        return True

    # def demolisher_line_strategy(self, game_state):
    #     """
    #     Build a line of the cheapest stationary unit so our demolisher can attack from long range.
    #     """
    #     # First let's figure out the cheapest unit
    #     # We could just check the game rules, but this demonstrates how to use the GameUnit class
    #     stationary_units = [WALL, TURRET, FACTORY]
    #     cheapest_unit = WALL
    #     for unit in stationary_units:
    #         unit_class = gamelib.GameUnit(unit, game_state.config)
    #         if (
    #             unit_class.cost[game_state.MP]
    #             < gamelib.GameUnit(cheapest_unit, game_state.config).cost[game_state.MP]
    #         ):
    #             cheapest_unit = unit

    #     # Now let's build out a line of stationary units. This will prevent our demolisher from running into the enemy base.
    #     # Instead they will stay at the perfect distance to attack the front two rows of the enemy base.
    #     for x in range(27, 5, -1):
    #         game_state.attempt_spawn(cheapest_unit, [x, 11])

    #     # Now spawn demolishers next to the line
    #     # By asking attempt_spawn to spawn 1000 units, it will essentially spawn as many as we have resources for
    #     game_state.attempt_spawn(DEMOLISHER, [24, 10], 1000)