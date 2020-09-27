
# helper for left_or_right
def find_damage_at_endpoint_from_start(start_point, game_state):
    edge = game_state.game_map.TOP_RIGHT
    if start_point[0] == 14:
        edge = game_state.game_map.TOP_LEFT
    path = game_state.find_path_to_edge(start_point, find_path_to_edge)
    return max_damage(path[-1], game_state)

# choose from either [13,0] or [14,0] to deploy the scouts
# depending on the defense focus of enemy
# returns 0 if choose [13, 0];
# returns 1 if choose [14, 0];
# returns -1 if either (i.e same)
def choose_start_point (game_state):
    start1 = [13, 0]
    start2 = [14, 0]
    damage1 = find_damage_at_endpoint_from_start(start1, game_state)
    damage2 = find_damage_at_endpoint_from_start(start2, game_state)
    if damage1 == damage2:
        return -1
    elif damage1 < damage2:
        return 0
    else:
        return 1



