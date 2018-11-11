# This is where you build your AI for the Newtonian game.

from joueur.base_ai import BaseAI

# <<-- Creer-Merge: imports -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
# you can add additional import(s) here
from games.newtonian.util import *
import time
# <<-- /Creer-Merge: imports -->>

class AI(BaseAI):
    """ The AI you add and improve code inside to play Newtonian. """

    @property
    def game(self):
        """The reference to the Game instance this AI is playing.

        :rtype: games.newtonian.game.Game
        """
        return self._game # don't directly touch this "private" variable pls

    @property
    def player(self):
        """The reference to the Player this AI controls in the Game.

        :rtype: games.newtonian.player.Player
        """
        return self._player # don't directly touch this "private" variable pls

    def get_name(self):
        """ This is the name you send to the server so your AI will control the
            player named this string.

        Returns
            str: The name of your Player.
        """
        # <<-- Creer-Merge: get-name -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
        return "Newtonian Python Player" # REPLACE THIS WITH YOUR TEAM NAME
        # <<-- /Creer-Merge: get-name -->>

    def start(self):
        """ This is called once the game starts and your AI knows its player and
            game. You can initialize your AI here.
        """
        # <<-- Creer-Merge: start -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
        # replace with your start logic
        # <<-- /Creer-Merge: start -->>

    def game_updated(self):
        """ This is called every time the game's state updates, so if you are
        tracking anything you can update it here.
        """
        # <<-- Creer-Merge: game-updated -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
        # replace with your game updated logic
        # <<-- /Creer-Merge: game-updated -->>

    def end(self, won, reason):
        """ This is called when the game ends, you can clean up your data and
            dump files here if need be.

        Args:
            won (bool): True means you won, False means you lost.
            reason (str): The human readable string explaining why your AI won
            or lost.
        """
        # <<-- Creer-Merge: end -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
        # replace with your end logic
        # <<-- /Creer-Merge: end -->>
    def run_turn(self):
        """ This is called every time it is this AI.player's turn.

        Returns:
            bool: Represents if you want to end your turn. True means end your turn, False means to keep your turn going and re-call this function.
        """
        # <<-- Creer-Merge: runTurn -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.

        start = time.time()
        print('Turn %s' % self.game.current_turn)

        assigned_tiles.clear()
        assigned_physicist_machines.clear()

        interns = [unit for unit in self.player.units if unit.job.title == 'intern']
        physicists = [unit for unit in self.player.units if unit.job.title == 'physicist']
        managers = [unit for unit in self.player.units if unit.job.title == 'manager']

        #if self.game.current_turn % 2:
        if True:
            #surround_enemies(self, self.player.opponent)
            safe_fusion(self)
            print('Turn %s took %s seconds' % (self.game.current_turn, time.time() - start))
            return True

        # TODO: Remove when they fix act() not taking actions
        intern_grab_adjacent_ore(self, interns)
        physicist_act(self, physicists)
        grab_adjacent_refined(self, managers)

        paths = dict()
        for unit in interns:
            if unit.health <= 4:
                paths[unit] = path_to_goal(self, unit.tile, goal_spawn)
            elif unit.blueium_ore == unit.job.carry_limit:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_machine_resource('blueium'))
            elif unit.redium_ore == unit.job.carry_limit:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_machine_resource('redium'))
            else:
                #paths[unit] = path_to_goal(self, unit.tile, goal_adjacent_ore)
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_ore)
                if not paths[unit]:
                    paths[unit] = path_adjacent_goal(self, unit.tile, goal_conveyor)
        move_along_paths(self, paths, self.player.units)

        refined = list()
        for tile in self.game.tiles:
            if tile.redium or tile.blueium:
                refined.append(tile)
        for tile in refined:
            path = path_to_goal(self, tile,
                    lambda ai, tile: tile.unit and tile.unit.owner == self.player and tile.unit.job.title == 'manager' and (tile.unit.redium + tile.unit.blueium == 0),
                    lambda ai, d, fro, tile: not tile.is_wall and not tile.machine and not (tile.unit and tile.unit.owner != self.player))
            if path:
                chosen = path[-1].unit
                #print('chose %s! %s away' % (chosen.id, len(path)))
                paths[chosen] = list(reversed(path))
                if tile.machine:
                    paths[chosen] = paths[chosen][:-1]

        enemy_refined_managers = list()
        for unit in self.player.opponent.units:
            if unit.job.title == 'manager' and (unit.blueium or unit.redium):
                enemy_refined_managers.append(unit)
        for unit in enemy_refined_managers:
            path = path_to_goal(self, unit.tile,
                    lambda ai, tile: tile.unit and tile.unit.owner == self.player and tile.unit.job.title == 'physicist',
                    lambda ai, d, fro, tile: not tile.is_wall and not tile.machine and not (tile.unit and tile.unit.owner != self.player))
            if path and len(path) <= 7:
                print('chase!')
                chosen = path[-1].unit
                paths[chosen] = list(reversed(path))[:-1]


        for unit in physicists:
            paths[unit] = flee(self, unit)
            if paths.get(unit, None):
                continue
            elif unit.blueium:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_generator)
            elif unit.redium:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_generator)
            else:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_actable_machine)
                if not paths[unit]:
                    paths[unit] = path_adjacent_goal(self, unit.tile, goal_stun_attack(unit))
                if not paths[unit]:
                    paths[unit] = path_adjacent_goal(self, unit.tile, goal_enemy)
                if paths[unit]:
                    for neighbor in paths[unit][-1].get_neighbors():
                        if neighbor.machine:
                            assigned_physicist_machines[neighbor] = unit

        move_along_paths(self, paths, self.player.units)

        for unit in managers:
            paths[unit] = flee(self, unit)
            if paths.get(unit, None):
                continue
            elif unit.blueium:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_generator)
            elif unit.redium:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_generator)
            else:
                paths[unit] = path_adjacent_goal(self, unit.tile, goal_stun_attack(unit))
                if not paths[unit]:
                    paths[unit] = path_adjacent_goal(self, unit.tile, goal_enemy)
        move_along_paths(self, paths, self.player.units)

        intern_grab_adjacent_ore(self, interns)
        intern_deposit_ore(self, interns)
        physicist_act(self, physicists)
        grab_adjacent_refined(self, managers)
        drop_refined(self, managers)

        attack_adjacent(self, self.player.units)

        print('Turn %s took %s seconds' % (self.game.current_turn, time.time() - start))

        return True
        # <<-- /Creer-Merge: runTurn -->>

    # <<-- Creer-Merge: functions -->> - Code you add between this comment and the end comment will be preserved between Creer re-runs.
    # if you need additional functions for your AI you can add them here
    # <<-- /Creer-Merge: functions -->>
