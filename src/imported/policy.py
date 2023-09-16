from enum import Enum, auto
from pacsltk import perfmodel

import conf

COLD_START_PROB_INITIAL_GUESS = 0.0


class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD_CLOUD = 2
    OFFLOAD_EDGE = 3
    DROP = 4


class ColdStartEstimation(Enum):
    NO = auto()
    NAIVE = auto()
    NAIVE_PER_FUNCTION = auto()
    PACS = auto()
    FULL_KNOWLEDGE = auto()

    @classmethod
    def from_string(cls, s):
        s = s.name.lower()
        if s == "no":
            return ColdStartEstimation.NO
        elif s == "naive":
            return ColdStartEstimation.NAIVE
        elif s == "naive-per-function":
            return ColdStartEstimation.NAIVE_PER_FUNCTION
        elif s == "pacs":
            return ColdStartEstimation.PACS
        elif s == "full-knowledge":
            return ColdStartEstimation.FULL_KNOWLEDGE
        return None


class Policy:

    def __init__(self, simulation, node):
        self.simulation = simulation
        self.node = node
        self.__edge_peers = None
        self.budget = simulation.config.getfloat(conf.SEC_POLICY, conf.HOURLY_BUDGET, fallback=-1.0)
        self.local_budget = self.budget
        if simulation.config.getboolean(conf.SEC_POLICY, conf.SPLIT_BUDGET_AMONG_EDGE_NODES, fallback=False):
            nodes = len(simulation.infra.get_edge_nodes())
            self.local_budget = self.budget / nodes

    def schedule(self, function, qos_class, offloaded_from):
        pass

    def update(self):
        pass

    def can_execute_locally(self, f, reclaim_memory=True):
        if f in self.node.warm_pool or self.node.curr_memory >= f.memory:
            return True
        if reclaim_memory:
            reclaimed = self.node.warm_pool.reclaim_memory(f.memory - self.node.curr_memory)
            self.node.curr_memory += reclaimed
        return self.node.curr_memory >= f.memory

    def _get_edge_peers(self):
        if self.__edge_peers is None:
            # TODO: need to refresh over time?
            self.__edge_peers = self.simulation.infra.get_neighbors(self.node, self.simulation.node_choice_rng,
                                                                    self.simulation.max_neighbors)
        return self.__edge_peers

    def _get_edge_peers_probabilities(self):
        peers = self._get_edge_peers()
        for peer in peers:
            if peer.curr_memory < 0.0:
                print(peer)
                print(peer.curr_memory)
            if peer.peer_exposed_memory_fraction < 0.0:
                print(peer)
                print(peer.peer_exposed_memory_fraction)
            assert (peer.curr_memory * peer.peer_exposed_memory_fraction >= 0.0)
        total_memory = sum([x.curr_memory * x.peer_exposed_memory_fraction for x in peers])
        if total_memory > 0.0:
            probs = [x.curr_memory * x.peer_exposed_memory_fraction / total_memory for x in peers]
        else:
            n = len(peers)
            probs = [1.0 / n for x in peers]
        return probs, peers

    # Picks a node for Edge offloading
    def pick_edge_node(self, fun, qos):
        # Pick peers based on resource availability
        probs, peers = self._get_edge_peers_probabilities()
        if len(peers) < 1:
            return None
        return self.simulation.node_choice_rng.choice(peers, p=probs)
