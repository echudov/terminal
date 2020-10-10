import gamelib
import numpy as np
import random
import time
import math
import queue


class Region:
    # CONSTANTS

    MIN_TURN_UPGRADE = 8  # Only start upgrading after this turn
    MAX_TURRETS = 5

    def __init__(
        self,
        unit_enum_map: dict,
        vertices: list,
        player_id: int,
        incoming_edges: list,
        outgoing_edges: list,
        breach_edges: list,
        map: gamelib.GameMap,
        damage_regions=None,
    ) -> object:
        """
        Initializes a general region to keep track of units.  Should only be initialized once at the beginning of the game since it's expensive to calculate.
        unit_enum_map (dict): Maps NAME to unit enum
        @type map: gamelib.GameMap
        @param vertices: list of tuples containing (x, y) coordinates for the region's vertices
        @param player_id: player_id of region (0 - us, 1 - opponent)
        @param incoming_edges: list of vertex pairs representing the edges that opponents can enter through
        @param outgoing_edges: list of vertex pairs representing the edges that opponents can exit out of
        @param breach_edges: list of vertex pairs representing the edge(s) that opponents can damage us through
        @param damage_regions: Numpy array representing the damage units take at a specific coordinate in the region
        """
        self.vertices = vertices
        self.coordinates = set()
        self.player_id = player_id
        self.incoming_edges = incoming_edges
        self.outgoing_edges = outgoing_edges
        self.breach_edges = breach_edges
        self.edges = set(incoming_edges + outgoing_edges + breach_edges)

        # dictionary containing unit types in region

        # region bounds
        self.xbounds = min(v[0] for v in self.vertices), max(
            v[0] for v in self.vertices
        )
        self.xwidth = self.xbounds[1] - self.xbounds[0] + 1

        self.ybounds = min(v[1] for v in self.vertices), max(
            v[1] for v in self.vertices
        )
        self.ywidth = self.ybounds[1] - self.ybounds[0] + 1

        # each value in the grid looks like (int, units)
        # the first # is the type of coordinate:
        # -1: invalid coordinate, 0: edge, 1: inside
        # the second is the stationary unit contained in the cell
        # the [] operator accesses values from this grid
        self.grid_type = np.full(
            shape=(self.xwidth, self.ywidth), fill_value=-1, dtype=object
        )
        self.grid_unit = np.full(
            shape=(self.xwidth, self.ywidth), fill_value=None, dtype=gamelib.GameUnit
        )

        # boolean to determine if we need to recalculate our paths from edge to edge based on new buildings being built
        self.recalculate_paths = True
        self.path_dict = {}
        self.all_boundaries = set()
        for i in range(len(vertices)):
            for coord in self.edge_coordinates(
                [vertices[i], vertices[(i + 1) % len(vertices)]]
            ):
                self.all_boundaries.add(coord)

        for y in range(self.ybounds[0], self.ybounds[1] + 1):
            for x in range(self.xbounds[0], self.xbounds[1] + 1):
                if (x, y) in self.all_boundaries:
                    self.grid_type[self.zero_coordinates((x, y))] = 0
                    continue
                if self.point_inside_polygon(x, y, vertices):
                    self.coordinates.add((x, y))
                    self.grid_type[self.zero_coordinates((x, y))] = 1

        self.tile_count = len(self.coordinates)
        # assigns edge coordinates to zero

        self.coordinates = self.coordinates.union(self.all_boundaries)
        for coord in self.all_boundaries:
            self[coord][0] = 0

        # calculates the damage regions
        self.damage_regions = np.full(shape=(self.xwidth, self.ywidth), fill_value=0)

        self.units = {
            unit_enum_map["TURRET"]: [],
            unit_enum_map["FACTORY"]: [],
            unit_enum_map["WALL"]: [],
        }
        self.calculate_local_damage_regions(unit_enum_map, map)

        # to access you must shift the coordinate with zero_coordinates

    def __getitem__(self, key: list or tuple) -> (int, gamelib.GameUnit):
        """
        Overloads [] operator to get tuple from self.grid
        @param key: tuple representing (x, y) coordinate on the regular map
        @return: Tuple representing information about the region grid at the coordinate
        """

        return [
            self.grid_type[self.zero_coordinates(key)],
            self.grid_unit[self.zero_coordinates(key)],
        ]

    def __setitem__(self, key: list or tuple, value: (int, gamelib.GameUnit)) -> None:
        """
        Continues overloading [] operator to set the value at the tuple
        @param key: tuple representing (x, y) coordinate on the regular map
        @param value: Tuple representing information about the region grid at the coordinate
        """

        self.grid_type[key[0] - self.xbounds[0], key[1] - self.ybounds[0]] = value[0]
        self.grid_unit[key[0] - self.xbounds[0], key[1] - self.ybounds[0]] = value[1]

    def in_bounds(self, coords: tuple or list) -> bool:
        """
        Checks if coordinate is in bounds
        @param coords: (x, y) pair
        @return: whether it's in bounds
        """

        if (
            self.xbounds[0] <= coords[0] <= self.xbounds[1]
            and self.ybounds[0] <= coords[1] <= self.ybounds[1]
        ):
            return True
        else:
            return False

    def on_edge(self, coords: tuple or list) -> bool:
        """
        Checks to see if the coordinate is an edge of the region
        @param coords: (x, y) coordinate
        @return: True if it is, false otherwise
        """

        return self[coords][0] == 0

    def on_inside(self, coords: tuple or list) -> bool:
        """
        Checks to see if the coordinate is inside the region
        @param coords: BONUS POINTS for figuring out what this means
        @return: True if it is, false otherwise
        """

        return self[coords][0] == 1

    def edge_coordinates(self, edge: (list or tuple, list or tuple)) -> list:
        """
        Calculates the lattice points along the edge
        @param edge: tuple of (x, y) coordinates denoting endpoints of the edge
        @return: list of lattice points along the edge
        """

        start = edge[0]
        finish = edge[1]
        if finish[0] < start[0]:
            start, finish = finish, start

        # if the line is horizontal
        if start[0] == finish[0]:
            return [
                (start[0], min(start[1], finish[1]) + i)
                for i in range(abs(finish[1] - start[1]) + 1)
            ]

        # line is vertical
        if start[1] == finish[1]:
            return [
                (min(start[0], finish[0]) + i, start[1])
                for i in range(abs(finish[0] - start[0]) + 1)
            ]

        # line is upwards sloping
        if finish[1] - start[1] > 0:
            return [
                (start[0] + i, start[1] + i) for i in range(finish[1] - start[1] + 1)
            ]
        # line is downward sloping
        else:
            return [
                (start[0] + i, start[1] - i) for i in range(start[1] - finish[1] + 1)
            ]

    def update_structures(self, unit_enum_map: dict, map: gamelib.GameMap) -> None:
        """
        Updates structures dictionary based on the current map
        unit_enum_map (dict): Maps NAME to unit enum
        @param map: map to base updates off of
        """

        # iterate through each valid tile inside the triangle to see what structure is in it
        for coord in self.coordinates:
            if self.grid_type[self.zero_coordinates(coord)] == -1:
                continue

            unit = map[coord[0], coord[1]]
            if not unit:
                self[coord[0], coord[1]][1] = None
                continue

            unit = unit[0]
            if unit.unit_type == unit_enum_map["TURRET"]:
                self.units[unit.unit_type].append(unit)
                self.grid_unit[self.zero_coordinates(coord)] = unit
            elif unit.unit_type == unit_enum_map["FACTORY"]:
                self.units[unit.unit_type].append(unit)
                self.grid_unit[self.zero_coordinates(coord)] = unit
            elif unit.unit_type == unit_enum_map["WALL"]:
                self.units[unit.unit_type].append(unit)
                self.grid_unit[self.zero_coordinates(coord)] = unit

        self.recalculate_paths = True

    def update_damage_regions(self, damage_regions: np.array(float)) -> None:
        """
        Updates damage regions array based the entire map's damage regions array
        @param damage_regions: Array representing the amount of damage dealt at each coordinate
        """

        self.damage_regions = damage_regions[
            self.xbounds[0] : (self.xbounds[1] + 1),
            self.ybounds[0] : (self.ybounds[1] + 1),
        ]

    def calculate_local_damage_regions(
        self, unit_enum_map: dict, game_map: gamelib.GameMap
    ):
        """
        Calculates the damage regions array based on only this region's structures
        Different from regular as it helps figure out the impact from only the buildings in this region, not others near it
        unit_enum_map (dict): Maps NAME to unit enum
        @param game_map: GameMap representing the current state
        """

        if game_map is None:
            return

        for turret in self.units[unit_enum_map["TURRET"]]:
            for coord in game_map.get_locations_in_range(
                (turret.x, turret.y), turret.attackRange
            ):
                if (
                    self.xbounds[1] >= coord[0] >= self.xbounds[0]
                    and self.ybounds[1] >= coord[1] >= self.ybounds[0]
                ):
                    self.damage_regions[self.zero_coordinates(coord)] += turret.damage_i

    def zero_coordinates(self, coord: tuple or list) -> (int, int):
        """
        Offsets coordinates to have (0, 0) at the lower left corner of the region space
        @param coord: (x, y) coordinate pair
        @return: transformed coordinates (x, y)
        """

        return coord[0] - self.xbounds[0], coord[1] - self.ybounds[0]

    def bfs(self, start: tuple or list, visited: np.array, path_dict: dict):
        """
        Breadth First Search based pathfinding algorithm between any given point and the edges of the region
        @param start: (x, y) coordinate to start bfs from
        @param visited: boolean array keeping track of which places have already been seen
        @param path_dict: dictionary containing all of the paths between two edge points
        """

        queue = [[list(start)]]
        visited[self.zero_coordinates(start)] = True
        while queue:
            path = queue.pop(0)
            s = path[-1]

            above = [s[0], s[1] + 1]
            below = [s[0], s[1] - 1]
            right = [s[0] + 1, s[1]]
            left = [s[0] - 1, s[1]]

            adjacents = [above, below, right, left]
            for adj in adjacents:
                if (
                    self.xbounds[0] <= adj[0] <= self.xbounds[1]
                    and self.ybounds[0] <= adj[1] <= self.ybounds[1]
                ):
                    if self[adj][0] >= 0 and not visited[self.zero_coordinates(adj)]:
                        visited[self.zero_coordinates(adj)] = True
                    if self[adj][1] is None:
                        continue

                    if self[adj][0] == 0:
                        path.append(above)
                        path_dict[tuple(start)][tuple(adj)] = path
                        path_dict[tuple(adj)][tuple(start)] = reversed(path)
                    else:
                        queue.append([path + above])

    def calculate_paths(self):
        """
        Calculates the paths from all edges to all other edges
        Not fast but only needs to be done once per turn
        Does BFS on each individual edge vertex
        **CAN BE OPTIMIZED FURTHER IF NEED BE**
        """

        if self.recalculate_paths:
            self.path_dict = {
                start: {end: [] for end in self.all_boundaries}
                for start in self.all_boundaries
            }
            for incoming_edge in self.incoming_edges:
                for entrance in self.edge_coordinates(incoming_edge):
                    visited = np.full((self.xwidth, self.ywidth), False)
                    self.bfs(entrance, visited, self.path_dict)

    def simulate_average_damage(self, unit_enum_map: dict, unit: str) -> float:
        """
        Simulates the average damage units would take if they entered this region and
        left it at all possible entrances and exits.
        unit_enum_map (dict): Maps NAME to unit enum
        @param unit: Gamelib Unit.  Must be mobile
        @return: Average damage taken across all possible paths
        """

        damage_to_units = 0
        total_paths = 0
        # calculate paths to each edge
        self.calculate_paths()

        # iterate through all edges
        if unit == unit_enum_map["DEMOLISHER"]:
            speed = 2
        elif unit == unit_enum_map["SCOUT"]:
            speed = 1
        elif unit == unit_enum_map["INTERCEPTOR"]:
            speed = 4

        for incoming_edge in self.incoming_edges:
            for entrance in self.edge_coordinates(incoming_edge):
                for path in self.path_dict[entrance].values():
                    if path:
                        total_paths += 1
                        damage_to_units += self.damage_on_path(speed, path)

        if total_paths == 0:
            return 0

        return damage_to_units / total_paths

    def damage_on_path(self, unit_speed: float, path: list) -> float:
        """
        Calculates damage taken on a specific path
        @param unit_speed: speed of the unit moving through the path
        @param path: list of coordinates (x, y)
        """

        damage = 0
        for coord in path:
            damage += self.damage_regions[self.zero_coordinates(coord)] * 1 / unit_speed

        return damage

    def average_tile_damage(self) -> float:
        """
        Calculates the average amount of damage a unit might take on tile
        @return: ^^^
        """

        total_damage = 0
        for coord in self.coordinates:
            total_damage += self.damage_regions[self.zero_coordinates(coord)]

        return total_damage / self.tile_count

    def calculate_region_cost(
        self,
        unit_enum_map: dict,
        health_prorated: bool = True,
        defensive_only: bool = False,
    ) -> int:
        """
        Calculates overall cost of region
        @param unit_enum_map: map describing the enumerations for each unit
        @param health_prorated: whether to prorate based on remaining health
        @param defensive_only: whether to only consider defensive units
        @return: returns the cost of the region
        """

        cost = 0
        for units in self.units.values():
            for unit in units:
                if defensive_only and unit.unit_type == unit_enum_map["FACTORY"]:
                    continue
                if health_prorated:
                    cost += (unit.health / unit.max_health) * unit.cost[
                        0
                    ]  # cost in structure points
                else:
                    cost += unit.cost[0]

        return cost

    def random_turret_placement(self, state: gamelib.GameState) -> (int, int):
        """
        Finds random available location to place a turret
        @param state: Game State
        @return: random available location (x, y) coordinate
        """

        loc = random.choice(list(self.coordinates))
        while (
            self.grid_type[self.zero_coordinates(loc)] == -1
            or self.grid_unit[self.zero_coordinates(loc)] is not None
        ):
            loc = random.choice(list(self.coordinates))

        return loc

    def calculate_overall_health(
        self, unit_enum_map: dict, defensive_only: bool = True
    ) -> int:
        """
        Calculates overall health of the region
        @param unit_enum_map: map describing the enumerations for each unit
        @param defensive_only: whether or not to only look at defensive units
        @return:
        """
        health = 0
        for units in self.units.values():
            for unit in units:
                if defensive_only and unit.unit_type == unit_enum_map["FACTORY"]:
                    continue
                health += unit.health

        return health

    def undefended_tiles(self) -> list:
        """
        Determines which tiles are undefended in the region
        @return: list of undefended tile coordinates
        """

        undefended = []
        for coord in self.coordinates:
            if self.damage_regions[self.zero_coordinates(coord)] == 0:
                # This coord is undefended by a turret
                undefended.append(coord)

        return undefended

    def calculate_region_states(self, unit_enum_map: dict, units: list):
        self.states = {}
        self.states["AVG TILE DMG"] = self.average_tile_damage()
        self.states["REGION COST ALL"] = self.calculate_region_cost(
            unit_enum_map, defensive_only=False
        )
        self.states["REGION COST DEF"] = self.calculate_region_cost(
            unit_enum_map, defensive_only=True
        )
        self.states["OVERALL HEALTH ALL"] = self.calculate_overall_health(
            unit_enum_map, defensive_only=False
        )
        self.states["OVERALL HEALTH DEF"] = self.calculate_overall_health(
            unit_enum_map, defensive_only=True
        )
        self.states["UNDEFENDED TILES"] = self.undefended_tiles()
        # self.states["SIMULATED DAMAGE"] = {
        #     unit: self.simulate_average_damage(unit_enum_map, unit) for unit in units
        # }

    def calculate_optimal_turret_placement(self, unit_enum_map: dict) -> (int, int):
        """
        Calculates optimal placement of turret based on the current region state.
        @param unit_enum_map: map describing the enumerations for each unit
        @return: optimal coordinate for turret placement
        """

        if self.units[unit_enum_map["TURRET"]] is None:
            # If no pre-existing turrets, random
            return random.choice(self.edge_coordinates(self.incoming_edges[0]))

        # Otherwise, find location maximizing distance from all other turrets
        best_candidate = list(self.coordinates)[0]
        distance_from_other_turrets = 0
        for coord in self.coordinates:
            if self.grid_unit[self.zero_coordinates(coord)] is not None or self.grid_type[self.zero_coordinates(coord)] == 0:
                continue

            # Maxmize distanced to ALL turrets
            dist = sum(
                math.sqrt((turret.x - coord[0]) ** 2 + (turret.y - coord[1]) ** 2)
                for turret in self.units[unit_enum_map["TURRET"]]
            )
            if dist > distance_from_other_turrets:
                best_candidate = coord

        return best_candidate

    def calculate_optimal_turret_upgrade(self, unit_enum_map: dict) -> (int, int):
        """
        Calculates the optimal turret to upgrade based on how close it is to the edge
        @param unit_enum_map: map describing the enumerations for each unit
        @return: (x, y) coordinate describing the location of said turret
        """

        # Find turret closest to the front

        if len(self.units[unit_enum_map["TURRET"]]) == 0:
            return None

        best_candidate = self.units[unit_enum_map["TURRET"]][0]
        highest_y = 0
        highest_x = 0
        for turret in self.units[unit_enum_map["TURRET"]]:
            if turret.upgraded:
                continue
            if turret.y >= highest_y:
                highest_y = turret.y
                highest_x = turret.x

        return highest_x, highest_y

    def place_walls_near_turrets(
        self, game_state: gamelib.GameState, unit_enum_map: dict, count=1, upgrade=False
    ):
        """
        Places walls near already placed turrets in the region.
        @param game_state: Game State
        @param unit_enum_map: map describing the enumerations for each unit
        @param count: number of walls to place
        @param upgrade: whether or not to upgrade the walls
        """

        for turret in self.units[unit_enum_map["TURRET"]]:
            above = [turret.x, turret.y + 1]
            right = [turret.x + 1, turret.y]
            left = [turret.x - 1, turret.y]
            loc = [above, right, left]
            game_state.attempt_spawn(
                unit_type=unit_enum_map["WALL"], locations=loc[:count]
            )
            if upgrade:
                for l in loc[:count]:
                    if self.in_bounds(l):
                        game_state.attempt_upgrade(locations=loc[:count])

    def fortify_region_defenses(
        self, game_state: gamelib.GameState, unit_enum_map: dict
    ):
        """
        Fortifies region defenses based on relationship between turrets and walls
        @param game_state: Game State
        @param unit_enum_map: map describing the enumerations for each unit
        """

        if game_state.turn_number >= self.MIN_TURN_UPGRADE:
            upgrade = True
        else:
            upgrade = False

        if len(self.units[unit_enum_map["TURRET"]]) > 2 * len(
            self.units[unit_enum_map["WALL"]]
        ):
            gamelib.util.debug_write("LESS TURRETS THAN WALLS")
            # Place more walls near turrets
            self.place_walls_near_turrets(game_state, unit_enum_map, upgrade=upgrade)

        if len(self.units[unit_enum_map["TURRET"]]) <= 1:
            gamelib.debug_write("LESS THAN 2 TURRETS")
            optimal = self.calculate_optimal_turret_placement(unit_enum_map)
            game_state.attempt_spawn(
                unit_type=unit_enum_map["TURRET"], locations=optimal
            )
        elif self.MAX_TURRETS > len(self.units[unit_enum_map["TURRET"]]) > 1:

            if (
                any(
                    (turret.health / turret.max_health < 0.5)
                    for turret in self.units[unit_enum_map["TURRET"]]
                )
                and game_state.get_resource(0, 0) >= 2
            ):
                gamelib.debug_write("Less than half hp")
                # Could have many turrets but atleast 1 is low health
                optimal = self.calculate_optimal_turret_placement(unit_enum_map)
                game_state.attempt_spawn(
                    unit_type=unit_enum_map["TURRET"], locations=optimal
                )
            elif game_state.get_resource(0, 0) >= 4:
                optimal = self.calculate_optimal_turret_upgrade(unit_enum_map)
                if not optimal:
                    game_state.attempt_upgrade(
                        unit_type=unit_enum_map["TURRET"], locations=optimal
                    )
                else:
                    optimal = self.calculate_optimal_turret_placement(unit_enum_map)
                    game_state.attempt_spawn(
                        unit_type=unit_enum_map["TURRET"], locations=optimal
                    )
        else:
            optimal = self.calculate_optimal_turret_upgrade(unit_enum_map)
            if not optimal:
                game_state.attempt_upgrade(
                    unit_type=unit_enum_map["TURRET"], locations=optimal
                )

    def point_inside_polygon(self, x: int, y: int, poly: list) -> bool:
        """
        Checks to see if an x,y coordinate is inside of a polygon
        @param x: x coordinate
        @param y: coordinate
        @param poly: list of vertices representing the convex polygon
        @return: whether the point is in the polygon
        """

        n = len(poly)
        inside = False

        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
