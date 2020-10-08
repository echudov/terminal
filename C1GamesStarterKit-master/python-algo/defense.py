import gamelib
import numpy as np
from region import Region

class Defense:

    def __init__(self, player_id: int, game_state: gamelib.GameState):
        """
        Initializes defense with multiple predetermined regions.
        @param player_id: Number representing which player this defense is for 0 - us, 1 - opponent
        @param game_state: passes current game_state as GameState object
        """
        self.regions = {}
        self.player_id = player_id
        self.damage_regions = np.zeros(shape=(game_state.map.ARENA_SIZE, game_state.map.HALF_ARENA))
        if player_id == 0:
            self.create_our_regions()
        else:
            self.create_enemy_regions()

    def create_our_regions(self):
        self.regions[0] = Region([(0, 13), (7, 13), (7, 6)], self.player_id,
                                 incoming_edges=[((0, 13), (7, 13)), ((7, 13), (7, 6))],
                                 outgoing_edges=[],
                                 breach_edges=[((0, 13), (7, 6))],
                                 map=None,
                                 damage_regions=self.damage_regions)
        self.regions[1] = Region([(27, 13), (20, 13), (20, 6)], self.player_id,
                                 incoming_edges=[((20, 13), (27, 13)), ((20, 13), (20, 6))],
                                 outgoing_edges=[],
                                 breach_edges=[((27, 13), (20, 6))],
                                 map=None,
                                 damage_regions=self.damage_regions)
        self.region[2] = Region([(7, 6), (7, 13), (14, 13)], self.player_id,
                                 incoming_edges=[((7, 6), (7, 13)), ((7, 13), (14, 13))],
                                 outgoing_edges=[((7, 6), (14, 13))],
                                 breach_edges=[],
                                 map=None,
                                 damage_regions=self.damage_regions)
        self.region[3] = Region([(13, 13), (20, 13), (20, 6)], self.player_id,
                                 incoming_edges=[((13, 13), (20, 13)), ((20, 13), (20, 6))],
                                 outgoing_edges=[((13, 13), (20, 6))],
                                 breach_edges=[],
                                 map=None,
                                 damage_regions=self.damage_regions)

        self.region[4] = Region([(7, 6), (13, 12), (14, 12), (20, 6)], self.player_id,
                                incoming_edges=[((7, 6), (13, 12)), ((13, 12), (14, 12)), ((14, 12), (20, 6))],
                                outgoing_edges=[((7, 6), (20, 6))],
                                breach_edges=[],
                                map=None,
                                damage_regions=self.damage_regions)
        self.region[5] = Region([(7, 6), (20, 6), (14, 0), (13, 0)], self.player_id,
                                incoming_edges=[((7, 6), (20, 6))],
                                outgoing_edges=[],
                                breach_edges=[((7, 6), (13, 0)), ((13, 0), (14, 0)), ((14, 0), (20, 6))],
                                map=None,
                                damage_regions=self.damage_regions)

    def create_enemy_regions(self):
        self.regions[0] = Region([(0, 14), (7, 14), (7, 21)], self.player_id,
                                 incoming_edges=[((0, 14), (7, 14)), ((7, 14), (7, 21))],
                                 outgoing_edges=[],
                                 breach_edges=[((0, 14), (7, 21))],
                                 map=None,
                                 damage_regions=self.damage_regions)
        self.regions[1] = Region([(20, 14), (20, 21), (27, 14)], self.player_id,
                                 incoming_edges=[((20, 14), (20, 21)), ((20, 14), (27, 14))],
                                 outgoing_edges=[],
                                 breach_edges=[((20, 21), (27, 14))],
                                 map=None,
                                 damage_regions=self.damage_regions)
        self.region[2] = Region([(7, 14), (7, 21), (14, 14)], self.player_id,
                                incoming_edges=[((7, 14), (14, 14)), ((7, 14), (7, 21))],
                                outgoing_edges=[((7, 21), (14, 14))],
                                breach_edges=[],
                                map=None,
                                damage_regions=self.damage_regions)
        self.region[3] = Region([(13, 14), (20, 21), (20, 14)], self.player_id,
                                incoming_edges=[((13, 14), (20, 14)), ((20, 14), (20, 21))],
                                outgoing_edges=[((13, 14), (20, 21))],
                                breach_edges=[],
                                map=None,
                                damage_regions=self.damage_regions)

        self.region[4] = Region([(7, 21), (13, 15), (14, 15), (20, 21)], self.player_id,
                                incoming_edges=[((7, 21), (13, 15)), ((13, 15), (14, 15)), ((14, 15), (20, 21))],
                                outgoing_edges=[((7, 21), (20, 21))],
                                breach_edges=[],
                                map=None,
                                damage_regions=self.damage_regions)
        self.region[5] = Region([(7, 21), (13, 27), (14, 27), (20, 21)], self.player_id,
                                incoming_edges=[((7, 21), (20, 21))],
                                outgoing_edges=[],
                                breach_edges=[((7, 21), (13, 27)), ((13, 27), (14, 27)), ((14, 27), (20, 21))],
                                map=None,
                                damage_regions=self.damage_regions)

    def update_regions(self, game_state):
        for region in self.regions.values():
            region.update_structures(game_state.map)