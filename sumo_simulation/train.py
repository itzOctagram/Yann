from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import time
import optparse
import random
import serial  # type: ignore
import numpy as np
import torch
import torch.optim as optim
import torch.nn.functional as F
import torch.nn as nn
import matplotlib.pyplot as plt
import threading
import asyncio
import websockets
import json
from typing import Literal

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # type: ignore  # noqa
import traci  # type: ignore # noqa


def get_vehicle_numbers(lanes):
    vehicle_per_lane = dict()
    for l in lanes:
        vehicle_per_lane[l] = 0
        for k in traci.lane.getLastStepVehicleIDs(l):
            if traci.vehicle.getLanePosition(k) > 10:
                vehicle_per_lane[l] += 1
    return vehicle_per_lane


def get_waiting_time(lanes):
    waiting_time = 0
    for lane in lanes:
        waiting_time += traci.lane.getWaitingTime(lane)
    return waiting_time


def phaseDuration(junction, phase_time, phase_state):
    traci.trafficlight.setRedYellowGreenState(junction, phase_state)
    traci.trafficlight.setPhaseDuration(junction, phase_time)


class Model(nn.Module):
    def __init__(self, lr, input_dims, fc1_dims, fc2_dims, n_actions):
        super(Model, self).__init__()
        self.lr = lr
        self.input_dims = input_dims
        self.fc1_dims = fc1_dims
        self.fc2_dims = fc2_dims
        self.n_actions = n_actions

        self.linear1 = nn.Linear(self.input_dims, self.fc1_dims)
        self.linear2 = nn.Linear(self.fc1_dims, self.fc2_dims)
        self.linear3 = nn.Linear(self.fc2_dims, self.n_actions)

        self.optimizer = optim.Adam(self.parameters(), lr=self.lr)
        self.loss = nn.MSELoss()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, state):
        x = F.relu(self.linear1(state))
        x = F.relu(self.linear2(x))
        actions = self.linear3(x)
        return actions


class Agent:
    def __init__(
        self,
        gamma,
        epsilon,
        lr,
        input_dims,
        fc1_dims,
        fc2_dims,
        batch_size,
        n_actions,
        junctions,
        max_memory_size=100000,
        epsilon_dec=5e-4,
        epsilon_end=0.05,
    ):
        self.gamma = gamma
        self.epsilon = epsilon
        self.lr = lr
        self.batch_size = batch_size
        self.input_dims = input_dims
        self.fc1_dims = fc1_dims
        self.fc2_dims = fc2_dims
        self.n_actions = n_actions
        self.action_space = [i for i in range(n_actions)]
        self.junctions = junctions
        self.max_mem = max_memory_size
        self.epsilon_dec = epsilon_dec
        self.epsilon_end = epsilon_end
        self.mem_cntr = 0
        self.iter_cntr = 0
        self.replace_target = 100

        self.Q_eval = Model(
            self.lr, self.input_dims, self.fc1_dims, self.fc2_dims, self.n_actions
        )
        self.memory = dict()
        for junction in junctions:
            self.memory[junction] = {
                "state_memory": np.zeros(
                    (self.max_mem, self.input_dims), dtype=np.float32
                ),
                "new_state_memory": np.zeros(
                    (self.max_mem, self.input_dims), dtype=np.float32
                ),
                "reward_memory": np.zeros(self.max_mem, dtype=np.float32),
                "action_memory": np.zeros(self.max_mem, dtype=np.int32),
                "terminal_memory": np.zeros(self.max_mem, dtype=np.bool_),
                "mem_cntr": 0,
                "iter_cntr": 0,
            }

    def store_transition(self, state, state_, action, reward, done, junction):
        index = self.memory[junction]["mem_cntr"] % self.max_mem
        self.memory[junction]["state_memory"][index] = state
        self.memory[junction]["new_state_memory"][index] = state_
        self.memory[junction]["reward_memory"][index] = reward
        self.memory[junction]["terminal_memory"][index] = done
        self.memory[junction]["action_memory"][index] = action
        self.memory[junction]["mem_cntr"] += 1

    def choose_action(self, observation):
        state = torch.tensor([observation], dtype=torch.float).to(self.Q_eval.device)
        if np.random.random() > self.epsilon:
            actions = self.Q_eval.forward(state)
            action = torch.argmax(actions).item()
        else:
            action = np.random.choice(self.action_space)
        return action

    def reset(self, junction_numbers):
        for junction_number in junction_numbers:
            self.memory[junction_number]["mem_cntr"] = 0

    def save(self, model_name):
        torch.save(self.Q_eval.state_dict(), f"sumo_simulation/models/{model_name}.bin")

    def learn(self, junction):
        self.Q_eval.optimizer.zero_grad()

        batch = np.arange(self.memory[junction]["mem_cntr"], dtype=np.int32)

        state_batch = torch.tensor(self.memory[junction]["state_memory"][batch]).to(
            self.Q_eval.device
        )
        new_state_batch = torch.tensor(
            self.memory[junction]["new_state_memory"][batch]
        ).to(self.Q_eval.device)
        reward_batch = torch.tensor(self.memory[junction]["reward_memory"][batch]).to(
            self.Q_eval.device
        )
        terminal_batch = torch.tensor(
            self.memory[junction]["terminal_memory"][batch]
        ).to(self.Q_eval.device)
        action_batch = self.memory[junction]["action_memory"][batch]

        q_eval = self.Q_eval.forward(state_batch)[batch, action_batch]
        q_next = self.Q_eval.forward(new_state_batch)
        q_next[terminal_batch] = 0.0
        q_target = reward_batch + self.gamma * torch.max(q_next, dim=1)[0]
        loss = self.Q_eval.loss(q_target, q_eval).to(self.Q_eval.device)

        loss.backward()
        self.Q_eval.optimizer.step()

        self.iter_cntr += 1
        self.epsilon = (
            self.epsilon - self.epsilon_dec
            if self.epsilon > self.epsilon_end
            else self.epsilon_end
        )


def run(train=True, model_name="model", epochs=50, steps=500):
    """execute the TraCI control loop"""
    epochs = epochs
    steps = steps
    best_time = np.inf
    total_time_list = list()
    traci.start(
        [
            checkBinary("sumo"),
            "-c",
            "sumo_simulation/configuration.sumocfg",
            "--tripinfo-output",
            "sumo_simulation/maps/tripinfo.xml",
        ]
    )
    all_junctions = traci.trafficlight.getIDList()
    junction_numbers = list(range(len(all_junctions)))

    brain = Agent(
        gamma=0.99,
        epsilon=0.0,
        lr=0.1,
        input_dims=8,
        # input_dims = len(all_junctions) * 4,
        fc1_dims=256,
        fc2_dims=256,
        batch_size=1024,
        n_actions=8,
        junctions=junction_numbers,
    )

    if not train:
        brain.Q_eval.load_state_dict(
            torch.load(
                f"sumo_simulation/models/{model_name}.bin",
                map_location=brain.Q_eval.device,
            )
        )

    print(brain.Q_eval.device)
    traci.close()
    for e in range(epochs):
        if train:
            traci.start(
                [
                    checkBinary("sumo"),
                    "-c",
                    "sumo_simulation/configuration.sumocfg",
                    "--tripinfo-output",
                    "sumo_simulation/tripinfo.xml",
                ]
            )
        else:
            traci.start(
                [
                    checkBinary("sumo-gui"),
                    "-c",
                    "sumo_simulation/configuration.sumocfg",
                    "--tripinfo-output",
                    "sumo_simulation/tripinfo.xml",
                ]
            )

        print(f"epoch: {e}")
        select_lane = [
            ["yyyyyrrrrrrrrrrrrrrr", "GGGGGrrrrrrrrrrrrrrr"],
            ["rrrrryyyyyrrrrrrrrrr", "rrrrrGGGGGrrrrrrrrrr"],
            ["rrrrrrrrrryyyyyrrrrr", "rrrrrrrrrrGGGGGrrrrr"],
            ["rrrrrrrrrrrrrrryyyyy", "rrrrrrrrrrrrrrrGGGGG"],
            ["yyyyyrrrrrrrrrrrrrrr", "GGGGGrrrrrrrrrrrrrrr"],
            ["rrrrryyyyyrrrrrrrrrr", "rrrrrGGGGGrrrrrrrrrr"],
            ["rrrrrrrrrryyyyyrrrrr", "rrrrrrrrrrGGGGGrrrrr"],
            ["rrrrrrrrrrrrrrryyyyy", "rrrrrrrrrrrrrrrGGGGG"],
        ]

        # select_lane = [
        #     ["yyyyrrrrrrrrrrrr", "GGGGrrrrrrrrrrrr"],
        #     ["rrrryyyyrrrrrrrr", "rrrrGGGGrrrrrrrr"],
        #     ["rrrrrrrryyyyrrrr", "rrrrrrrrGGGGrrrr"],
        #     ["rrrrrrrrrrrryyyy", "rrrrrrrrrrrrGGGG"],
        # ]

        step = 0
        total_time = 0
        min_duration = 5

        traffic_lights_time = dict()
        prev_wait_time = dict()
        prev_vehicles_per_lane = dict()
        prev_action = dict()
        all_lanes = list()

        for junction_number, junction in enumerate(all_junctions):
            prev_wait_time[junction] = 0
            prev_action[junction_number] = 0
            traffic_lights_time[junction] = 0
            prev_vehicles_per_lane[junction_number] = [0] * 8
            # prev_vehicles_per_lane[junction_number] = [0] * (len(all_junctions) * 4)
            all_lanes.extend(list(traci.trafficlight.getControlledLanes(junction)))

        while step <= steps:
            traci.simulationStep()
            for junction_number, junction in enumerate(all_junctions):
                controled_lanes = traci.trafficlight.getControlledLanes(junction)
                waiting_time = get_waiting_time(controled_lanes)
                total_time += waiting_time
                if traffic_lights_time[junction] == 0:
                    vehicles_per_lane = get_vehicle_numbers(controled_lanes)
                    # vehicles_per_lane = get_vehicle_numbers(all_lanes)

                    # storing previous state and current state
                    reward = -1 * waiting_time
                    state_ = list(vehicles_per_lane.values())
                    state = prev_vehicles_per_lane[junction_number]
                    prev_vehicles_per_lane[junction_number] = state_
                    brain.store_transition(
                        state,
                        state_,
                        prev_action[junction_number],
                        reward,
                        (step == steps),
                        junction_number,
                    )

                    # selecting new action based on current state
                    lane = brain.choose_action(state_)
                    prev_action[junction_number] = lane
                    phaseDuration(junction, 6, select_lane[lane][0])
                    phaseDuration(junction, min_duration + 10, select_lane[lane][1])

                    traffic_lights_time[junction] = min_duration + 10
                    if train:
                        brain.learn(junction_number)
                else:
                    traffic_lights_time[junction] -= 1
            step += 1
        print("total_time", total_time)
        total_time_list.append(total_time)

        if total_time < best_time:
            best_time = total_time
            if train:
                brain.save(model_name)

        traci.close()
        sys.stdout.flush()
        if not train:
            break
    if train:
        plt.plot(list(range(len(total_time_list))), total_time_list)
        plt.xlabel("epochs")
        plt.ylabel("total time")
        plt.savefig(f"sumo_simulation/plots/time_vs_epoch_{model_name}.png")
        plt.show()


# use thhis
def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option(
        "-m",
        dest="model_name",
        type="string",
        default="new_model",
        help="name of model",
    )
    optParser.add_option(
        "--train",
        action="store_true",
        default=False,
        help="training or testing",
    )
    optParser.add_option(
        "-e",
        dest="epochs",
        type="int",
        default=50,
        help="Number of epochs",
    )
    optParser.add_option(
        "-s",
        dest="steps",
        type="int",
        default=5000,
        help="Number of steps",
    )

    options, args = optParser.parse_args()
    return options


def add_vehicle(
    direction: Literal["north", "west", "south", "east"],
    turn: Literal["left", "straight", "right"],
):
    routeId = 1
    routeId = routeId + {"north": 0, "west": 1, "south": 2, "east": 3}[direction] * 3
    routeId = routeId + {"left": 0, "straight": 1, "right": 2}[turn]
    print(f"Adding vehicle with routeId: {routeId}")
    traci.vehicle.add(f"veh_{time.time()}", f"route{routeId}")


async def handler(websocket, path):
    async for message in websocket:
        data = json.loads(message)
        print(f"Received data from {path}: {data}")
        data = data["received_from_sender"]
        direction = data["direction"]
        turn = data["turn"]
        direction = {0: "north", 1: "west", 2: "south", 3: "east"}[direction]
        turn = {0: "left", 1: "straight", 2: "right"}[turn]
        add_vehicle(direction, turn)


async def receive_message():
    uri = "ws://localhost:8765/receiver"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await handler(websocket, uri)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Wait before reconnecting
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)  # Wait before reconnecting


def run_receive_message():
    asyncio.run(receive_message())


# this is the main entry point of this script
if __name__ == "__main__":
    options = get_options()
    model_name = options.model_name
    train = options.train
    epochs = options.epochs
    steps = options.steps

    # Start the receive_message function in a separate thread
    websocket_thread = threading.Thread(target=run_receive_message)
    websocket_thread.start()

    # Run the SUMO simulation
    run(train=train, model_name=model_name, epochs=epochs, steps=steps)

    # Wait for the WebSocket server thread to finish
    # websocket_thread.join()
