"""This file contains functions to return meta-info"""

from gamelib.game_state import GameState
from gamelib.game_map import GameMap
from gamelib.unit import GameUnit

from gamelib.util import debug_write


def are_losing(game_state: GameState) -> bool:
    """Returns whether or not we are losing. Function of health.

    Args:
        game_state (GameState): The current game state object

    Returns:
        losing (bool): Whether we are losing
    """

    return game_state.my_health >= game_state.enemy_health


def health_differential(game_state: GameState) -> int:
    """Returns difference between our and opponent's health. If diff < 0, we are losing.

    Args:
        game_state (GameState): The current game state object

    Returns:
        differential (int): The health differential between us and our opponent
    """

    return game_state.my_health - game_state.enemy_health


def resource_differential(game_state: GameState, resource_type: str) -> int:
    """Returns difference between our and opponent's resources of the given type (MP / SP).
    If diff < 0, we have fewer.

    Args:
        game_state (GameState): The current game state object
        resource_type (str): Either "MP" or "SP"

    Returns:
        differential (int): The differential between our and our opponent's given resource
    """

    if resource_type == "MP":
        return game_state.get_resource(1, 0) - game_state.get_resource(1, 1)
    else:
        return game_state.get_resource(0, 0) - game_state.get_resource(0, 1)


def get_structure_objects(
    game_state: GameState,
    unit_enum_map: dict,
    desired_structure_type: str = None,
    player: int = None,
) -> [GameUnit]:
    """Returns a list of all GameUnit structures (as objects). Optionally, specify the type of structure and/or player.

    Args:
        game_state (GameState): The current game state object
        unit_enum_map (dict): Maps NAME to unit enum
        desired_structure_type (OPTIONAL) (str): If given, only return this type of structure
        player (OPTIONAL) (int): If given, only return the structures owned by this player (0 is us, 1 is opponent)

    Returns:
        structures_list (List): List of all our structures (or of the given type)
    """

    board_map = game_state.game_map

    our_structures = []

    # Iterate over board and add to list if our unit
    for x in range(board_map.ARENA_SIZE):
        for y in range(board_map.ARENA_SIZE):
            units = board_map[x, y]
            if not units:
                continue

            # Only can have 1 structure on a tile
            unit = units[0]

            if player is not None:
                # Desired specific player
                if unit.player_index != player:
                    continue  # Not the desired player's

            if desired_structure_type is None:
                # Add all types to list
                if (
                    unit.unit_type == unit_enum_map["TURRET"]
                    or unit.unit_type == unit_enum_map["WALL"]
                    or unit.unit_type == unit_enum_map["FACTORY"]
                ):
                    our_structures.append(unit)
            else:
                # Add only given type to list
                if unit.unit_type == desired_structure_type:
                    our_structures.append(unit)

    return our_structures


def get_structure_dict(game_state: GameState, unit_enum_map: dict, player: int) -> dict:
    """Returns a dict mapping structure type (name as str) to its list for the given player.

    Args:
        game_state (GameState): The current game state object
        unit_enum_map (dict): Maps NAME to unit enum
        player (int): Either 0 (Us) or 1 (Enemy)

    Returns:
        structures_map (dict): Maps structure type as str to their list
    """

    factories = get_structure_objects(game_state, unit_enum_map["FACTORY"], player=player)
    turrets = get_structure_objects(game_state, unit_enum_map["TURRET"], player=player)
    walls = get_structure_objects(game_state, unit_enum_map["WALL"], player=player)

    # Construct and return dict
    unit_mappings = {
        unit_enum_map["FACTORY"]: factories,
        unit_enum_map["TURRET"]: turrets,
        unit_enum_map["WALL"]: walls,
    }

    return unit_mappings


def compute_factory_impact_differential(game_state: GameState, unit_enum_map: dict) -> (int, int):
    """Computes the factory impact differential between us and our opponent.
    This is the MP/SP production difference per turn as of this game state.
    If diff < 0, we are producing less of that resource type.

    Args:
        game_state: (GameState): The current game state object
        unit_enum_map (dict): Maps NAME to unit enum

    Returns:
        factory_impact_diff (int, int): Tuple (MP-Diff, SP-Diff)
    """

    mp_diff = 0
    sp_diff = 0

    factories = get_structure_objects(game_state, unit_enum_map["FACTORY"])
    for factory in factories:
        if factory.player_index == 0:
            # Ours
            if factory.upgraded:
                sp_diff += 3
                mp_diff += 1
            else:
                sp_diff += 1
                mp_diff += 1
        else:
            # Opponent's
            if factory.upgraded:
                sp_diff -= 3
                mp_diff -= 1
            else:
                sp_diff -= 1
                mp_diff -= 1

    return (mp_diff, sp_diff)
