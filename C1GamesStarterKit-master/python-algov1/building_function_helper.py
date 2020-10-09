"""This file contains functions to help determing WHERE to place a new unit"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap


def factory_location_helper(game_state: GameState) -> (int, int):
    """Returns a location to place 1 Factory at (as back as possible) or None if impossible

    Args:
        game_state (GameState): The current game state object

    Returns:
        location (int, int): Location to place as a Tuple or None
    """

    # Bottom at (13, 0) and (14, 0).
    # Start at (13, 1) and (14, 1) and work up (every +1y, have +2x)

    location = (13, 1)
    for row in range(1, 13):
        # Start at 1st row and go up to top of our half
        x_left_bound = 13 - row
        x_right_bound = 14 + row

        for x in range(x_left_bound + 1, x_right_bound):
            # Don't build at left or right edge (+1 offset)
            blocked = game_state.contains_stationary_unit((x, row))
            if not blocked:
                location = (x, row)

                return location

    return None
