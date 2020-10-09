from region import Region
def region_print_test():
    region = Region(
            [(7, 6), (20, 6), (14, 0), (13, 0)],
            0,
            incoming_edges=[((7, 6), (20, 6))],
            outgoing_edges=[],
            breach_edges=[((7, 6), (13, 0)), ((13, 0), (14, 0)), ((14, 0), (20, 6))],
            map=None,
            damage_regions=None,
        )
    print(sorted(region.all_boundaries))

if __name__ == '__main__':
    region_print_test()