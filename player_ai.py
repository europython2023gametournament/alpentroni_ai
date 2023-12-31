# SPDX-License-Identifier: BSD-3-Clause

import numpy as np

from supremacy.vehicles import Jet, Vehicle

# This is your team name
CREATOR = "alpentroni"


# This is the AI bot that will be instantiated for the competition
class PlayerAi:
    def __init__(self):
        self.team = CREATOR  # Mandatory attribute

        # Record the previous positions of all my vehicles
        self.previous_positions = {}
        self.tank_target_positions = {}
        # Record the number of tanks and ships I have at each base
        self.ntanks = {}
        self.nships = {}
        self.recon = False
        self.protector_tanks = {}
        self.recon_position = [20, 20]
        self.recon_heading = 0
        self.next_recon_height = 20
        self.recon_alive = False

    def __closest_point(self, points, reference_point):
        if points:
            distances = [np.sqrt((x2 - reference_point[0]) ** 2 + (y2 - reference_point[1]) ** 2) for x2, y2 in points]
            closest = points[distances.index(min(distances))]
            return closest
        else:
            return None

    def __within_range(self, point1, point2, r):
        distance = np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
        return distance <= r

    def __is_heading_towards(self, pt1, pt2, direction):
        dx = pt2[0] - pt1[0]
        dy = pt2[1] - pt1[1]

        angle = (np.arctan2(dy, dx) * (180 / np.pi) - 90) % 360

        return abs(direction - angle) <= 180

    def __target_in_range(self, info, jet):
        for name in info:
            if name != self.team:
                target = []
                if "bases" in info[name]:
                    target += info[name]["bases"]
                if "ships" in info[name]:
                    target += info[name]["ships"]
                for t in target:
                    if self.__within_range([jet.x, jet.y], [t.x, t.y], 20):
                        return [t.x, t.y]
        return None

    def __defense_in_range(self, info, mine):
        for name in info:
            if name != self.team:
                defense = []
                if "tanks" in info[name]:
                    defense += info[name]["tanks"]
                if "jets" in info[name]:
                    defense += info[name]["jets"]
                for d in defense:
                    if self.__within_range([mine.x, mine.y], [d.x, d.y], 20):
                        return [d.x, d.y]
        return None

    def __ship_near_base(self, ship, bases):
        for base in bases:
            if ship.get_distance(base.x, base.y) < 40:
                return True
        return False

    def __check_bases(self, ship, info):
        for team in info:
            if "bases" in info[team]:
                if self.__ship_near_base(ship, info[team]["bases"]):
                    return True
        return False

    def __control_jet(self, info: dict, jet, game_map: np.ndarray):
        x = int(jet.x)
        y = int(jet.y)
        """
        :param info : dict
            A dictionary containing all the information about the game.
            The structure is as follows:
            {
                "team_name_1": {
                    "bases": [base_1, base_2, ...],
                    "tanks": [tank_1, tank_2, ...],
                    "ships": [ship_1, ship_2, ...],
                    "jets": [jet_1, jet_2, ...],
                },
                "team_name_2": {
                    ...
                },
                ...
            }
        :param jet:
        :param game_map:
        :return:
        """

        target = self.__target_in_range(info, jet)
        defense = self.__defense_in_range(info, jet)
        # Check if it will hit a defensive obstacle
        if target:
            # If there's a target in range, attack it, even as recon jet
            jet.goto(*target)
        elif defense:
            if self.__is_heading_towards(defense, [jet.x, jet.x], jet['heading']):
                # If there's an obstacle ahead, turn 140 degrees to the right
                jet.set_heading(jet['heading'] + 140)
        else:
            # go to closest base, which is not the base of the team
            bases = []
            for team in info:
                if team == self.team:
                    continue
                if "bases" in info[team]:
                    for base in info[team]["bases"]:
                        bases.append([base.x, base.y])
            closest_base = self.__closest_point(bases, [jet.x, jet.y])
            if closest_base:
                jet.goto(*closest_base)
        # Continue on path

    def __move_tank(self, tank, target=None):
        if (tank.uid in self.previous_positions) and (not tank.stopped):
            if all(tank.position == self.previous_positions[tank.uid]["position"]):
                tank.set_heading(np.random.random() * 360.0)
            # Else, if there is a target, go to the target
            elif target is not None:
                tank.goto(*target)
        # Store the previous position of this tank for the next time step
        self.previous_positions[tank.uid] = {"position": tank.position, "moved": True}

    def __reset_moved(self):
        for key, value in self.previous_positions.items():
            self.previous_positions[key]["moved"] = False

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        # Get information about my team
        myinfo = info[self.team]
        self.__reset_moved()
        tank_uids = []
        if "tanks" in myinfo:
            for tank in myinfo["tanks"]:
                tank_uids.append(tank.uid)
        ship_uids = []
        if "ships" in myinfo:
            for ship in myinfo["ships"]:
                ship_uids.append(ship.uid)

        # Iterate through all my bases (vehicles belong to bases)
        for base in myinfo["bases"]:
            # If this is a new base, initialize the tank & ship counters
            if base.uid not in self.ntanks:
                self.ntanks[base.uid] = []
            if base.uid not in self.nships:
                self.nships[base.uid] = []
            if "tanks" in myinfo:
                self.ntanks[base.uid] = [item for item in self.ntanks[base.uid] if item in tank_uids]
                counter = 0
                for tank in myinfo["tanks"]:
                    if tank.uid in self.ntanks[base.uid]:
                        if counter > 3:
                            self.__move_tank(tank)
                        else:
                            if tank.uid in self.tank_target_positions:
                                # check if target is reached or if tank didn't move at all
                                if self.__within_range([tank.x, tank.y], self.tank_target_positions[tank.uid], 1) \
                                        or all(tank.position == self.previous_positions[tank.uid]["position"]):
                                    target_x = base.x + np.random.randint(-10, 10)
                                    target_y = base.y + np.random.randint(-10, 10)
                                    self.tank_target_positions[tank.uid] = [target_x, target_y]
                            else:
                                target_x = base.x + np.random.randint(-10, 10)
                                target_y = base.y + np.random.randint(-10, 10)
                                self.tank_target_positions[tank.uid] = [target_x, target_y]
                            tank.goto(self.tank_target_positions[tank.uid][0], self.tank_target_positions[tank.uid][1],
                                      True)
                            self.previous_positions[tank.uid] = {"position": tank.position, "moved": True}
                        counter += 1

            if len(myinfo["bases"]) > 1:
                if base.crystal > base.cost("tank") and len(self.ntanks[base.uid]) < 2:
                    tank_uid = base.build_tank(heading=360 * np.random.random())
                    self.ntanks[base.uid].append(tank_uid)
                if base.mines < 3:
                    if base.crystal > base.cost("mine"):
                        base.build_mine()
                elif base.crystal > base.cost("jet"):
                    jet_uid = base.build_jet(heading=360 * np.random.random())
                elif base.crystal > base.cost("ship") and "ships" not in myinfo:
                    ship_uid = base.build_ship(heading=360 * np.random.random())
                    self.nships[base.uid].append(ship_uid)
                elif base.crystal > base.cost("ship") and len(myinfo["ships"]) < 1:
                    ship_uid = base.build_ship(heading=360 * np.random.random())
                    self.nships[base.uid].append(ship_uid)

            else:
                if base.mines < 3:
                    if base.crystal > base.cost("mine"):
                        base.build_mine()
                # Secondly, each base should build a tank if it has less than 5 tanks
                elif base.crystal > base.cost("tank") and len(self.ntanks[base.uid]) < 5:
                    tank_uid = base.build_tank(heading=360 * np.random.random())
                    self.ntanks[base.uid].append(tank_uid)
                # Thirdly, each base should build a ship if it has less than 3 ships
                elif base.crystal > base.cost("ship") and len(myinfo["bases"]) < 2:
                    # build_ship() returns the uid of the ship that was built
                    ship_uid = base.build_ship(heading=360 * np.random.random())
                    # Add 1 to the ship counter for this base
                    self.nships[base.uid].append(ship_uid)
                elif base.crystal > base.cost("jet"):
                    jet_uid = base.build_jet(heading=360 * np.random.random())

        # Try to find an enemy target
        target = None
        # If there are multiple teams in the info, find the first team that is not mine
        if len(info) > 1:
            for name in info:
                if name != self.team:
                    # Jets target bases and ships, tanks only bases
                    if "bases" in info[name]:
                        # Simply target the first base
                        t = info[name]["bases"][0]
                        target = [t.x, t.y]

        if "tanks" in myinfo:
            for tank in myinfo["tanks"]:
                if tank.uid in self.previous_positions:
                    if not self.previous_positions[tank.uid]["moved"]:
                        self.__move_tank(tank)
        if "ships" in myinfo:
            for ship in myinfo["ships"]:
                if ship.uid in self.previous_positions and all(ship.position == self.previous_positions[ship.uid]["position"]):
                    not_near_base = not self.__ship_near_base(ship, myinfo.get('bases', [])) and not self.__check_bases(ship, info)
                    if ship.get_distance(ship.owner.x, ship.owner.y) > 40 and not_near_base:
                        ship.convert_to_base()
                    else:
                        ship.set_heading(np.random.random() * 360.0)

                self.previous_positions[ship.uid] = {"position": ship.position, "moved": True}

                defense = self.__defense_in_range(info, ship)
                # Check if it will hit a defensive obstacle
                if defense:
                    if self.__is_heading_towards(defense, [ship.x, ship.x], ship['heading']):
                        # If there's an obstacle ahead, turn 140 degrees to the right
                        ship.set_heading(ship['heading'] + 140)

        # Iterate through all my jets
        if "jets" in myinfo:
            for jet in myinfo["jets"]:
                self.__control_jet(info, jet, game_map)
