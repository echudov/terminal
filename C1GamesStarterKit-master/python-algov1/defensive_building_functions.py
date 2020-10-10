"""This file contains functions to build/simulate defensive mechanisms/strategies"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from gamelib.util import debug_write


class DefensiveWallStrat:
    """Contains builder/simulator for a line of horizontal walls"""

    def build_h_wall_line(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        starting_location: (int, int) or [[int]],
        length: int,
        right: bool = True,
    ) -> int:
        """
        Used for placing a horizontal line of walls
        @param game_state: GameState object containing current gamestate info
        unit_enum_map (dict): Maps NAME to unit enum
        @param starting_location: (x, y) or [[x, y]]
        @param length: duh
        @param right: whether the wall goes right or left of the starting location
        @return: num_walls: The number of walls actually built
        """

        built = 0  # To return

        if right:
            locations = [
                [starting_location[0] + i, starting_location[1]] for i in range(length)
            ]

            for loc in locations:
                if not game_state.can_spawn(unit_enum_map["WALL"], loc):
                    continue

                built += game_state.attempt_spawn(unit_enum_map["WALL"], loc)

        if not right:
            locations = [
                [starting_location[0] - i, starting_location[1]] for i in range(length)
            ]

            for loc in locations:
                if not game_state.can_spawn(unit_enum_map["WALL"], loc):
                    continue

                built += game_state.attempt_spawn(unit_enum_map["WALL"], loc)

        return built

    def simulate_wall_line(
        self,
        game_map: GameMap,
        unit_enum_map: dict,
        starting_location: (int, int) or [[int]],
        length: int,
        right: bool = True,
    ):
        """
        Meant only for simulating future states.
        Use build_h_wall_line_game for regular wall placement
        @param game_map: GameMap object containg map info
        unit_enum_map (dict): Maps NAME to unit enum
        @param starting_location: location where to first place the wall
        @param length: length of the wall
        @param right: whether the wall goes right or left of the starting location
        @return: nothing
        """

        if right:
            locations = [
                [starting_location[0] + i, starting_location[1]] for i in range(length)
            ]

            for loc in locations:
                if not game_map[loc[0], loc[1]]:
                    game_map.add_unit(unit_enum_map["WALL"], loc)

        if not right:
            locations = [
                [starting_location[0] - i, starting_location[1]] for i in range(length)
            ]

            for loc in locations:
                if not game_map[loc[0], loc[1]]:
                    game_map.add_unit(unit_enum_map["WALL"], loc)


class DefensiveTurretWallStrat:
    """Contains builder/simulator for a turret paired with 1 or more walls"""

    def build_turret_wall_pair(
        self,
        game_state: GameState,
        unit_enum_map: dict,
        turret_location: (int, int) or [[int]],
        above: bool = True,
        left: bool = False,
        right: bool = False,
    ) -> int:
        """Builds a turret/wall pair at the given location and the wall(s) at the given bool offset(s).

        Args:
            game_state (GameState): The current game state object
            unit_enum_map (dict): Maps NAME to unit enum
            turret_location ((int, int) or [[int]]): The turret's location
            above (bool): Whether to build a wall above the turret
            left (bool): Whether to build a wall left of the turret
            right (bool): Whether to build a wall right of the turret

        Returns:
            built (int): Number of structures built (1 wall & 1 turret) = 2
        """

        built = 0  # To return

        wall_offsets = []
        if above:
            wall_offsets.append([0, 1])
        if left:
            wall_offsets.append([-1, 0])
        if right:
            wall_offsets.append([1, 0])

        if not game_state.can_spawn(unit_enum_map["TURRET"], turret_location):
            return built
        for wo in wall_offsets:
            if not game_state.can_spawn(
                unit_enum_map["WALL"],
                [wo[0] + turret_location[0], wo[1] + turret_location[1]],
            ):
                return built

        # Can build Turret and wall(s)

        built += game_state.attempt_spawn(unit_enum_map["TURRET"], turret_location)

        # Build the wall(s)
        for wo in wall_offsets:
            coord = [
                wo[0] + turret_location[0],
                wo[1] + turret_location[1],
            ]
            built += game_state.attempt_spawn(unit_enum_map["WALL"], coord)

        return built

    def simulate_turret_wall_pair(
        self,
        game_map: GameMap,
        unit_enum_map: dict,
        turret_location: (int, int) or [[int]],
        above: bool = True,
        left: bool = False,
        right: bool = False,
        upgrade_wall: bool = False,
        upgrade_turret: bool = False,
    ):
        """Meant only for simulating future states.

        Args:
            game_state (GameState): The current game state object
            unit_enum_map (dict): Maps NAME to unit enum
            turret_location ((int, int) or [[int]]): The turret's location
            sp_available (int): The amount of SP left
            above (bool): Whether to build a wall above the turret
            left (bool): Whether to build a wall left of the turret
            right (bool): Whether to build a wall right of the turret
            upgrade_wall: Whether to upgrade the wall
            upgrade_turret: Whether to upgrade the turret
        """

        wall_offsets = []
        if above:
            wall_offsets.append([0, 1])
        if left:
            wall_offsets.append([-1, 0])
        if right:
            wall_offsets.append([1, 0])

        if not game_map[turret_location[0], turret_location[1]]:
            game_map.add_unit(unit_enum_map["TURRET"], turret_location)
        else:
            return  # Either add both or none

        for wo in wall_offsets:
            coord = [
                wo[0] + turret_location[0],
                wo[1] + turret_location[1],
            ]
            if not game_map[coord[0], coord[1]]:
                game_map.add_unit(unit_enum_map["WALL"], [coord[0], coord[1]])
