"""This file contains functions to build/simulate offensive mechanisms/strategies"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from defensive_building_functions import DefensiveWallStrat

from gamelib.util import debug_write


class OffensiveInterceptorSpam:
    """Contains builder/simulator for intercepter spam attack strategy"""

    def build_interceptor_spam_multiple_locs(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        num_interceptors: int,
        locations: [(int, int)] or [[[int]]],
    ) -> int:
        """Builds X Interceptors at EACH of the MULTIPLE given locations (stacked)

        Args:
            game_state (GameState): The current GameState object
            unit_enum_map (dict): Maps NAME to unit enum
            num_interceptors (int): How many interceptors
            locations [(int, int)] or [[[int]]]: The coordinates to place them at

        Returns:
            built (int): Number of Interceptors actually successfully placed
        """

        built = 0  # To return

        for loc in locations:
            built += self.build_interceptor_spam_single_loc(
                game_state, unit_enum_map, num_interceptors, loc
            )

        return built

    def build_interceptor_spam_single_loc(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        num_interceptors: int,
        location: (int, int) or [[int]],
    ) -> int:
        """Builds X Interceptors at the given location (stacked)

        Args:
            game_state (GameState): The current GameState object
            unit_enum_map (dict): Maps NAME to unit enum
            num_interceptors (int): How many interceptors
            location (int, int) or [int]: The (x, y) or [x, y] coordinate to place them at

        Returns:
            built (int): Number of Interceptors actually successfully placed
        """

        built = 0  # To return

        for _ in range(num_interceptors):
            if self._build_interceptor_helper(game_state, unit_enum_map, location):
                built += 1

        return built

    def _build_interceptor_helper(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        location: (int, int) or [[int]],
    ) -> bool:
        """Private helper to place an interceptor at a given location

        Args:
            game_state (GameState): The current GameState object
            unit_enum_map (dict): Maps NAME to unit enum
            location (int, int) or [int]: The (x, y) or [x, y] coordinates to place it at

        Returns:
            is_successful (bool): Whether the interceptor was able to be placed
        """

        if not game_state.can_spawn(unit_enum_map["INTERCEPTOR"], location):
            return False

        built = game_state.attempt_spawn(unit_enum_map["INTERCEPTOR"], location)

        return True if built == 1 else False


class OffensiveDemolisherLine:
    """Contains builder/simulator for Demolisher behind horizontal wall line strat"""

    def build_demolisher_line(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        num_demolishers: int,
        location: (int, int) or [[int]],
    ) -> bool:
        """Builds a line of walls starting at the given location and stacked demolishers 1 tile back

        Args:
            game_state (GameState): The current GameState object
            unit_enum_map (dict): Maps NAME to unit enum
            num_demolishers (int): How many demolishers
            location (int, int) or [int]: The (x, y) or [x, y] coordinate to place them at

        Returns:
            bool (int): Whether this strategy was successfully executed
        """

        # Build a full line towards right of location (might overflow but fine)
        wall_num = DefensiveWallStrat().build_h_wall_line(
            game_state, unit_enum_map, location, game_state.ARENA_SIZE, right=True
        )

        # Build demolishers 1 tile behind
        dem_y = location[1] - 1
        dem_x = 14 + dem_y  # Start from the right-most possible place for this row
        while not game_state.can_spawn(unit_enum_map["DEMOLISHER"], [dem_x, dem_y]):
            dem_x -= 1  # Find a suitable place to stack (iteratively go left)

        dem_num = 0
        for _ in range(game_state.number_affordable(unit_enum_map["DEMOLISHER"])):
            dem_num += game_state.attempt_spawn(
                unit_enum_map["DEMOLISHER"], [dem_x, dem_y]
            )

        # TODO - Delete walls that allow us to enter regions

        if wall_num == 0 or dem_num == 0:
            return False

        return True
