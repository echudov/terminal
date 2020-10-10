"""This file contains functions to help determing WHERE to place a new unit"""

from collections import Counter

from gamelib.game_state import GameState
from gamelib.game_map import GameMap

# CONSTANTS

# Fraction of turrets in first 3 rows to be considered "concentrated"
MIN_FRONT_TURRET_DENSITY = 0.6
FACTORY_ROW_MAX = 6


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
    for row in range(1, FACTORY_ROW_MAX):
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


def demolisher_location_helper(
    game_state: GameState, unit_enum_map: dict, enemy_units: dict
) -> (int, bool):
    """Returns a location to stack demolishers to inflict the most damage on the enemy's frontline structures. Returns None if front 3 rows not concentrated.

    Args:
        game_state (GameState): The current game state object
        unit_enum_map (dict): The unit enum dict
        enemy_units (dict): Dict of enemy's units mapping type to set of those Units

    Returns:
        location (int, bool): Y-coord and True if left half more concentrated, else False. Or None if not concentrated
    """

    # Find the row (y-coord) with highest number of turrets
    their_turrets = enemy_units[unit_enum_map["TURRET"]]
    if len(their_turrets) == 0:
        return None

    y_coords = Counter()  # Maps point y-coord to count

    for turret in their_turrets:
        if turret.y <= 16:
            # Only count if within front 3 rows
            y_coords.update({turret.y: 1})

    if sum(y_coords.values()) < MIN_FRONT_TURRET_DENSITY * len(their_turrets):
        return None  # Their front 3 rows are not that concentrated

    # Returns a list of tuples (elem, count)
    highest_concentration = y_coords.most_common(1)[0]
    highest_concentration_y = highest_concentration[0]

    # Find the left/right half with highest concentration
    left_right_half_counter = Counter()
    their_turrets_x_coord = [
        turret.x for turret in their_turrets if turret.y == highest_concentration_y
    ]

    # Start at THEIR most concentrated row
    x_left_bound = 13 - highest_concentration_y
    x_right_bound = 14 + highest_concentration_y
    for x in range(x_left_bound, x_right_bound + 1):
        # Go through every x in the most concentrated row (if turret, count)

        if x <= 13 and x in their_turrets_x_coord:
            left_right_half_counter.update({"LEFT": 1})
        elif x >= 14 and x in their_turrets_x_coord:
            left_right_half_counter.update({"RIGHT": 1})

    most_conc_half = left_right_half_counter.most_common(1)[0]
    left_half_more_conc = True if most_conc_half == "LEFT" else False

    return highest_concentration_y, left_half_more_conc


def coordinate_path_location_helper(
    game_state: GameState, desired_coordinates: [[int]]
):
    """Returns a VALID spawn location such that a mobile unit will pass at least once through the given coordinates. Useful for routing units through a specific region.
    Returns None if impossible.

    Args:
        game_state: The current GameState object
        desired_coordinates: Try to route the unit through at least one of these coordinates

    Returns:
        spawn_location (int, int): Location to spawn, or None
    """

    # Find where to place mobile unit to pass through 1 of those coords
    loc = None

    # Iterate through all possible spawn locations
    g_map = game_state.game_map
    possible_spawn_locs = g_map.get_edge_locations(
        g_map.BOTTOM_LEFT
    ) + g_map.get_edge_locations(g_map.BOTTOM_RIGHT)
    for spawn_loc in possible_spawn_locs:
        path = game_state.find_path_to_edge(spawn_loc)

        # Starting point was blocked by stationary unit
        if path is None:
            continue

        # If final point is not on an edge, it's a self-destruct path
        final_point = path[-1]
        if final_point not in g_map.get_edge_locations(
            g_map.TOP_LEFT
        ) or final_point not in g_map.get_edge_locations(g_map.TOP_RIGHT):
            continue  # Self-destruct path

        # This is a valid path
        if any(path_coord in desired_coordinates for path_coord in path):
            # This path goes through the desired coordinates at least once
            loc = path[0]
            break

    return loc