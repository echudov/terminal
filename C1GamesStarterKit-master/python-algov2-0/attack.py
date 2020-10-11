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

    def __str__(self):
        return "Player ID: " + str(self.player_id) + "; Attack Type: " + str(self.attack_type) + "; DMG To Defenses " + \
            str(self.damage_dealt_to_defense) + "; DMG To Troops " + str(self.damage_dealt_to_troops) + \
            "; Breaches: " + str(self.breaches) + "; Self Destructs: " + str(self.self_destructs) + \
            "; Total Cost: " + str(self.total_cost)