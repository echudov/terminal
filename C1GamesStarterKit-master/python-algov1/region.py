import gamelib
import numpy as np


class Region:
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
            for coord in self.edge_coordinates([vertices[i], vertices[(i + 1) % len(vertices)]]):
                self.all_boundaries.add(coord)

        for y in range(self.ybounds[0], self.ybounds[1] + 1):
            for x in range(self.xbounds[0], self.xbounds[1] + 1):
                if (x, y) in self.all_boundaries:
                    self.grid_type[self.zero_coordinates((x, y))] = 0
                    continue
                if self.point_inside_polygon(x, y, vertices):
                    self.coordinates.add((x, y))
                    self.grid_type[self.zero_coordinates((x, y))] = 1


        self.tile_count = sum(len(hcoords) for hcoords in self.coordinates)
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

    def on_edge(self, coords: tuple or list) -> bool:
        """
        Checks to see if the coordinate is an edge of the region
        @param coords: (x, y) coordinate
        @return: True if it is, false otherwise
        """
        if self[coords][0] == 0:
            return True
        else:
            return False

    def on_inside(self, coords: tuple or list) -> bool:
        """
        Checks to see if the coordinate is inside the region
        @param coords: BONUS POINTS for figuring out what this means
        @return: True if it is, false otherwise
        """
        if self[coords][0] == 1:
            return True
        else:
            return False

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
        for hcoords in self.coordinates:
            for coord in hcoords:
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

    def zero_coordinates(self, coord: tuple or list):
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
        queue = [[start]]
        visited[self.zero_coordinates(start)] = True
        while queue:
            path = queue.pop(0)
            s = path[-1]
            above = (s[0], s[1] + 1)
            below = (s[0], s[1] - 1)
            right = (s[0] + 1, s[1])
            left = (s[0] - 1, s[1])
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
                        path_dict[start][adj] = path.append(above)
                        path_dict[adj][start] = reversed(path_dict[start][adj])
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

    def simulate_average_damage(self, unit_enum_map: dict, unit: str):
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
        if unit == "DEMOLISHER":
            speed = 2
        elif unit == "SCOUT":
            speed = 1
        elif unit == "INTERCEPTOR":
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

    def average_tile_damage(self):
        """
        Calculates the average amount of damage a unit might take on tile
        @return:
        """
        total_damage = 0
        for hcoords in self.coordinates:
            for coord in hcoords:
                total_damage += self.damage_regions[self.zero_coordinates(coord)]
        return total_damage / self.tile_count

    def calculate_region_cost(
        self, unit_enum_map: dict, health_prorated=True, defensive_only=False
    ):
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

    def calculate_overall_health(self, unit_enum_map: dict, defensive_only=True):
        health = 0
        for units in self.units.values():
            for unit in units:
                if defensive_only and unit.unit_type == unit_enum_map["FACTORY"]:
                    continue
                health += unit.health
        return health

    def undefended_tiles(self):
        undefended = []
        for hcoords in self.coordinates:
            for coord in hcoords:
                if self.damage_regions[self.zero_coordinates(coord)] == 0:
                    undefended.append(coord)
        return undefended

    def calculate_region_states(self, unit_enum_map: dict, units):
        states = {}
        states["AVG TILE DMG"] = self.average_tile_damage()
        states["REGION COST ALL"] = self.calculate_region_cost(unit_enum_map, defensive_only=False)
        states["REGION COST DEF"] = self.calculate_region_cost(unit_enum_map, defensive_only=True)
        states["OVERALL HEALTH ALL"] = self.calculate_overall_health(
            unit_enum_map, defensive_only=False
        )
        states["OVERALL HEALTH DEF"] = self.calculate_overall_health(
            unit_enum_map, defensive_only=True
        )
        states["UNDEFENDED TILES"] = self.undefended_tiles()
        states["SIMULATED DAMAGE"] = {
            unit: self.simulate_average_damage(unit_enum_map, unit) for unit in units
        }
        return states

    def point_inside_polygon(self, x, y, poly):
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
