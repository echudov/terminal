import gamelib
import numpy as np
from region import Region
import queue


class Defense:
    # CONSTANTS

    # Relative weight (lower means more emphasis on turrets)
    TURRET_TO_WALL_RATIO = 1
    MIN_TURN_TO_FORTIFY_BACK_REGIONS = 3  # Used in fortify_defenses
    MIN_TURN_REBUILD = 10  # Min turn to start re-building low-health structures
    PERCENT_TO_REBUILD_TURRET = 0.75  # Threshold for above
    PERCENT_TO_REBUILD_WALL = 0.75  # Threshold for above

    def __init__(self, unit_enum_map: dict, player_id: int):
        """
        Initializes defense with multiple predetermined regions.
        unit_enum_map (dict): Maps NAME to unit enum
        @param player_id: Number representing which player this defense is for 0 - us, 1 - opponent
        @param game_state: passes current game_state as GameState object
        """
        self.regions = {}
        self.region_count = 6
        self.player_id = player_id
        self.damage_regions = np.zeros(shape=(28, 14))
        self.grid_unit = np.full(shape=(28, 14), fill_value=None)
        if player_id == 0:
            self.create_our_regions(unit_enum_map)
        else:
            self.create_enemy_regions(unit_enum_map)
        self.coordinate_regions = np.full(shape=(28, 14), fill_value=-1)
        self.grid_type = np.full(shape=self.coordinate_regions.shape, fill_value=-1)
        self.initialize_coordinate_regions()
        self.initialize_grid()
        self.history = []
        self.units = {
            unit_enum_map["TURRET"]: [],
            unit_enum_map["FACTORY"]: [],
            unit_enum_map["WALL"]: [],
        }
        self.recalculate_damage_regions = True
        self.turrets_to_rebuild = queue.Queue()
        self.walls_to_rebuild = queue.Queue()

    def create_our_regions(self, unit_enum_map: dict):
        self.regions[0] = Region(
            unit_enum_map,
            [(0, 13), (7, 13), (7, 6)],
            self.player_id,
            incoming_edges=[((0, 13), (7, 13)), ((7, 13), (7, 6))],
            outgoing_edges=[],
            breach_edges=[((0, 13), (7, 6))],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[1] = Region(
            unit_enum_map,
            [(27, 13), (20, 13), (20, 6)],
            self.player_id,
            incoming_edges=[((20, 13), (27, 13)), ((20, 13), (20, 6))],
            outgoing_edges=[],
            breach_edges=[((27, 13), (20, 6))],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[2] = Region(
            unit_enum_map,
            [(7, 6), (7, 13), (14, 13)],
            self.player_id,
            incoming_edges=[((7, 6), (7, 13)), ((7, 13), (14, 13))],
            outgoing_edges=[((7, 6), (14, 13))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[3] = Region(
            unit_enum_map,
            [(13, 13), (20, 13), (20, 6)],
            self.player_id,
            incoming_edges=[((13, 13), (20, 13)), ((20, 13), (20, 6))],
            outgoing_edges=[((13, 13), (20, 6))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[4] = Region(
            unit_enum_map,
            [(7, 6), (13, 12), (14, 12), (20, 6)],
            self.player_id,
            incoming_edges=[
                ((7, 6), (13, 12)),
                ((13, 12), (14, 12)),
                ((14, 12), (20, 6)),
            ],
            outgoing_edges=[((7, 6), (20, 6))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[5] = Region(
            unit_enum_map,
            [(7, 6), (20, 6), (14, 0), (13, 0)],
            self.player_id,
            incoming_edges=[((7, 6), (20, 6))],
            outgoing_edges=[],
            breach_edges=[((7, 6), (13, 0)), ((13, 0), (14, 0)), ((14, 0), (20, 6))],
            map=None,
            damage_regions=self.damage_regions,
        )

    def create_enemy_regions(self, unit_enum_map: dict):
        self.regions[0] = Region(
            unit_enum_map,
            [(0, 14), (7, 14), (7, 21)],
            self.player_id,
            incoming_edges=[((0, 14), (7, 14)), ((7, 14), (7, 21))],
            outgoing_edges=[],
            breach_edges=[((0, 14), (7, 21))],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[1] = Region(
            unit_enum_map,
            [(20, 14), (20, 21), (27, 14)],
            self.player_id,
            incoming_edges=[((20, 14), (20, 21)), ((20, 14), (27, 14))],
            outgoing_edges=[],
            breach_edges=[((20, 21), (27, 14))],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[2] = Region(
            unit_enum_map,
            [(7, 14), (7, 21), (14, 14)],
            self.player_id,
            incoming_edges=[((7, 14), (14, 14)), ((7, 14), (7, 21))],
            outgoing_edges=[((7, 21), (14, 14))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[3] = Region(
            unit_enum_map,
            [(13, 14), (20, 21), (20, 14)],
            self.player_id,
            incoming_edges=[((13, 14), (20, 14)), ((20, 14), (20, 21))],
            outgoing_edges=[((13, 14), (20, 21))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[4] = Region(
            unit_enum_map,
            [(7, 21), (13, 15), (14, 15), (20, 21)],
            self.player_id,
            incoming_edges=[
                ((7, 21), (13, 15)),
                ((13, 15), (14, 15)),
                ((14, 15), (20, 21)),
            ],
            outgoing_edges=[((7, 21), (20, 21))],
            breach_edges=[],
            map=None,
            damage_regions=self.damage_regions,
        )
        self.regions[5] = Region(
            unit_enum_map,
            [(7, 21), (13, 27), (14, 27), (20, 21)],
            self.player_id,
            incoming_edges=[((7, 21), (20, 21))],
            outgoing_edges=[],
            breach_edges=[
                ((7, 21), (13, 27)),
                ((13, 27), (14, 27)),
                ((14, 27), (20, 21)),
            ],
            map=None,
            damage_regions=self.damage_regions,
        )

    def on_new_round(self, unit_enum_map: dict, game_state: gamelib.GameState):
        """
        Updates relevant values
        unit_enum_map (dict): Maps NAME to unit enum
        @param game_state: GameState value to update with
        """

        self.update_defense(unit_enum_map, game_state)

    def initialize_coordinate_regions(self):
        """
        Initializes coordinate_regions to contain information about what region they are contained in
        """

        for i in range(len(self.regions)):
            for coordinate in self.regions[i].coordinates:
                self.coordinate_regions[
                    self.offset_coord(self.offset_coord(coordinate))
                ] = i

    def get_region(self, coord: list or tuple):
        """
        Gets the region that the coordinate is contained in
        @param coord: (x, y) coordinate to query
        @return: list of regions containing coordinate
        """

        return self.coordinate_regions[self.offset_coord(coord)]

    def offset_coord(self, coord: list or tuple):
        """
        Offsets coordinate depending on if the player is us or the enemy
        @param coord: (x, y) coordinate
        @return: offset coordinate
        """

        if self.player_id == 1:
            return coord[0], coord[1] - 14
        else:
            return coord

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

    def initialize_grid(self):
        """
        Initializes grid describing what each coordinate's type is;
        -1: out of bounds
        0: breach_edge
        1: inner coordinate
        """
        for x in range(self.coordinate_regions.shape[0]):
            for y in range(self.coordinate_regions.shape[1]):
                if self.coordinate_regions[x, y] != -1:
                    self.grid_type[x, y] = 1
        if self.player_id == 0:
            for coord in self.edge_coordinates([[0, 13], [13, 0]]):
                self.grid_type[coord] = 0
            for coord in self.edge_coordinates([[14, 0], [27, 13]]):
                self.grid_type[coord] = 0
        else:
            for coord in self.edge_coordinates([[0, 14], [13, 27]]):
                self.grid_type[self.offset_coord(coord)] = 0
            for coord in self.edge_coordinates([[14, 27], [27, 14]]):
                self.grid_type[self.offset_coord(coord)] = 0

    def update_defense(self, unit_enum_map: dict, game_state: gamelib.GameState):
        """
        Updates defense values
        @param game_state: GameState to update with
        """

        # for simulating unit traversals in region
        units = [
            unit_enum_map["DEMOLISHER"],
            unit_enum_map["SCOUT"],
            unit_enum_map["INTERCEPTOR"],
        ]
        # resets units
        self.units = {
            unit_enum_map["TURRET"]: [],
            unit_enum_map["FACTORY"]: [],
            unit_enum_map["WALL"]: [],
        }

        for region in self.regions.values():
            region.update_structures(unit_enum_map, game_state.game_map)
            # iterate through the units to add to the overall game state
            # we use a set because there is overlap of regions, we don't want to double count units
            # find the states of region i
            region.calculate_region_states(unit_enum_map, units)

        for x in range(game_state.ARENA_SIZE):
            for y in range(
                game_state.HALF_ARENA * self.player_id,
                game_state.HALF_ARENA * (1 + self.player_id),
            ):
                if not game_state.game_map.in_arena_bounds((x, y)):
                    continue
                unit = game_state.game_map[x, y]
                if not unit:
                    continue
                unit = unit[0]
                if (
                    unit.unit_type == unit_enum_map["WALL"]
                    or unit.unit_type == unit_enum_map["TURRET"]
                    or unit.unit_type == unit_enum_map["FACTORY"]
                ):
                    self.units[unit.unit_type].append(unit)
                    self.grid_unit[self.offset_coord((x, y))] = unit
        self.recalculate_damage_regions = True

    def calculate_damage_regions(self, game_map: gamelib.GameMap, unit_enum_map):
        """
        Evaluates all damages from turrets to combine into one np array
        Describes the amount of damage a unit takes per frame in a specific location
        """
        if self.recalculate_damage_regions:
            for turret in self.units[unit_enum_map["TURRET"]]:
                if turret.upgraded:
                    damage = 15
                    radius=3.5
                else:
                    damage = 5
                    radius=2.5
                for coord in game_map.get_locations_in_range(location=[turret.x, turret.y], radius=radius):
                    offset_coord = self.offset_coord(coord)
                    if self.grid_type[offset_coord] == -1 or offset_coord[1] > 13:
                        continue
                    self.damage_regions[offset_coord] += damage
            self.recalculate_damage_regions = False

    def get_damage_at_coord(self, coord):
        return self.damage_regions[self.offset_coord(coord)]

    def get_defense_undefended_tiles(self):
        """
        Updates defense tiles
        @return: list of undefended tiles
        """

        return {
            i: self.regions[i].states["UNDEFENDED TILES"]
            for i in range(self.region_count)
        }

    def calculate_total_cost(
        self,
        unit_enum_map: dict,
        defensive_only: bool = True,
        health_prorated: bool = True,
    ) -> float:
        """
        Calculates the total cost of all units
        unit_enum_map (dict): Maps NAME to unit enum
        @param defensive_only: Whether to only look at defensive units
        @param health_prorated: Whether to prorate cost by remaining health
        @return: total cost
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

    def weakest_region(
        self,
        unit_enum_map: dict,
        criteria: str = "HEALTH",
        regions_to_consider: list = range(4),
    ) -> int:
        """
        Finds weakest region based on the criteria specified
        @param unit_enum_map: map describing the enumerations for each unit
        @param criteria: WORKS AS FOLLOWS:
                         HEALTH - Considers which region has the lowest overall health of defensive buildings
                         UNDEFENDED TILES - Considers which region has the most undefended tiles
        @param regions_to_consider: which regions to consider
        @return: Region ID.
        """

        if criteria == "HEALTH":
            min_health = 1000000000
            min_id = 0
            for reg_id in regions_to_consider:
                if self.regions[reg_id].states["OVERALL HEALTH DEF"] < min_health:
                    min_id = reg_id
                    min_health = self.regions[reg_id].states["OVERALL HEALTH DEF"]

            return min_id

        if criteria == "UNDEFENDED TILES":
            undefended_tiles_max = 0
            worst_id = 0
            for reg_id in regions_to_consider:
                if (
                    len(self.regions[reg_id].states["UNDEFENDED TILES"])
                    > undefended_tiles_max
                ):
                    undefended_tiles_max = len(
                        self.regions[reg_id].states["UNDEFENDED TILES"]
                    )
                    worst_id = reg_id

            return worst_id

        if criteria == "DEFENSIVE POWER":
            min_defensive_power = 100000000
            min_id = 0
            for reg_id in regions_to_consider:
                region_wall_power = 0
                region_turret_power = 0
                for units in self.regions[reg_id].units.values():
                    for unit in units:
                        if unit.unit_type == unit_enum_map["WALL"]:
                            region_wall_power += unit.cost[0] * (
                                unit.health / unit.max_health
                            )
                        elif unit.unit_type == unit_enum_map["TURRET"]:
                            region_turret_power += (
                                unit.cost[0]
                                * (unit.health / unit.max_health)
                                * self.TURRET_TO_WALL_RATIO
                            )

                if min(region_turret_power, region_wall_power) < min_defensive_power:
                    min_id = reg_id
                    min_defensive_power = min(region_turret_power, region_wall_power)

            return min_id

        if criteria == "AVG TILE DMG":
            min_avg_tile_dmg = 100000000
            min_id = 0
            for reg_id in regions_to_consider:
                avg_tile_dmg = self.regions[reg_id].states["AVG TILE DMG"]
                if avg_tile_dmg < min_avg_tile_dmg:
                    min_avg_tile_dmg = avg_tile_dmg
                    min_id = reg_id
            return min_id

    def build_corners(self, game_state, unit_enum_map):
        for i in range(4):
            if game_state.can_spawn(unit_enum_map["WALL"], location=[i, 13]):
                game_state.attempt_spawn(
                    unit_enum_map["WALL"],
                    locations=[i, 13],
                )
            if game_state.can_spawn(unit_enum_map["WALL"], location=[27 - i, 13]):
                game_state.attempt_spawn(
                    unit_enum_map["WALL"],
                    locations=[27 - i, 13],
                )
            game_state.attempt_upgrade([[i, 13], [27 - i, 13]])

    def rebuild_routine(self, game_state, unit_enum_map):
        while (
                not self.turrets_to_rebuild.empty() and game_state.get_resource(0, 0) >= 4
        ):
            elem = self.turrets_to_rebuild.get()
            if (
                    game_state.attempt_spawn(
                        unit_type=unit_enum_map["TURRET"], locations=elem["COORD"]
                    )
                    > 0
            ):
                if True:
                    turret = game_state.game_map[elem["COORD"]][0]
                    above = [turret.x, turret.y + 1]
                    right = [turret.x + 1, turret.y]
                    left = [turret.x - 1, turret.y]
                    loc = [above, right, left]
                    game_state.attempt_spawn(
                        unit_type=unit_enum_map["WALL"], locations=loc
                    )
                    if elem["UPGRADE"]:
                        for l in loc:
                            game_state.attempt_upgrade(locations=loc)

        self.turrets_to_rebuild = queue.Queue()

        while not self.walls_to_rebuild.empty() and game_state.get_resource(0, 0) >= 4:
            elem = self.walls_to_rebuild.get()
            if (
                    game_state.attempt_spawn(
                        unit_type=unit_enum_map["WALL"], locations=elem["COORD"]
                    )
                    > 0
            ):
                if True:
                    game_state.attempt_upgrade(locations=elem["COORD"])

        self.walls_to_rebuild = queue.Queue()

        for turret in self.units[unit_enum_map["TURRET"]]:
            if turret.health < self.PERCENT_TO_REBUILD_TURRET * turret.max_health:
                self.turrets_to_rebuild.put(
                    {"COORD": [turret.x, turret.y], "UPGRADE": turret.upgraded}
                )
                game_state.attempt_remove([turret.x, turret.y])
        for wall in self.units[unit_enum_map["WALL"]]:
            if wall.health < self.PERCENT_TO_REBUILD_WALL * wall.max_health:
                self.walls_to_rebuild.put(
                    {"COORD": [wall.x, wall.y], "UPGRADE": wall.upgraded}
                )
                game_state.attempt_remove([wall.x, wall.y])

    def fortify_defenses(
        self,
        game_state: gamelib.GameState,
        unit_enum_map: dict,
        criteria: str = "DEFENSIVE POWER",
        sp_left: int = 3,
    ):
        """
        Fortifies defenses by finding the weakest region by our criteria
        and fortifying based on the Region fortify_region_defenses subroutine
        @param sp_left: Amount of sp points to leave after defenses are fortified
        @param game_state: Game State to pass in
        @param criteria: Criteria to evaluate weakest region on
        """

        # If it's late enough, rebuild
        if game_state.turn_number > self.MIN_TURN_REBUILD:
            # Run routine to delete and rebuild units that are at low health
            self.rebuild_routine(game_state, unit_enum_map)
            # Run routine to build corner walls if they haven't been built yet
            self.build_corners(game_state, unit_enum_map)



        count = 0
        while game_state.get_resource(0, 0) > sp_left and count < 15:
            if game_state.turn_number > self.MIN_TURN_TO_FORTIFY_BACK_REGIONS:
                # Check the back regions too (fortify factories, etc.)
                weakest_region = self.weakest_region(
                    unit_enum_map, criteria=criteria, regions_to_consider=range(6)
                )
            else:
                weakest_region = self.weakest_region(
                    unit_enum_map, criteria=criteria, regions_to_consider=range(4)
                )

            gamelib.util.debug_write(
                "WEAKEST REGION AT COUNT: "
                + str(count)
                + " is: "
                + str(weakest_region)
                + "; CURRENT SP IS: "
                + str(game_state.get_resource(0, 0))
            )
            self.regions[weakest_region].fortify_region_defenses(
                game_state, unit_enum_map
            )
            # IF WE HAVE TIME REFACTOR THIS TO BE MORE EFFICIENT BY UPDATING ONLY ON WHAT CHANGED
            # RIGHT NOW I THINK WE HAVE THE TIME TO SPARE THOUGH
            # IMPORTANT TO NOT NEGLECT THOUGH IF WE RUN INTO COMPUTATIONAL TIME CONSTRAINTS
            self.update_defense(unit_enum_map, game_state)
            count += 1

