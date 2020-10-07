"""This file contains functions to return meta-info"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from gamelib.util import debug_write


def are_losing(game_state: GameState) -> bool:
    """Returns whether or not we are losing. Function of health."""

    return game_state.my_health >= game_state.enemy_health


def health_differential(game_state: GameState) -> int:
    """Returns difference between our and opponent's health. If diff < 0, we are losing."""

    return game_state.my_health - game_state.enemy_health


def resource_differential(game_state: GameState, resource_type: str) -> int:
    """Returns difference between our and opponent's resources of the given type (MP / SP).
    If diff < 0, we have fewer.
    """

    if resource_type == "MP":
        return game_state.get_resource(1, 0) - game_state.get_resource(1, 1)
    else:
        return game_state.get_resource(0, 0) - game_state.get_resource(0, 1)


def get_structure_nums(game_state: GameState, player: int) -> dict:
    """Returns a dict mapping structure type (name as str) to its count for the given player.
    Player = 0 -> Us
    Player = 1 -> Enemy
    """

    board_map = game_state.game_map

    turret_count = 0
    wall_count = 0
    factory_count = 0

    # Iterate over board and counts player's units
    for x in range(board_map.ARENA_SIZE):
        for y in range(board_map.ARENA_SIZE):
            units = board_map[x, y]
            if len(units) == 0:
                continue

            # Only can have 1 structure on a tile
            unit = units[0]
            if unit.player_index != player:
                continue

            # Count
            if unit.unit_type == "TURRET":
                turret_count += 1
            elif unit.unit_type == "WALL":
                wall_count += 1
            elif unit.unit_type == "FACTORY":
                factory_count += 1

    # Construct and return dict
    unit_mappings = {
        "TURRET": turret_count,
        "WALL": wall_count,
        "FACTORY": factory_count,
    }

    return unit_mappings


def get_structure_objects(
    game_state: GameState, desired_unit_type: str = None
) -> [GameUnit]:
    """Returns a list of all our GameUnit structures (for example to upgrade them).
    Optionally, specify the type of structure.
    """

    board_map = game_state.game_map

    our_structures = []

    # Iterate over board and add to list if our unit
    for x in range(board_map.ARENA_SIZE):
        for y in range(board_map.ARENA_SIZE):
            units = board_map[x, y]
            if len(units) == 0:
                continue

            # Only can have 1 structure on a tile
            unit = units[0]
            if unit.player_index != 0:
                continue  # Not ours

            if desired_unit_type is None:
                # Add all types to list
                if (
                    unit.unit_type == "TURRET"
                    or unit.unit_type == "WALL"
                    or unit.unit_type == "FACTORY"
                ):
                    our_structures.append(unit)
            else:
                # Add only given type to list
                if unit.unit_type == desired_unit_type:
                    our_structures.append(unit)

    return our_structures
