import gamelib
import matplotlib.path as mplPath
import numpy as np


class Region:
    def __init__(
        self,
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
        @type map: gamelib.GameMap
        @param vertices: list of tuples containing (x, y) coordinates for the region's vertices
        @param player_id: player_id of region (0 - us, 1 - opponent)
        @param incoming_edges: list of vertex pairs representing the edges that opponents can enter through
        @param outgoing_edges: list of vertex pairs representing the edges that opponents can exit out of
        @param breach_edges: list of vertex pairs representing the edge(s) that opponents can damage us through
        @param damage_regions: Numpy array representing the damage units take at a specific coordinate in the region
        """
        self.vertices = vertices
        self.coordinates = []
        self.player_id = player_id
        self.incoming_edges = incoming_edges
        self.outgoing_edges = outgoing_edges
        self.breach_edges = breach_edges
        self.edges = set(incoming_edges + outgoing_edges + breach_edges)

        # dictionary containing unit types in region
        self.units = {"TURRET": [], "FACTORY": [], "WALL": []}

        # region bounds
        self.xbounds = min(v[0] for v in self.vertices), max(
            v[0] for v in self.vertices
        )
        self.xwidth = self.xbounds[1] - self.xbounds[0]

        self.ybounds = min(v[1] for v in self.vertices), max(
            v[1] for v in self.vertices
        )
        self.ywidth = self.ybounds[1] - self.ybounds[0]

        # each value in the grid looks like (int, units)
        # the first # is the type of coordinate:
        # -1: invalid coordinate, 0: edge, 1: inside
        # the second is the stationary unit contained in the cell
        # the [] operator accesses values from this grid
        self.grid = np.full(
            shape=(self.xwidth, self.ywidth), fill_value=(-1, None), dtype=(int, object)
        )

        # boolean to determine if we need to recalculate our paths from edge to edge based on new buildings being built
        self.recalculate_paths = True
        self.path_dict = {}

        # checks to see if x, y coordinates are in the polygon
        polygon_path = mplPath.Path(np.array(vertices))
        for y in range(self.ybounds[0], self.ybounds[1] + 1):
            hlist = []
            for x in range(self.xbounds[0], self.xbounds[1] + 1):
                if polygon_path.contains_point((x, y)):
                    hlist.append((x, y))
                    self[x, y][0] = 1
            self.coordinates.append(hlist)

        # assigns edge coordinates to zero
        self.all_boundaries = set([self.edge_coordinates(edge) for edge in self.edges])
        for coord in self.all_boundaries:
            self[coord][0] = 0

        # calculates the damage regions
        if damage_regions is None:
            self.damage_regions = np.full(
                shape=(self.xwidth, self.ywidth), fill_value=0
            )
            self.calculate_local_damage_regions(map)
            # to access you must shift the coordinate with zero_coordinates
        else:
            self.damage_regions = damage_regions[
                self.xbounds[0] : (self.xbounds[1] + 1),
                self.ybounds[0] : (self.ybounds[1] + 1),
            ]

    def __getitem__(self, key: list or tuple) -> (int, gamelib.unit):
        """
        Overloads [] operator to get tuple from self.grid
        @param key: tuple representing (x, y) coordinate on the regular map
        @return: Tuple representing information about the region grid at the coordinate
        """
        return self.grid[self.zero_coordinates(key)]

    def __setitem__(self, key: list or tuple, value: (int, gamelib.unit)) -> None:
        """
        Continues overloading [] operator to set the value at the tuple
        @param key: tuple representing (x, y) coordinate on the regular map
        @param value: Tuple representing information about the region grid at the coordinate
        """
        self.grid[key[0] - self.xbounds[0], key[1] - self.ybounds[0]] = value

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
        else:
            return [
                (start[0] - i, start[1] - i) for i in range(start[1] - finish[1] + 1)
            ]

    def update_structures(self, map: gamelib.GameMap) -> None:
        """
        Updates structures dictionary based on the current map
        @param map: map to base updates off of
        """
        # iterate through each valid tile inside the triangle to see what structure is in it
        for hcoords in self.coordinates:
            for coord in hcoords:
                unit = map[coord[0], coord[1]]
                if not unit:
                    self[coord[0], coord[1]][1] = None
                    continue
                unit = unit[0]
                if unit.unit_type == "TURRET":
                    self.units[unit.unit_type].append(unit)
                    self[coord[0], coord[1]][1] = unit
                elif unit.unit_type == "FACTORY":
                    self.units[unit.unit_type].append(unit)
                    self[coord[0], coord[1]][1] = unit
                elif unit.unit_type == "WALL":
                    self.units[unit.unit_type].append(unit)
                    self[coord[0], coord[1]][1] = unit
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

    def calculate_local_damage_regions(self, game_map: gamelib.GameMap):
        """
        Calculates the damage regions array based on only this region's structures
        Different from regular as it helps figure out the impact from only the buildings in this region, not
        others near it
        @param game_map: GameMap representing the current state
        """
        if game_map is None:
            return

        for turret in self.units["TURRET"]:
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
        self.path_dict = {
            start: {end: [] for end in self.all_boundaries}
            for start in self.all_boundaries
        }
        if self.recalculate_paths:
            for incoming_edge in self.incoming_edges:
                for entrance in self.edge_coordinates(incoming_edge):
                    visited = np.full((self.xwidth, self.ywidth), False)
                    self.bfs(entrance, visited, self.path_dict)

    def simulate_average_damage(self, unit_type: gamelib.unit):
        """
        Simulates the average damage units would take if they entered this region and
        left it at all possible entrances and exits.
        @param unit_type: Gamelib Unit.  Must be mobile
        @return: Average damage taken across all possible paths
        """
        damage_to_units = 0
        total_paths = 0
        # calculate paths to each edge
        if self.recalculate_paths:
            self.calculate_paths()
        # iterate through all edges
        for incoming_edge in self.incoming_edges:
            for entrance in self.edge_coordinates(incoming_edge):
                for path in self.path_dict[entrance].values():
                    if path:
                        total_paths += 1
                        damage_to_units += self.damage_on_path(unit_type.speed)

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

    def calculate_region_cost(self):
        # TBA
        return None

    def update_history(self):
        return None