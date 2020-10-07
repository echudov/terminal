import gamelib
from gamelib import util

def build_h_wall_line_game(game_state, starting_location, length, right=True, ignore_boundaries=True):
    """
    Used for placing a horizontal line of walls
    @param game_state: GameState object containing current gamestate info
    @param starting_location: duh
    @param length: duh
    @param right: whether the wall goes right or left of the starting location
    @param ignore_boundaries: whether to care about boundaries
    @return: nothing
    """
    if not game_state.map.in_arena_bounds(location=starting_location):
        util.debug_write("Attempted to build wall at " + starting_location + " but starts out of bounds")
        return
    if game_state.number_affordable(game_state.WALL) < length:
        util.debug_write("Attempted to build wall at " + starting_location + " but wall is too expensive")
    if right:
        if ignore_boundaries or game_state.map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] + length - 1)):
            game_state.attempt_spawn(game_state.WALL, [[starting_location[0], starting_location[1] + i] for i in range(length)])
        else:
            util.debug_write("Attempted to build wall at " + starting_location + " but wall goes out of bounds")
    if not right:
        if ignore_boundaries or game_state.map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] - length + 1)):
            game_state.attempt_spawn(game_state.WALL,
                                     [[starting_location[0], starting_location[1] - i] for i in range(length)])
        else:
            util.debug_write("Attempted to build wall at " + starting_location + " but wall goes out of bounds")



def build_h_wall_line_map(map, starting_location, length, wall_id, right=True, ignore_boundaries=True):
    """
    Meant only for simulating future states.
    Use build_h_wall_line_game for regular wall placement
    @param map: GameMap object containg map info
    @param starting_location: location where to first place the wall
    @param length: length of the wall
    @param wall_id: The type/id of the wall, constant provided in algo_strategy.py
    @param right: whether the wall goes right or left of the starting location
    @param ignore_boundaries: whether to care about boundaries
    @return: nothing
    """
    if not map.in_arena_bounds(location=starting_location):
        util.debug_write("Attempted to build wall at " + starting_location + " but wall starts out of bounds")
        return
    if right:
        if ignore_boundaries or map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] + length - 1)):
            for loc in [[starting_location[0], starting_location[1] + i] for i in range(length)]:
                if not map[loc[0], loc[1]]:
                    map.add_unit(wall_id, loc)
        else:
            util.debug_write("Attempted to build wall at " + starting_location + " but wall goes out of bounds")
    if not right:
        if ignore_boundaries or map.in_arena_bounds(
                location=(starting_location[0], starting_location[1] - length + 1)):
            for loc in [[starting_location[0], starting_location[1] - i] for i in range(length)]:
                if not map[loc[0], loc[1]]:
                    map.add_unit(wall_id, loc)
        else:
            util.debug_write("Attempted to build wall at " + starting_location + " but wall goes out of bounds")


def build_turret_wall_pair_game(game_state, turret_location, spent=0, above=True, left=False, right=False, upgrade_wall=False, upgrade_turret=False):
    cost = spent
    if not game_state.map.in_arena_bounds(turret_location):
        util.debug_write("Attempted to build turret at " + turret_location + " but coordinate is out of bounds")
    wall_offsets = []
    if above:
        wall_offsets.append([0, 1])
    if left:
        wall_offsets.append([-1, 0])
    if right:
        wall_offsets.append([1, 0])
    if cost + game_state.cost(game_state.TURRET)[0] < game_state.SP and not game_state.contains_stationary_unit(location=turret_location):
        game_state.attempt_spawn(game_state.TURRET, turret_location)
        cost += game_state.type_cost(game_state.TURRET)[0]
    else:
        return
    for wo in wall_offsets:
        coord = [wall_offsets[0] + turret_location[0], wall_offsets[1] + turret_location[1]]
        if cost + game_state.type_cost(game_state.WALL)[0] < game_state.SP:
            game_state.attempt_spawn(game_state.WALL)
            cost += game_state.type_cost(game_state.WALL)[0]

def build_turret_wall_pair_map(map, turret_location, turret_id, wall_id, above=True, left=False, right=False, upgrade_wall=False, upgrade_turret=False):
    if not map.in_arena_bounds(turret_location):
        util.debug_write("Attempted to build turret at " + turret_location + " but coordinate is out of bounds")
    wall_offsets = []
    if above:
        wall_offsets.append([0, 1])
    if left:
        wall_offsets.append([-1, 0])
    if right:
        wall_offsets.append([1, 0])
    if not map[turret_location[0], turret_location[1]]:
        map.add_unit(turret_id, turret_location)
    else:
        return
    for wo in wall_offsets:
        coord = [wall_offsets[0] + turret_location[0], wall_offsets[1] + turret_location[1]]
        if not map[coord[0], coord[1]]:
            map.add_unit(wall_id)
