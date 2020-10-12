from region import Region
def region_print_test():
    region = Region(
            unit_enum_map=None,
            vertices=[(7, 6), (20, 6), (14, 0), (13, 0)],
            player_id=0,
            incoming_edges=[((7, 6), (20, 6))],
            outgoing_edges=[],
            breach_edges=[((7, 6), (13, 0)), ((13, 0), (14, 0)), ((14, 0), (20, 6))],
            map=None,
            damage_regions=None,
        )
    print(region.grid_type)

if __name__ == '__main__':
    region_print_test()