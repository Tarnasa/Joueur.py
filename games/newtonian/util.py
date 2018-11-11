from collections import deque, defaultdict

assigned_tiles = dict()
assigned_physicist_machines = dict()
assigned_manager_machines = dict()

def _neighbor_func(ai, tile):
    for neighbor in tile.get_neighbors():
        if not tile.is_wall and not tile.machine and not tile.unit:
            yield neighbor

def bfs(ai, start_tile, neighbor_func=_neighbor_func):
    frontier = deque([0, start_tile])
    seen = set()
    while frontier:
        d, top = frontier.popleft()
        if top in seen:
            continue
        seen.add(neighbor)
        yield d, top
        for neighbor in neighbor_func(ai, top):
            frontier.append((d + 1, neighbor))

def pathable_basic(ai, d, from_tile, to_tile):
    return not to_tile.is_wall and not to_tile.machine and not to_tile.unit

def pathable_through(ai, d, from_tile, to_tile):
    return not to_tile.is_wall and not to_tile.machine

def pathable_through_player(player):
    def f(ai, d, from_tile, to_tile):
        return not to_tile.is_wall and not to_tile.machine and (not to_tile.unit or (to_tile.unit.owner == player and to_tile.unit.moves and not to_tile.unit.stun_time))
    return f

def bfs_pathable(ai, start_tile, pathable=pathable_basic):
    frontier = deque([(0, start_tile)])
    seen = set([start_tile])
    while frontier:
        d, top = frontier.popleft()
        yield d, top
        for neighbor in top.get_neighbors():
            if neighbor not in seen and pathable(ai, d + 1, top, neighbor):
                frontier.append((d + 1, neighbor))
                seen.add(neighbor)

def build_path(came_from, head):
    path = deque()
    while head:
        path.appendleft(head)
        head = came_from.get(head, None)
    return path

def _pathable_through_own(ai, d, from_tile, to_tile):
    #return not to_tile.is_wall and not to_tile.machine and (not to_tile.unit or to_tile.unit.owner == ai.player)
    #return not to_tile.is_wall and not to_tile.machine and (not to_tile.unit or (d > 5 and to_tile.unit.owner == ai.player))
    return not to_tile.is_wall and not to_tile.machine and not to_tile.unit
def path_to_goal(ai, start_tile, goal_func, pathable=_pathable_through_own):
    came_from = dict()
    def _pathable(ai, d, from_tile, to_tile):
        if pathable(ai, d, from_tile, to_tile):
            #print('%s,%s -> %s,%s' % (from_tile.x, from_tile.y, to_tile.x, to_tile.y))
            #if came_from.get(from_tile, None) == to_tile:
            #    raise Exception('NOPE')
            came_from[to_tile] = from_tile
            return True
        return False
    for d, tile in bfs_pathable(ai, start_tile, _pathable):
        if goal_func(ai, tile) and tile not in assigned_tiles:
            assigned_tiles[tile] = start_tile
            return build_path(came_from, tile)
    return []

def path_adjacent_goal(ai, start_tile, goal_func, pathable=_pathable_through_own):
    if goal_func(ai, start_tile):
        return [start_tile]
    came_from = {start_tile: None}
    frontier = deque([(0, start_tile)])
    while frontier:
        d, top = frontier.popleft()
        for neighbor in top.get_neighbors():
            if neighbor not in came_from:
                is_pathable = pathable(ai, d + 1, top, neighbor)
                is_goal = neighbor not in assigned_tiles and goal_func(ai, neighbor)
                if is_goal:
                    came_from[neighbor] = top
                    assigned_tiles[top] = start_tile
                    return build_path(came_from, top)
                if is_pathable:
                    frontier.append((d + 1, neighbor))
                    came_from[neighbor] = top
    return []

def or_goals(goal1, goal2):
    def f(ai, tile):
        return goal1(ai, tile) or goal2(ai, tile)
    return f

def and_goals(goal1, goal2):
    def f(ai, tile):
        return goal1(ai, tile) and goal2(ai, tile)
    return f

def goal_enemy(ai, tile):
    return tile.unit and tile.unit.owner != ai.player

def goal_stun(attacker):
    def f(ai, tile):
        return tile.unit and tile.unit.owner != ai.player and can_stun(attacker, tile.unit)
    return f

def goal_stun_attack(attacker):
    def f(ai, tile):
        return tile.unit and tile.unit.owner != ai.player and (tile.unit.stun_time or can_stun(attacker, tile.unit))
    return f

def goal_ore(ai, tile):
    return (tile.blueium_ore or tile.redium_ore) and not tile.machine

def goal_conveyor(ai, tile):
    return tile.type == 'conveyor'

def goal_machine_resource(resource):
    def f(ai, tile):
        return tile.machine and tile.machine.ore_type == resource
    return f

def goal_unrefined_machine(ai, tile):
    return tile.machine and \
            not tile.blueium and \
            not tile.redium and \
            tile not in assigned_physicist_machines

def goal_unored_machine(ai, tile):
    return tile.machine and not tile.blueium_ore and not tile.redium_ore

def goal_actable_machine(ai, tile):
    return tile.machine and ((
        tile.machine.ore_type == 'blueium' and
        tile.blueium_ore >= tile.machine.refine_input
        ) or (
            tile.machine.ore_type == 'redium' and
            tile.redium_ore >= tile.machine.refine_input
            ) or (
                tile.machine.worked > 0
                ))

def goal_refined(ai, tile):
    return tile.blueium or tile.redium

def goal_generator(ai, tile):
    return tile.owner == ai.player and tile.type == 'generator'

def goal_spawn(ai, tile):
    return tile.owner == ai.player and tile.type == 'spawn'

def goal_intern_full(unit):
    if unit.blueium_ore == unit.job.carry_limit:
        return goal_machine_resource('blueium')
    elif unit.redium_ore == unit.job.carry_limit:
        return goal_machine_resource('redium')
    else:
        return goal_ore
    # TODO: goal_conveyor

def goal_intern_partial(unit):
    if unit.blueium_ore:
        return goal_machine_resource('blueium')
    elif unit.redium_ore:
        return goal_machine_resource('redium')
    else:
        return goal_conveyor
    # TODO: goal_conveyor and goal_ore

def move_along_path(ai, path, unit):
    i = path.index(unit.tile)
    if i < len(path)-1:
        step = path[i + 1]
        if not step.unit and unit.move(step):
            return True
        if step.is_wall:
            print('WALLLL %s of %s ?????????????' % (i+1, len(path)))
            print('unit at %s,%s step at %s,%s' % (unit.tile.x, unit.tile.y, step.x, step.y))
            for tile in path:
                print('%s,%s wall %s' % (tile.x, tile.y, tile.is_wall))
    return False

def move_along_paths(ai, paths, units):
    moved = True
    while moved:
        moved = False
        for unit in units:
            path = paths.get(unit, None)
            if not path or unit.moves <= 0 or unit.stun_time > 0:
                continue
            if move_along_path(ai, path, unit):
                moved = True

def can_stun(attacker, attacked):
    if attacker.job.title == 'intern' and attacked.job.title == 'physicist':
        return True
    if attacker.job.title == 'physicist' and attacked.job.title == 'manager':
        return True
    if attacker.job.title == 'manager' and attacked.job.title == 'intern':
        return True
    return False

def stun_adjacent(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.unit and neighbor.unit.owner != ai.player:
                if not neighbor.unit.stun_time and can_stun(unit, neighbor.unit):
                    if unit.act(neighbor):
                        break

def attack_adjacent(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.unit and neighbor.unit.owner != ai.player:
                if not neighbor.unit.stun_time and can_stun(unit, neighbor.unit):
                    if unit.act(neighbor):
                        break
                if unit.attack(neighbor):
                    break

def intern_grab_adjacent_ore(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        if unit.blueium_ore + unit.redium_ore >= unit.job.carry_limit:
            continue
        for neighbor in unit.tile.get_neighbors() + [unit.tile]:
            if not neighbor.machine:
                if neighbor.blueium_ore:
                    if unit.pickup(neighbor, -1, 'blueium ore'):
                        break
                if neighbor.redium_ore:
                    if unit.pickup(neighbor, -1, 'redium ore'):
                        break

def intern_deposit_ore(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.machine and neighbor.machine.ore_type == 'blueium':
                if unit.blueium_ore:
                    if unit.drop(neighbor, -1, 'blueium ore'):
                        break
            if neighbor.machine and neighbor.machine.ore_type == 'redium':
                if unit.redium_ore:
                    if unit.drop(neighbor, -1, 'redium ore'):
                        break

def physicist_act(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.machine and neighbor.machine.worked:
                if unit.act(neighbor):
                    break
            if neighbor.machine and neighbor.machine.ore_type == 'blueium':
                if neighbor.blueium_ore >= neighbor.machine.refine_input:
                    if unit.act(neighbor):
                        break
            if neighbor.machine and neighbor.machine.ore_type == 'redium':
                if neighbor.redium_ore >= neighbor.machine.refine_input:
                    if unit.act(neighbor):
                        break

def grab_adjacent_refined(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        if unit.blueium + unit.redium >= unit.job.carry_limit:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.blueium:
                if unit.pickup(neighbor, -1, 'blueium'):
                    break
            if neighbor.redium:
                if unit.pickup(neighbor, -1, 'redium'):
                    break

def drop_refined(ai, units):
    for unit in units:
        if unit.acted or unit.stun_time:
            continue
        for neighbor in unit.tile.get_neighbors():
            if neighbor.owner == ai.player and neighbor.type == 'generator':
                if unit.blueium:
                    print('drop!')
                    if unit.drop(neighbor, -1, 'blueium'):
                        break
                if unit.redium:
                    print('drop!')
                    if unit.drop(neighbor, -1, 'redium'):
                        break

def flee(ai, unit):
    if unit.health < 4:
        path = path_to_goal(ai, unit.tile, goal_spawn)
        if len(path) / 5 <= 3:
            print('flee-----------------------------------------------------')
            return path
    return []

def multi_bfs(ai, start_tiles, goal_func, pathable=_pathable_through_own, max_distance=999):
    for start_tile in start_tiles:
        if goal_func(ai, start_tile):
            yield [start_tile]
    came_from = {start_tile: None for start_tile in start_tiles}
    frontier = deque([(0, start_tile) for start_tile in start_tiles])
    while frontier:
        d, top = frontier.popleft()
        if d > max_distance:
            break
        for neighbor in top.get_neighbors():
            if neighbor not in came_from:
                is_pathable = pathable(ai, d + 1, top, neighbor)
                is_goal = goal_func(ai, neighbor)
                if is_goal:
                    came_from[neighbor] = top
                    yield build_path(came_from, neighbor)
                if is_pathable:
                    frontier.append((d + 1, neighbor))
                    came_from[neighbor] = top

# multi-agent bfs
# then assign units to attack nearests in groups of three
# TODO: Does not work, because all of our units will try to move to the same location
def surround_enemies(ai, enemy_player):
    adjacent_to_enemy_interns = set()
    adjacent_to_enemy = set()
    enemy_paths = list()
    for unit in enemy_player.units:
        if unit.job.title == 'intern':
            for tile in unit.tile.get_neighbors():
                if not tile.is_wall and not tile.machine and (not tile.unit or tile.unit.owner != enemy_player):
                    adjacent_to_enemy_interns.add(tile)
            path = path_adjacent_goal(ai, unit.tile, goal_intern_partial(unit), pathable_basic)
            if path:
                enemy_paths.append(path)
        else:
            for tile in unit.tile.get_neighbors():
                if not tile.is_wall and not tile.machine and (not tile.unit or tile.unit.owner != enemy_player):
                    adjacent_to_enemy.add(tile)
    paths = dict()
    possible_attackers = set(enemy_player.opponent.units)
    attackers = list()
    while adjacent_to_enemy_interns:
        path = next(multi_bfs(ai, adjacent_to_enemy_interns,
                lambda ai, tile: tile.unit and tile.unit.owner != enemy_player and tile.unit not in attackers,
                pathable_basic, 7), None)
        if path:
            attacker = path[-1].unit
            paths[attacker] = list(reversed(path))
            attackers.append(attacker)
            possible_attackers.remove(attacker)
            adjacent_to_enemy_interns.remove(path[0])
        else:
            break
    for d in range(15):
        if not possible_attackers:
            break
        future_tiles = set()
        i = d*5+1
        for path in enemy_paths:
            if i < len(path):
                future_tiles.add(path[d*5+1])
            else:
                future_tiles.add(path[-1])
        while future_tiles:
            path = next(multi_bfs(ai, future_tiles,
                lambda ai, tile: tile.unit and tile.unit.owner != enemy_player and tile.unit not in attackers,
                pathable_through_player(ai.player), d*5+2), None)
            if path:
                attacker = path[-1].unit
                paths[attacker] = list(reversed(path))
                attackers.append(attacker)
                possible_attackers.remove(attacker)
                #adjacent_to_enemy_interns.remove(path[0])
            else:
                break
    while adjacent_to_enemy:
        path = next(multi_bfs(ai, adjacent_to_enemy,
                lambda ai, tile: tile.unit and tile.unit.owner != enemy_player and tile.unit not in attackers,
                pathable_basic, 7), None)
        if path:
            attacker = path[-1].unit
            paths[attacker] = list(reversed(path))
            attackers.append(attacker)
            possible_attackers.remove(attacker)
            adjacent_to_enemy.remove(path[0])
        else:
            break
    move_along_paths(ai, paths, attackers)
    attack_adjacent(ai, attackers)

# Get the next needed action to get points
# (Gather ore, bring ore, process ore, pickup refined, return refined)
def get_stage(ai):
    process = False
    for unit in ai.player.units:
        if unit.blueium or unit.redium:
            return 'return'
    for tile in ai.game.tiles:
        if tile.blueium or tile.redium:
            return 'refined'
        if tile.machine and (tile.blueium_ore >= tile.machine.refine_input or tile.redium_ore >= tile.machine.refine_input):
            process = True
    if process:
        return 'process'
    bring = False
    for unit in ai.player.units:
        if unit.blueium_ore == unit.job.carry_limit or unit.redium_ore == unit.job.carry_limit:
            bring = True
    if bring:
        return 'bring'
    return 'gather'
        
# Perform the current stage, but stun opposing
def safe_fusion(ai):
    stage = get_stage(ai)
    print('STAGE %s' % stage)
    if stage == 'gather':
        safe_fusion_gather(ai)
    elif stage == 'bring':
        safe_fusion_bring(ai)
    elif stage == 'process':
        safe_fusion_process(ai)
    elif stage == 'refined':
        safe_fusion_refined(ai)
    elif stage == 'return':
        safe_fusion_return(ai)
    else:
        print("BAD STAGE")
        safe_fusion_gather(ai)

# Intern do stuff, rest stun enemies
def safe_fusion_gather(ai):
    intern_tiles = [unit.tile for unit in ai.player.units if unit.job.title == 'intern']
    path = next(multi_bfs(ai, intern_tiles, goal_ore), None)
    if not path:
        path = next(multi_bfs(ai, intern_tiles, goal_conveyor), None)
    paths = dict()
    if path:
        unit = path[0].unit
        intern_grab_adjacent_ore(ai, [unit])
        if get_stage(ai) == 'bring':
            safe_fusion_bring(ai)
            return
        paths[unit] = path
        if path[-1].redium_ore or path[-1].blueium_ore:
            paths[unit] = list(path)[:-1]
        for tile in path:
            print('%s,%s' % (tile.x, tile.y))
        move_along_paths(ai, paths, [unit])
        intern_grab_adjacent_ore(ai, [unit])
    super_stun(ai, [unit for unit in ai.player.units if not paths.get(unit, None)])

def safe_fusion_bring(ai):
    intern = next((unit for unit in ai.player.units if unit.blueium_ore or unit.redium_ore), None)
    paths = dict()
    if intern:
        resource = 'blueium' if intern.blueium_ore else 'redium'
        paths[intern] = path_adjacent_goal(ai, intern.tile, goal_machine_resource(resource))
        move_along_paths(ai, paths, [intern])
        intern_deposit_ore(ai, [intern])
    else:
        print('failed to bring!')
    super_stun(ai, [unit for unit in ai.player.units if not paths.get(unit, None)])

def safe_fusion_process(ai):
    tiles = [unit.tile for unit in ai.player.units if unit.job.title == 'physicist' and not unit.stun_time]
    path = next(multi_bfs(ai, tiles, goal_actable_machine), None)
    paths = dict()
    if path:
        unit = path[0].unit
        paths[unit] = path
        move_along_paths(ai, paths, [unit])
        physicist_act(ai, [unit])
    super_stun(ai, [unit for unit in ai.player.units if not paths.get(unit, None)])

def safe_fusion_refined(ai):
    tiles = [unit.tile for unit in ai.player.units if unit.job.title == 'manager' and not unit.stun_time]
    path = next(multi_bfs(ai, tiles, goal_refined), None)
    paths = dict()
    if path:
        unit = path[0].unit
        grab_adjacent_refined(ai, [unit])
        paths[unit] = path
        while unit.moves:
            if not move_along_path(ai, path, unit):
                break
            grab_adjacent_refined(ai, [unit])
            if get_stage(ai) == 'return':
                print('SUPER RETURN')
                safe_fusion_return(ai)
                return
        grab_adjacent_refined(ai, [unit])
    else:
        print('no manager')
    super_stun(ai, [unit for unit in ai.player.units if not paths.get(unit, None)])

def safe_fusion_return(ai):
    unit = next((unit for unit in ai.player.units if unit.blueium or unit.redium), None)
    paths = dict()
    if unit:
        paths[unit] = path_adjacent_goal(ai, unit.tile, goal_generator)
        move_along_paths(ai, paths, [unit])
        drop_refined(ai, [unit])
    else:
        print('failed to return!')
    super_stun(ai, [unit for unit in ai.player.units if not paths.get(unit, None)])


def stun_enemies(ai, paths):
    claimed = set()
    unclaimed = lambda ai, tile: tile not in claimed
    for unit in ai.player.units:
        if not paths.get(unit, None):
            paths[unit] = path_adjacent_goal(ai, unit.tile, and_goals(goal_stun(unit), unclaimed))
        if not paths.get(unit, None):
            paths[unit] = path_adjacent_goal(ai, unit.tile, goal_stun_attack(unit))
    move_along_paths(ai, paths, ai.player.units)
    attack_adjacent(ai, ai.player.units)


def multi_path_to_goal_claimed(ai, start_tiles, goal_func, pathable=pathable_basic, max_distance=999):
    start_tiles = list(start_tiles)
    claimed = set()
    while start_tiles:
        path = next(multi_bfs(ai, start_tiles,
            and_goals(goal_func, lambda ai, tile: tile not in claimed),
            lambda ai, d, fro, tile: tile not in steps and pathable(ai, d, fro, tile), max_distance), None)
        if path:
            yield path
            if len(path) > 6:
                steps.add(path[6])
            start_tiles.remove(path[0])
            claimed.add(path[-1])
        else:
            break

def multi_path_to_goal(ai, start_tiles, goal_func, pathable=pathable_basic, max_distance=999):
    start_tiles = list(start_tiles)
    while start_tiles:
        #path = next(multi_bfs(ai, start_tiles, goal_func, pathable, max_distance), None)
        path = next(multi_bfs(ai, start_tiles, goal_func,
            lambda ai, d, fro, tile: tile not in steps and pathable(ai, d, fro, tile), max_distance), None)
        if path:
            yield path
            if len(path) > 6:
                steps.add(path[6])
            start_tiles.remove(path[0])
        else:
            break

def multi_path_to_goal_both(ai, start_tiles, goal_func, pathable=pathable_basic, max_distance=999):
    start_tiles = list(start_tiles)
    for path in multi_path_to_goal_claimed(ai, start_tiles, goal_func, pathable, max_distance):
        start_tiles.remove(path[0])
        yield path
    for path in multi_path_to_goal(ai, start_tiles, goal_func, pathable, max_distance):
        yield path

def super_stun(ai, units):
    stun_enemies(ai, {unit: [] for unit in ai.player.units if unit not in units})
    return
    global steps
    steps = set()
    if ai.game.current_turn % 2 == 0:
        print('LAME')
        stun_enemies(ai, {unit: [] for unit in ai.player.units if unit not in units})
        return
    paths = dict()
    for title in ['manager', 'physicist', 'intern']:
        tiles = [unit.tile for unit in units if unit.job.title == title]
        if not tiles:
            continue
        for path in multi_path_to_goal_both(ai, tiles, goal_stun(tiles[0].unit)):
            for tile in path:
                print('new %s,%s' % (tile.x, tile.y))
            unit = path[0].unit
            paths[unit] = path
    for title in ['manager', 'physicist', 'intern']:
        tiles = [unit.tile for unit in units if unit.job.title == title and unit not in paths]
        if not tiles:
            continue
        for path in multi_path_to_goal_both(ai, tiles, goal_stun_attack(tiles[0].unit)):
            unit = path[0].unit
            paths[unit] = path
    stun_adjacent(ai, ai.player.units)
    move_along_paths(ai, paths, ai.player.units)
    attack_adjacent(ai, ai.player.units)

# Find path from mineral to intern
# For all tiles with only two neighbors
# That tile becomes a target for one of your own units
# Then run multi-bfs again to find which unit to go to which of these targets?
def block_enemy(ai):
    pass

# Find path from mineral to intern
# For all tiles with only two neighbors
# That is a target

# Find all paths from all machines to all ores
# When paths cross, those tiles are more valuable
