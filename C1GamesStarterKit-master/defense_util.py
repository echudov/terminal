import gamelib
import matplotlib.path as mplPath
import numpy as np

class Region:

    def __init__(self, vertices: list, player_id: int, incoming_edges: list, outgoing_edges: list, breach_edges: list) -> object:
        """
        Initializes a general region to keep track of units
        @param vertices:
        @param player_id:
        @param incoming_edges:
        @param outgoing_edges:
        @param breach_edges:
        """
        self.vertices = vertices
        self.coordinates = []
        self.player_id = player_id
        self.incoming_edges = incoming_edges
        self.outgoing_edges = outgoing_edges
        self.breach_edges = breach_edges
        self.edges = set(incoming_edges + outgoing_edges + breach_edges)

        self.units = {"TURRET": [], "FACTORY": [], "WALL": []}

        self.xbounds = min(v[0] for v in self.vertices), max(v[0] for v in self.vertices)
        self.xwidth = self.xbounds[1] - self.xbounds[0]
        self.ywidth = self.ybounds[1] - self.ybounds[0]
        self.ybounds = min(v[1] for v in self.vertices), max(v[1] for v in self.vertices)

        # each value in the grid looks like (int, units)
        # the first # is the type of coordinate:
        # -1: invalid coordinate, 0: edge, 1: inside
        self.grid = np.full(shape=(self.xwidth, self.ywidth), fill_value=(-1, None), dtype=(int, gamelib.unit))

        # checks to see if x, y coordinates are in the polygon
        polygon_path = mplPath.Path(np.array(vertices))
        for y in range(self.ybounds[0], self.ybounds[1] + 1):
            hlist = []
            for x in range(self.xbounds[0], self.xbounds[1] + 1):
                    if polygon_path.contains_point((x, y)):
                        hlist.append((x, y))
                        self[x, y][0] = 1
            self.coordinates.append(hlist)

        for edge in edges:
            for coord in edge_coordinates(edge):
                self[x, y][0] = 0


    def __getitem__(self, key: list or tuple) -> (int, gamelib.unit):
        return self.grid[key[0] - self.xbounds[0], key[1] - self.ybounds[0]]

    def __setitem__(self, key: list or tuple, value: (int, gamelib.unit)) -> None:
        self.grid[key[0] - self.xbounds[0], key[1] - self.ybounds[0]] = value

    def on_edge(self, coords):
        if self[coords][0] == 0:
            return True
        else:
            return False

    def on_inside(self, coords):
        if self[coords][0] == 1:
            return True
        else:
            return False

    def edge_coordinates(self, edge: (list or tuple, list or tuple)) -> list:
        start = edge[0]
        finish = edge[1]
        # if the line is horizontal
        if start[0] == finish[0]:
            return [(start[0], min(start[1], finish[1]) + i) for i in range(abs(finish[1] - start[1]) + 1)]
        # line is vertical
        if start[1] == finish[1]:
            return [(min(start[0], finish[0]) + i, start[1]) for i in range(abs(finish[0] - start[0]) + 1)]
        # line is upwards sloping
        if finish[1] - start[1] > 0:
            return [(start[0] + i, start[1] + i) for i in range(finish[1] - start[1] + 1)]
        else:
            return [(start[0] - i, start[1] - i) for i in range(start[1] - finish[1] + 1)]

    def update_structures(self, map: gamelib.GameMap, structures: list = None) -> None:
        if structures is None:
            # iterate through each valid tile inside the triangle to see what structure is in it
            for hcoords in self.coordinates:
                for coord in hcoords:
                    unit = map[coord[0], coord[1]]
                    if not unit:
                        continue
                        self[coord[0], coord[1]][1] = None
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

    def bfs(self, start, visited, start_dict):
        queue = [[start]]
        visited[start] = True
        while queue:
            path = queue.pop(0)
            s = path[-1]
            above = (s[0], s[1] + 1)
            below = (s[0], s[1] - 1)
            right = (s[0] + 1, s[1])
            left = (s[0] - 1, s[1])
            if self[above][0] >= 0 and not visited[above]:


                if neighbor is valid:
                    start_dict[neighbor]

    def simulate_breachability(self, unit_type, starting_location, count=None):
        units_breached = 0
        for incoming_edge in self.incoming_edges:
            for

