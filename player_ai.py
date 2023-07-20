# SPDX-License-Identifier: BSD-3-Clause

import numpy as np

from supremacy.vehicles import Jet, Vehicle

# This is your team name
CREATOR = "alpitroni"


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

    def __target_in_range(self, info, jet):
        for name in info:
            if name != self.team:
                if "bases" in info[name]:
                    target = info[name]["bases"]
                    for d in target:
                        if self.__within_range([jet.x, jet.y], [d.x, d.y], 20):
                            return [d.x, d.y]
        return None

    def __obstacle_in_path(self, info, jet: Jet):
        h = int(self.recon_heading)
        pos = [0, 0]
        if h == 0:
            pos = [jet.x + 3, jet.y]
        elif h == 90:
            pos = [jet.x, jet.y + 3]
        elif h == 180:
            pos = [jet.x - 3, jet.y]
        elif h == 270:
            pos = [jet.x, jet.y - 3]

        for name in info:
            if name != self.team:
                defense = []
                if "tanks" in info[name]:
                    defense += info[name]["tanks"]
                if "jets" in info[name]:
                    defense += info[name]["jets"]
                if "ships" in info[name]:
                    defense += info[name]["ships"]

                for d in defense:
                    if self.__within_range(pos, [d.x, d.y], 6):
                        return True
        return False


    def __get_closest_base(self, info: dict, vehicle: Vehicle):
        vehicle_x = vehicle["x"]
        vehicle_y = vehicle["y"]
        bases = []
        for name in info:
            if name != self.team:

                if "bases" in info[name]:
                    for base in info[name]["bases"]:
                        bases.append([base.x, base.y])
        closest_base = self.__closest_point(bases, [vehicle_x, vehicle_y])
        return closest_base

    def __get_closest_ship(self, info: dict, vehicle: Vehicle):
        vehicle_x = vehicle["x"]
        vehicle_y = vehicle["y"]
        bases = []
        for name in info:
            if name != self.team:
                if "bases" in info[name]:
                    for base in info[name]["bases"]:
                        bases.append([base.x, base.y])
        closest_ship = self.__closest_point(bases, [vehicle_x, vehicle_y])
        return closest_ship

    def __get_closest_tank(self, info: dict, vehicle: Vehicle):
        vehicle_x = vehicle["x"]
        vehicle_y = vehicle["y"]
        bases = []
        for name in info:
            if name != self.team:

                if "bases" in info[name]:
                    for base in info[name]["bases"]:
                        bases.append([base.x, base.y])
        closest_tank = self.__closest_point(bases, [vehicle_x, vehicle_y])
        return closest_tank

    def __control_recon_jet(self, info: dict, jet: Jet, game_map: np.ndarray):
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

        self.recon_alive = self.__within_range([x, y], self.recon_position, 2)

        if not self.recon_alive:
            # Recon is "not alive", which means it has not reached the recon position
            jet.goto(*self.recon_position)
        else:
            target = self.__target_in_range(info, jet)
            # Check if it will hit a defensive obstacle
            if target:
                # If there's a target in range, attack it, even as recon jet
                jet.goto(*target)
            elif self.__obstacle_in_path(info, jet):
                h = int(self.recon_heading)
                # If there's an obstacle ahead, turn 90 degrees to the right
                jet.set_heading((h + 90) % 360)
                self.recon_heading = (h + 90) % 360
                # Move in the new direction
                if self.recon_heading == 0:
                    self.recon_position = [x + 1, y]
                elif self.recon_heading == 90:
                    self.recon_position = [x, y + 1]
                elif self.recon_heading == 180:
                    self.recon_position = [x - 1, y]
                elif self.recon_heading == 270:
                    self.recon_position = [x, y - 1]
            else:
                print(self.next_recon_height, y, self.recon_heading, self.recon_position, x)
                # Recon is alive, which means it is on recon duty
                if self.__within_range([x, y], [10, y], 2):
                    # if a horizontal line has been explored it will head upwards
                    if y >= self.next_recon_height - 2:
                        self.next_recon_height = y + 40
                        self.recon_position = [x, self.next_recon_height]
                    jet.goto(*self.recon_position)
                    self.recon_heading = 90
                else:
                    # else it will head right until at x == 0
                    jet.set_heading(0)
                    self.recon_heading = 0
                    self.recon_position = [x + 1, y]

    def run(self, t: float, dt: float, info: dict, game_map: np.ndarray):
        # Get information about my team
        myinfo = info[self.team]

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
                for tank in myinfo["tanks"]:
                    if tank.uid in self.ntanks[base.uid]:
                        if tank.uid in self.tank_target_positions:
                            # check if target is reached or if tank didn't move at all
                            if self.__within_range([tank.x, tank.y], self.tank_target_positions[tank.uid], 1) \
                                    or all(tank.position == self.previous_positions[tank.uid]):
                                target_x = base.x + np.random.randint(-2, 2)
                                target_y = base.y + np.random.randint(-2, 2)
                                self.tank_target_positions[tank.uid] = [target_x, target_y]
                        else:
                            target_x = base.x + np.random.randint(-2, 2)
                            target_y = base.y + np.random.randint(-2, 2)
                            self.tank_target_positions[tank.uid] = [target_x, target_y]
                        self.previous_positions[tank.uid] = self.tank_target_positions[tank.uid]
                        tank.goto(self.tank_target_positions[tank.uid][0], self.tank_target_positions[tank.uid][1], True)

            if "ships" in myinfo:
                self.nships[base.uid] = [item for item in self.nships[base.uid] if item in ship_uids]
            # create two tanks that stays at the base to protect it
            if base.mines < 3:
                if base.crystal > base.cost("mine"):
                    base.build_mine()

            # Secondly, each base should build a tank if it has less than 5 tanks
            elif base.crystal > base.cost("tank") and len(self.ntanks[base.uid]) < 2:
                print("Base UID: " + str(base.uid) + "Number of tanks: " + str(len(self.ntanks[base.uid])))
                # build_tank() returns the uid of the tank that was built
                tank_uid = base.build_tank(heading=360 * np.random.random())
                # Add 1 to the tank counter for this base
                self.ntanks[base.uid].append(tank_uid)
            # Thirdly, each base should build a ship if it has less than 3 ships
            elif base.crystal > base.cost("ship") and len(self.nships[base.uid]) < 1:
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

        # Controlling my vehicles ==============================================

        # Description of information available on vehicles
        # (same info for tanks, ships, and jets):
        #
        # This is read-only information that all the vehicles (enemy and your own) have.
        # We define tank = info[team_name_1]["tanks"][0]. Then:
        #
        # tank.x (float): the x position of the tank
        # tank.y (float): the y position of the tank
        # tank.team (str): the name of the team the tank belongs to, e.g. ‘John’
        # tank.number (int): the player number
        # tank.speed (int): vehicle speed
        # tank.health (int): current health
        # tank.attack (int): vehicle attack force (how much damage it deals to enemy
        #     vehicles and bases)
        # tank.stopped (bool): True if the vehicle has been told to stop
        # tank.heading (float): the heading angle (in degrees) of the direction in
        #     which the vehicle will advance (0 = east, 90 = north, 180 = west,
        #     270 = south)
        # tank.vector (np.ndarray): the heading of the vehicle as a vector
        #     (basically equal to (cos(heading), sin(heading))
        # tank.position (np.ndarray): the (x, y) position as a numpy array
        # tank.uid (str): unique id for the tank
        #
        # Description of vehicle methods:
        #
        # If the vehicle is your own, the object will also have the following methods:
        #
        # tank.get_position(): returns current np.array([x, y])
        # tank.get_heading(): returns current heading in degrees
        # tank.set_heading(angle): set the heading angle (in degrees)
        # tank.get_vector(): returns np.array([cos(heading), sin(heading)])
        # tank.set_vector(np.array([vx, vy])): set the heading vector
        # tank.goto(x, y): go towards the (x, y) position
        # tank.stop(): halts the vehicle
        # tank.start(): starts the vehicle if it has stopped
        # tank.get_distance(x, y): get the distance between the current vehicle
        #     position and the given point (x, y) on the map
        # ship.convert_to_base(): convert the ship to a new base (only for ships).
        #     This only succeeds if there is land close to the ship.
        #
        # Note that by default, the goto() and get_distance() methods will use the
        # shortest path on the map (i.e. they may go through the map boundaries).

        # Iterate through all my ships
        if "ships" in myinfo:
            for ship in myinfo["ships"]:
                if ship.uid in self.previous_positions:
                    # If the ship position is the same as the previous position,
                    # convert the ship to a base if it is far from the owning base,
                    # set a random heading otherwise
                    if all(ship.position == self.previous_positions[ship.uid]):
                        if ship.get_distance(ship.owner.x, ship.owner.y) > 20:
                            ship.convert_to_base()
                        else:
                            ship.set_heading(np.random.random() * 360.0)
                # Store the previous position of this ship for the next time step
                self.previous_positions[ship.uid] = ship.position

        # Iterate through all my jets
        if "jets" in myinfo:
            self.__control_recon_jet(info, myinfo["jets"][0], game_map)
            # Go through all jets except recon jet [0]
            for jet in myinfo["jets"][1:]:
                # Jets simply go to the target if there is one, they never get stuck
                target_finders = [
                    self.__get_closest_base,
                    self.__get_closest_ship,
                    self.__get_closest_tank
                ]

                target = None
                for target_finder in target_finders:
                    target = target_finder(info, jet)
                    if target:
                        break
                if target:
                    jet.goto(*target)
