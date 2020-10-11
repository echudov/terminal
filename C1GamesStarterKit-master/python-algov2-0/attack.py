class Attack:

    def __init__(self, player_id, attack_type, cost):
        # String representing the attack type
        # "DEMOLISHER LINE"
        # "SCOUT SPAM"
        # "DEMOLISHER SCOUT"
        # "DEMOLISHER INTERCEPTOR"
        # "INTERCEPTOR DEFENSE"
        self.player_id = player_id
        self.attack_type = attack_type
        self.damage_dealt_to_defense = 0
        self.damage_dealt_to_troops = 0
        self.breaches = []
        self.self_destructs = []
        self.total_cost = cost

    def damage_per_point(self):
        return ( self.damage_dealt_to_defense + self.damage_dealt_to_troops ) / self.total_cost

    def cost_per_breach(self):
        if not self.breaches:
            return self.total_cost / len(self.breaches)
        else:
            return 1000000000
