import gamelib
import numpy as np
from region import Region


class Defense:
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
        if player_id == 0:
            self.create_our_regions(unit_enum_map)
        else:
            self.create_enemy_regions(unit_enum_map)
        self.coordinate_regions = [[[] for y in range(14)] for x in range(28)]
        self.history = []
        self.units = {
            unit_enum_map["TURRET"]: set(),
            unit_enum_map["FACTORY"]: set(),
            unit_enum_map["WALL"]: set(),
        }
        self.states = {}

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
            for coordinate in sum(self.regions[i].coordinates):
                self.coordinate_regions[
                    self.offset_coord(self.offset_coord(coordinate))
                ].append(i)

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
            unit_enum_map["TURRET"]: set(),
            unit_enum_map["FACTORY"]: set(),
            unit_enum_map["WALL"]: set(),
        }
        for i, region in self.regions.items():
            region.update_structures(unit_enum_map, game_state.game_map)
            # iterate through the units to add to the overall game state
            # we use a set because there is overlap of regions, we don't want to double count units
            # find the states of region i
            self.states[i] = region.calculate_region_states(units)
        for x in range(game_state.ARENA_SIZE):
            for y in range(game_state.HALF_ARENA):
                unit = game_state.game_map[x, y]
                if not unit:
                    continue
                unit = unit[0]
                if (
                    unit.unit_type == unit_enum_map["WALL"]
                    or unit.unit_type == unit_enum_map["TURRET"]
                    or unit.unit_type == unit_enum_map["FACTORY"]
                ):
                    self.units[unit.unit_type] = unit

    def get_defense_undefended_tiles(self):
        """
        Updates defense tiles
        @return: list of undefended tiles
        """
        return {i: self.states[i]["UNDEFENDED TILES"] for i in range(self.region_count)}

    def calculate_total_cost(
        self, unit_enum_map: dict, defensive_only=True, health_prorated=True
    ):
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
