from pacsltk import perfmodel

import conf
import optimizer
from policy import Policy, SchedulerDecision, ColdStartEstimation, COLD_START_PROB_INITIAL_GUESS

ADAPTIVE_LOCAL_MEMORY_COEFFICIENT = True
ADAPTIVE_EDGE_MEMORY_COEFFICIENT = True

"""
ProbabilisticPolicyVertical = ProbabilisticPolicy
"""


class ProbabilisticPolicyVertical(Policy):

    # Probability vector: p_e, p_o, p_d

    def __init__(self, simulation, node, strict_budget_enforce=False):
        super().__init__(simulation, node)
        self.strict_budget_enforce = strict_budget_enforce
        cloud_region = node.region.default_cloud
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

        self.rng = self.simulation.policy_rng1
        self.stats_snapshot = None
        self.last_update_time = None
        self.arrival_rate_alpha = self.simulation.config.getfloat(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA,
                                                                  fallback=1.0)
        self.local_cold_start_estimation = ColdStartEstimation.from_string(
            self.simulation.config.get(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY,
                                       fallback=ColdStartEstimation.NAIVE))
        assert (self.local_cold_start_estimation != ColdStartEstimation.FULL_KNOWLEDGE)
        self.cloud_cold_start_estimation = ColdStartEstimation.from_string(
            self.simulation.config.get(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY,
                                       fallback=ColdStartEstimation.NAIVE))
        assert (self.cloud_cold_start_estimation != ColdStartEstimation.FULL_KNOWLEDGE)
        self.edge_cold_start_estimation = ColdStartEstimation.from_string(
            self.simulation.config.get(conf.SEC_POLICY, conf.EDGE_COLD_START_EST_STRATEGY,
                                       fallback=ColdStartEstimation.NAIVE))
        assert (self.edge_cold_start_estimation != ColdStartEstimation.FULL_KNOWLEDGE)

        self.curr_local_blocked_reqs = 0
        self.curr_local_reqs = 0
        self.local_usable_memory_coeff = 1.0
        self.forced_drop = 0.0

        self.arrival_rates = {}
        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}
        self.cold_start_prob_local = {}
        self.cold_start_prob_cloud = {}
        self.cloud_rtt = 0.0
        self.cloud_bw = 0.0
        self.rt_percentile = self.simulation.config.getfloat(conf.SEC_POLICY, "rt-percentile", fallback=-1.0)

        self.init_time_local = {f: simulation.init_time[(f, self.node)] for f in simulation.functions}
        self.init_time_cloud = {f: simulation.init_time[(f, self.cloud)] for f in simulation.functions}
        self.init_time_edge = {}  # updated periodically

        self.possible_decisions = [SchedulerDecision.EXEC, SchedulerDecision.OFFLOAD_CLOUD, SchedulerDecision.DROP]
        self.probs = {(f, c): [0.5, 0.5, 0.] for f in simulation.functions for c in simulation.classes}

    def schedule(self, f, c, offloaded_from):
        probabilities = self.probs[(f, c)]
        decision = self.rng.choice(self.possible_decisions, p=probabilities)
        if decision == SchedulerDecision.EXEC:
            self.curr_local_reqs += 1
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(f):
            self.curr_local_blocked_reqs += 1

            # check if we can afford a Cloud offloading
            if self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
                return SchedulerDecision.DROP

            nolocal_prob = sum(probabilities[1:])
            if nolocal_prob > 0.0:
                decision = self.rng.choice([SchedulerDecision.OFFLOAD_CLOUD, SchedulerDecision.DROP],
                                           p=[probabilities[1] / nolocal_prob, probabilities[2] / nolocal_prob])
            else:
                decision = SchedulerDecision.OFFLOAD_CLOUD

        if decision == SchedulerDecision.OFFLOAD_CLOUD and self.strict_budget_enforce and \
                self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
            return SchedulerDecision.DROP

        return decision

    def update(self):
        # Questo metodo viene chiamato periodicamente

        self.update_metrics()

        arrivals = sum(
            [self.arrival_rates.get((f, c), 0.0) for f in self.simulation.functions for c in self.simulation.classes])
        if arrivals > 0.0:
            self.update_probabilities()

        self.stats_snapshot = self.simulation.stats.to_dict()
        self.last_update_time = self.simulation.t

        self.curr_local_blocked_reqs = 0
        self.curr_local_reqs = 0

    def update_metrics(self):
        stats = self.simulation.stats

        if ADAPTIVE_EDGE_MEMORY_COEFFICIENT and self.stats_snapshot is not None:
            # Reduce exposed memory if offloaded have been dropped
            dropped_offl = sum([stats.dropped_offloaded[(f, c, self.node)] for f in self.simulation.functions for c in
                                self.simulation.classes])
            prev_dropped_offl = sum(
                [self.stats_snapshot["dropped_offloaded"][repr((f, c, self.node))] for f in self.simulation.functions
                 for c in self.simulation.classes])
            arrivals = sum(
                [stats.arrivals[(f, c, self.node)] - self.stats_snapshot["arrivals"][repr((f, c, self.node))] for f in
                 self.simulation.functions for c in self.simulation.classes])
            ext_arrivals = sum(
                [stats.ext_arrivals[(f, c, self.node)] - self.stats_snapshot["ext_arrivals"][repr((f, c, self.node))]
                 for f in self.simulation.functions for c in self.simulation.classes])

            loss = (dropped_offl - prev_dropped_offl) / (arrivals - ext_arrivals) if arrivals - ext_arrivals > 0 else 0
            if loss > 0.0:
                self.node.peer_exposed_memory_fraction = max(0.05, self.node.peer_exposed_memory_fraction * loss / 2.0)
            else:
                self.node.peer_exposed_memory_fraction = min(self.node.peer_exposed_memory_fraction * 1.1, 1.0)
            # print(f"{self.node}: Loss: {loss} ({dropped_offl-prev_dropped_offl}): {self.node.peer_exposed_memory_fraction:.3f}")

        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}

        for f in self.simulation.functions:
            if stats.node2completions[(f, self.node)] > 0:
                self.estimated_service_time[f] = stats.execution_time_sum[(f, self.node)] / \
                                                 stats.node2completions[(f, self.node)]
            else:
                self.estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.cloud)] > 0:
                self.estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.cloud)] / \
                                                       stats.node2completions[(f, self.cloud)]
            else:
                self.estimated_service_time_cloud[f] = 0.1

        expected_compl = {}
        expected_drop = {}
        expected_offload = {}
        if self.stats_snapshot is not None:
            arrival_rates = {}
            for f, c, n in stats.arrivals:
                if n != self.node:
                    continue
                new_arrivals = stats.arrivals[(f, c, self.node)] - self.stats_snapshot["arrivals"][repr((f, c, n))]
                expected_compl[(f, c)] = new_arrivals * self.probs[(f, c)][0]
                expected_offload[(f, c)] = new_arrivals * self.probs[(f, c)][1]
                expected_drop[(f, c)] = new_arrivals * self.probs[(f, c)][2]
                new_rate = new_arrivals / (self.simulation.t - self.last_update_time)
                self.arrival_rates[(f, c)] = self.arrival_rate_alpha * new_rate + \
                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)]
        else:
            for f, c, n in stats.arrivals:
                if n != self.node:
                    continue
                self.arrival_rates[(f, c)] = stats.arrivals[(f, c, self.node)] / self.simulation.t

        self.estimate_cold_start_prob(stats)

        # print(f"[{self.node}] Arrivals: {self.arrival_rates}")

        self.cloud_rtt = 2 * self.simulation.infra.get_latency(self.node, self.cloud)
        self.cloud_bw = self.simulation.infra.get_bandwidth(self.node, self.cloud)

    def estimate_cold_start_prob(self, stats):
        #
        # LOCAL NODE
        #
        if self.local_cold_start_estimation == ColdStartEstimation.PACS:
            for f in self.simulation.functions:
                total_arrival_rate = max(0.001,
                                         sum([self.arrival_rates.get((f, x), 0.0) for x in self.simulation.classes]))
                # XXX: we are ignoring initial warm pool....
                props1, _ = perfmodel.get_sls_warm_count_dist(total_arrival_rate,
                                                              self.estimated_service_time[f],
                                                              self.estimated_service_time[f] +
                                                              self.simulation.init_time[(f, self.node)],
                                                              self.simulation.expiration_timeout)
                self.cold_start_prob_local[f] = props1["cold_prob"]
        elif self.local_cold_start_estimation == ColdStartEstimation.NAIVE:
            # Same prob for every function
            node_compl = sum([stats.node2completions[(_f, self.node)] for _f in self.simulation.functions])
            node_cs = sum([stats.cold_starts[(_f, self.node)] for _f in self.simulation.functions])
            for f in self.simulation.functions:
                if node_compl > 0:
                    self.cold_start_prob_local[f] = node_cs / node_compl
                else:
                    self.cold_start_prob_local[f] = COLD_START_PROB_INITIAL_GUESS
        elif self.local_cold_start_estimation == ColdStartEstimation.NAIVE_PER_FUNCTION:
            for f in self.simulation.functions:
                if stats.node2completions.get((f, self.node), 0) > 0:
                    self.cold_start_prob_local[f] = stats.cold_starts.get((f, self.node),
                                                                          0) / stats.node2completions.get(
                        (f, self.node), 0)
                else:
                    self.cold_start_prob_local[f] = COLD_START_PROB_INITIAL_GUESS
        else:  # No
            for f in self.simulation.functions:
                self.cold_start_prob_local[f] = 0

        # CLOUD
        #
        if self.cloud_cold_start_estimation == ColdStartEstimation.PACS:
            for f in self.simulation.functions:
                total_arrival_rate = max(0.001,
                                         sum([self.arrival_rates.get((f, x), 0.0) * self.probs[(f, x)][1] for x in
                                              self.simulation.classes]))
                props1, _ = perfmodel.get_sls_warm_count_dist(total_arrival_rate,
                                                              self.estimated_service_time_cloud[f],
                                                              self.estimated_service_time_cloud[f] +
                                                              self.simulation.init_time[(f, self.node)],
                                                              self.simulation.expiration_timeout)
                self.cold_start_prob_cloud[f] = props1["cold_prob"]
        elif self.cloud_cold_start_estimation == ColdStartEstimation.NAIVE:
            # Same prob for every function
            node_compl = sum([stats.node2completions[(_f, self.cloud)] for _f in self.simulation.functions])
            node_cs = sum([stats.cold_starts[(_f, self.cloud)] for _f in self.simulation.functions])
            for f in self.simulation.functions:
                if node_compl > 0:
                    self.cold_start_prob_cloud[f] = node_cs / node_compl
                else:
                    self.cold_start_prob_cloud[f] = COLD_START_PROB_INITIAL_GUESS
        elif self.cloud_cold_start_estimation == ColdStartEstimation.NAIVE_PER_FUNCTION:
            for f in self.simulation.functions:
                if stats.node2completions.get((f, self.cloud), 0) > 0:
                    self.cold_start_prob_cloud[f] = stats.cold_starts.get((f, self.cloud),
                                                                          0) / stats.node2completions.get(
                        (f, self.cloud), 0)
                else:
                    self.cold_start_prob_cloud[f] = COLD_START_PROB_INITIAL_GUESS
        else:  # No
            for f in self.simulation.functions:
                self.cold_start_prob_cloud[f] = 0

        # print(f"[{self.node}] Cold start prob: {self.cold_start_prob_local}")
        # print(f"[{self.cloud}] Cold start prob: {self.cold_start_prob_cloud}")

    def update_probabilities(self):
        if ADAPTIVE_LOCAL_MEMORY_COEFFICIENT:
            loss = self.curr_local_blocked_reqs / self.curr_local_reqs if self.curr_local_reqs > 0 else 0
            if loss > 0.0:
                self.local_usable_memory_coeff -= self.local_usable_memory_coeff * loss / 2.0
            else:
                self.local_usable_memory_coeff = min(self.local_usable_memory_coeff * 1.1, 1.0)
            print(f"Usable memory: {self.local_usable_memory_coeff:.2f}")

        bandwidth = self.simulation.infra.get_bandwidth(self.node, self.cloud)
        new_probs = optimizer.update_probabilities(self.node, self.cloud, self.simulation, self.arrival_rates,
                                                   self.estimated_service_time, self.estimated_service_time_cloud,
                                                   self.simulation.init_time, self.cloud_rtt, bandwidth,
                                                   self.cold_start_prob_local, self.cold_start_prob_cloud,
                                                   self.rt_percentile, self.local_budget,
                                                   self.local_usable_memory_coeff,,
        if new_probs is not None:
            self.probs = new_probs
            # print(f"[{self.node}] Probs: {self.probs}")


class ProbabilisticPolicyHorizontal(ProbabilisticPolicyVertical):

    # Probability vector: p_L, p_C, p_E, p_D
    # LP Model v2

    def __init__(self, simulation, node, strict_budget_enforce=False):
        super().__init__(simulation, node, strict_budget_enforce)

        self.aggregated_edge_memory = 0.0
        self.estimated_service_time_edge = {}
        self.edge_rtt = 0.0
        self.edge_bw = 0.0  # FIXME: aggiunto rispetto alla simulazione originale
        self.cold_start_prob_edge = {}
        self.prohibit_any_2nd_offloading = simulation.config.getboolean(conf.SEC_POLICY,
                                                                        conf.PROHIBIT_ANY_SECOND_OFFLOADING,
                                                                        fallback="false")
        print(self.prohibit_any_2nd_offloading)
        self.possible_decisions = list(SchedulerDecision)
        self.probs = {(f, c): [0.5, 0.5, 0., 0.] for f in simulation.functions for c in simulation.classes}

    def schedule(self, f, c, offloaded_from):
        probabilities = self.probs[(f, c)].copy()

        # If the request has already been offloaded, cannot offload again
        if len(offloaded_from) > 0:
            probabilities[SchedulerDecision.OFFLOAD_EDGE.value - 1] = 0
            probabilities[SchedulerDecision.OFFLOAD_CLOUD.value - 1] = 0
            s = sum(probabilities)
            if not s > 0.0:
                probabilities = [0 for x in probabilities]
                probabilities[SchedulerDecision.EXEC.value - 1] = 0.5
                probabilities[SchedulerDecision.DROP.value - 1] = 0.5
            else:
                probabilities = [x / s for x in probabilities]

        decision = self.rng.choice(self.possible_decisions, p=probabilities)
        if decision == SchedulerDecision.EXEC:
            self.curr_local_reqs += 1
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(f):
            self.curr_local_blocked_reqs += 1
            if self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
                probabilities[SchedulerDecision.OFFLOAD_CLOUD.value - 1] = 0
            probabilities[SchedulerDecision.EXEC.value - 1] = 0
            s = sum(probabilities)
            if not s > 0.0:
                # NOTE: we may add new Cloud offloadings even if p_cloud=0
                if c.utility > 0.0 and \
                        self.simulation.stats.cost / self.simulation.t * 3600 < self.budget \
                        and (not self.prohibit_any_2nd_offloading or len(offloaded_from) == 0):
                    return SchedulerDecision.OFFLOAD_CLOUD
                else:
                    return SchedulerDecision.DROP
                    self.forced_drop += 1
            probabilities = [x / s for x in probabilities]
            return self.rng.choice(self.possible_decisions, p=probabilities)

        if decision == SchedulerDecision.OFFLOAD_CLOUD and self.strict_budget_enforce and \
                self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
            return SchedulerDecision.DROP

        return decision

    def update_metrics(self):
        super().update_metrics()
        stats = self.simulation.stats

        neighbor_probs, neighbors = self._get_edge_peers_probabilities()
        if len(neighbors) == 0:
            self.aggregated_edge_memory = 1
        else:
            self.aggregated_edge_memory = max(1,
                                              sum([x.curr_memory * x.peer_exposed_memory_fraction for x in neighbors]))

        self.edge_rtt = sum(
            [self.simulation.infra.get_latency(self.node, x) * prob for x, prob in zip(neighbors, neighbor_probs)])
        self.edge_bw = sum(
            [self.simulation.infra.get_bandwidth(self.node, x) * prob for x, prob in zip(neighbors, neighbor_probs)])

        self.estimated_service_time_edge = {}
        for f in self.simulation.functions:
            inittime = 0.0
            servtime = 0.0
            for neighbor, prob in zip(neighbors, neighbor_probs):
                if stats.node2completions[(f, neighbor)] > 0:
                    servtime += prob * stats.execution_time_sum[(f, neighbor)] / stats.node2completions[(f, neighbor)]
                inittime += prob * self.simulation.init_time[(f, neighbor)]
            if servtime == 0.0:
                servtime = self.estimated_service_time[f]
            self.estimated_service_time_edge[f] = servtime
            self.init_time_edge[f] = inittime

        self.estimate_edge_cold_start_prob(stats, neighbors, neighbor_probs)

    def estimate_edge_cold_start_prob(self, stats, neighbors, neighbor_probs):
        peer_probs, peers = self._get_edge_peers_probabilities()

        if self.edge_cold_start_estimation == ColdStartEstimation.PACS:
            for f in self.simulation.functions:
                total_offloaded_rate = max(0.001,
                                           sum([self.arrival_rates.get((f, x), 0.0) * self.probs[(f, x)][3] for x in
                                                self.simulation.classes]))
                props1, _ = perfmodel.get_sls_warm_count_dist(total_offloaded_rate,
                                                              self.estimated_service_time_edge[f],
                                                              self.estimated_service_time_edge[f] +
                                                              self.simulation.init_time[(f, self.node)],
                                                              self.simulation.expiration_timeout)
                self.cold_start_prob_edge[f] = props1["cold_prob"]
        elif self.edge_cold_start_estimation == ColdStartEstimation.NAIVE:
            # Same prob for every function
            total_prob = 0
            for p, peer_prob in zip(peers, peer_probs):
                node_compl = sum([stats.node2completions[(_f, p)] for _f in self.simulation.functions])
                node_cs = sum([stats.cold_starts[(_f, p)] for _f in self.simulation.functions])
                if node_compl > 0:
                    _prob = node_cs / node_compl
                else:
                    _prob = COLD_START_PROB_INITIAL_GUESS
                total_prob += _prob * peer_prob
            for f in self.simulation.functions:
                self.cold_start_prob_edge[f] = total_prob
        elif self.edge_cold_start_estimation == ColdStartEstimation.NAIVE_PER_FUNCTION:
            for f in self.simulation.functions:
                self.cold_start_prob_edge[f] = 0
                for p, peer_prob in zip(peers, peer_probs):
                    if stats.node2completions.get((f, p), 0) > 0:
                        _prob = stats.cold_starts.get((f, p), 0) / stats.node2completions.get((f, p), 0)
                    else:
                        _prob = COLD_START_PROB_INITIAL_GUESS
                    self.cold_start_prob_edge[f] += _prob * peer_prob

        else:  # No
            for f in self.simulation.functions:
                self.cold_start_prob_edge[f] = 0

    def update_probabilities(self):
        if ADAPTIVE_LOCAL_MEMORY_COEFFICIENT:
            loss = self.curr_local_blocked_reqs / self.curr_local_reqs if self.curr_local_reqs > 0 else 0
            if loss > 0.0:
                self.local_usable_memory_coeff -= self.local_usable_memory_coeff * loss / 2.0
            else:
                self.local_usable_memory_coeff = min(self.local_usable_memory_coeff * 1.1, 1.0)
            print(f"{self.node}: Usable memory: {self.local_usable_memory_coeff:.2f}")

        new_probs = optimizer.update_probabilities(self.node, self.cloud, self.aggregated_edge_memory, self.simulation,
                                                   self.arrival_rates, self.estimated_service_time,
                                                   self.estimated_service_time_cloud, self.estimated_service_time_edge,
                                                   self.init_time_local, self.init_time_cloud, self.init_time_edge,
                                                   self.cloud_rtt, self.edge_rtt, self.cloud_bw, self.edge_bw,
                                                   self.cold_start_prob_local, self.cold_start_prob_cloud,
                                                   self.cold_start_prob_edge, self.local_budget,
                                                   self.local_usable_memory_coeff)
        if new_probs is not None:
            self.probs = new_probs
            # print(f"[{self.node}] Probs: {self.probs}")
