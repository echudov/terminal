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
        starting_location: (int, int) or [[int]],
        length: int,
        right: bool = True,
        ignore_boundaries: bool = True,
    ) -> int:
        """
        Used for placing a horizontal line of walls
        @param game_state: GameState object containing current gamestate info
        @param starting_location: (x, y) or [[x, y]]
        @param length: duh
        @param right: whether the wall goes right or left of the starting location
        @param ignore_boundaries: whether to care about boundaries
        @return: num_walls: The number of walls actually built
        """

        if not game_state.map.in_arena_bounds(location=starting_location):
            debug_write(
                "Attempted to build wall at "
                + starting_location
                + " but starts out of bounds"
            )
            return

        if game_state.number_affordable(game_state.WALL) < length:
            debug_write(
                "Attempted to build wall at "
                + starting_location
                + " but wall is too expensive"
            )
            return

        built = 0  # To return

        if right:
            # Adjust location for edge (if adding length 3, want to check 3 locations, not 4th)
            if ignore_boundaries or game_state.map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] + length - 1)
            ):
                built = game_state.attempt_spawn(
                    game_state.WALL,
                    [
                        [starting_location[0], starting_location[1] + i]
                        for i in range(length)
                    ],
                )
            else:
                debug_write(
                    "Attempted to build wall at "
                    + starting_location
                    + " but wall goes out of bounds"
                )

        if not right:
            # Adjust location for edge (if adding length 3, want to check 3 locations, not "-1th")
            if ignore_boundaries or game_state.map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] - length + 1)
            ):
                built = game_state.attempt_spawn(
                    game_state.WALL,
                    [
                        [starting_location[0], starting_location[1] - i]
                        for i in range(length)
                    ],
                )
            else:
                debug_write(
                    "Attempted to build wall at "
                    + starting_location
                    + " but wall goes out of bounds"
                )

        return built

    def simulate_wall_line(
        self,
        game_map: GameMap,
        starting_location: (int, int) or [[int]],
        length: int,
        wall_id: int,
        right: bool = True,
        ignore_boundaries: bool = True,
    ):
        """
        Meant only for simulating future states.
        Use build_h_wall_line_game for regular wall placement
        @param game_map: GameMap object containg map info
        @param starting_location: location where to first place the wall
        @param length: length of the wall
        @param wall_id: The type/id of the wall, constant provided in algo_strategy.py
        @param right: whether the wall goes right or left of the starting location
        @param ignore_boundaries: whether to care about boundaries
        @return: nothing
        """

        if not game_map.in_arena_bounds(location=starting_location):
            debug_write(
                "Attempted to build wall at "
                + starting_location
                + " but wall starts out of bounds"
            )
            return

        if right:
            # Adjust location for edge (if adding length 3, want to check 3 locations, not 4th)
            if ignore_boundaries or game_map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] + length - 1)
            ):
                for loc in [
                    [starting_location[0], starting_location[1] + i]
                    for i in range(length)
                ]:
                    if not game_map[loc[0], loc[1]]:
                        game_map.add_unit(wall_id, loc)
            else:
                debug_write(
                    "Attempted to build wall at "
                    + starting_location
                    + " but wall goes out of bounds"
                )

        if not right:
            # Adjust location for edge (if adding length 3, want to check 3 locations, not "-1th")
            if ignore_boundaries or game_map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] - length + 1)
            ):
                for loc in [
                    [starting_location[0], starting_location[1] - i]
                    for i in range(length)
                ]:
                    if not game_map[loc[0], loc[1]]:
                        game_map.add_unit(wall_id, loc)
            else:
                debug_write(
                    "Attempted to build wall at "
                    + starting_location
                    + " but wall goes out of bounds"
                )


class DefensiveTurretWallStrat:
    """Contains builder/simulator for a turret paired with 1 or more walls"""

    def build_turret_wall_pair(
        self,
        game_state: GameState,
        turret_location: (int, int) or [[int]],
        sp_available: int,
        above: bool = True,
        left: bool = False,
        right: bool = False,
        upgrade_wall: bool = False,
        upgrade_turret: bool = False,
    ) -> int:
        """Builds a turret/wall pair at the given location and the wall(s) at the given bool offset(s).

        Args:
            game_state (GameState): The current game state object
            turret_location ((int, int) or [[int]]): The turret's location
            sp_available (int): The amount of SP left
            above (bool): Whether to build a wall above the turret
            left (bool): Whether to build a wall left of the turret
            right (bool): Whether to build a wall right of the turret
            upgrade_wall: Whether to upgrade the wall
            upgrade_turret: Whether to upgrade the turret

        Returns:
            built (int): Number of structures built (1 wall & 1 turret) = 2
        """

        if not game_state.map.in_arena_bounds(turret_location):
            debug_write(
                "Attempted to build turret at "
                + turret_location
                + " but coordinate is out of bounds"
            )
            return 0

        built = 0  # To return

        wall_offsets = []
        if above:
            wall_offsets.append([0, 1])
        if left:
            wall_offsets.append([-1, 0])
        if right:
            wall_offsets.append([1, 0])

        total_cost = game_state.type_cost(game_state.TURRET)[0] + (
            game_state.type_cost(game_state.WALL)[0] * len(wall_offsets)
        )
        can_build_turret = not game_state.contains_stationary_unit(
            location=turret_location
        )

        if total_cost < game_state.get_resource(game_state.SP) and can_build_turret:
            game_state.attempt_spawn(
                game_state.TURRET, turret_location
            )  # Build the turret
            built += 1

            # Build the wall(s)
            for wo in wall_offsets:
                coord = [
                    wo[0] + turret_location[0],
                    wo[1] + turret_location[1],
                ]
                game_state.attempt_spawn(game_state.WALL, coord)
                built += 1

            return built
        else:
            return 0

    def simulate_turret_wall_pair(
        self,
        game_map: GameMap,
        turret_location: (int, int) or [[int]],
        turret_id: int,
        wall_id: int,
        above: bool = True,
        left: bool = False,
        right: bool = False,
        upgrade_wall: bool = False,
        upgrade_turret: bool = False,
    ):
        """Meant only for simulating future states.

        Args:
            game_state (GameState): The current game state object
            turret_location ((int, int) or [[int]]): The turret's location
            sp_available (int): The amount of SP left
            above (bool): Whether to build a wall above the turret
            left (bool): Whether to build a wall left of the turret
            right (bool): Whether to build a wall right of the turret
            upgrade_wall: Whether to upgrade the wall
            upgrade_turret: Whether to upgrade the turret
        """

        if not game_map.in_arena_bounds(turret_location):
            debug_write(
                "Attempted to build turret at "
                + turret_location
                + " but coordinate is out of bounds"
            )
            return

        wall_offsets = []
        if above:
            wall_offsets.append([0, 1])
        if left:
            wall_offsets.append([-1, 0])
        if right:
            wall_offsets.append([1, 0])

        if not game_map[turret_location[0], turret_location[1]]:
            game_map.add_unit(turret_id, turret_location)
        else:
            return

        for wo in wall_offsets:
            coord = [
                wo[0] + turret_location[0],
                wo[1] + turret_location[1],
            ]
            if not game_map[coord[0], coord[1]]:
                game_map.add_unit(wall_id, [coord[0], coord[1]])
