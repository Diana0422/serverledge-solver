import os
import math
import pulp as pl
import logging

# Configura il registro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warm_start = False
BETA_COST = 0.0


def update_probabilities(local_total_memory, cloud_cost, aggregated_edge_memory, metrics, arrival_rates, serv_time,
                         serv_time_cloud, serv_time_edge, init_time_local, init_time_cloud, init_time_edge,
                         offload_time_cloud, offload_time_edge, bandwidth_cloud, bandwidth_edge, cold_start_p_local,
                         cold_start_p_cloud, cold_start_p_edge, budget=-1, local_usable_memory_coeff=1.0,
                         log_queue=None):
    VERBOSE = metrics.verbosity
    F = metrics.functions
    C = metrics.classes
    F_C = [(f, c) for f in F for c in C]

    if VERBOSE > 1:
        print(f"functions: {metrics.functions}")
        print(f"classes: {metrics.classes}")
        print(f"F_C: {F_C}")
        print("------------------------------")
        print(f"Edge memory: {aggregated_edge_memory}")
        print(f"Arrival rates: {arrival_rates}")
        print(f"Init time local: {init_time_local}")
        print(f"Init time cloud: {init_time_cloud}")
        print(f"Init time edge: {init_time_edge}")
        print(f"Service time local: {serv_time}")
        print(f"Service time cloud: {serv_time_cloud}")
        print(f"Service time edge: {serv_time_edge}")
        print(f"Cold start local: {cold_start_p_local}")
        print(f"Cold start cloud: {cold_start_p_cloud}")
        print(f"Cold start edge: {cold_start_p_edge}")
        print("------------------------------")

    prob = pl.LpProblem("MyProblem", pl.LpMaximize)
    x = pl.LpVariable.dicts("X", (F, C), 0, None, pl.LpContinuous)
    y = pl.LpVariable.dicts("Y", (F, C), 0, None, pl.LpContinuous)
    pL = pl.LpVariable.dicts("PExec", (F, C), 0, 1, pl.LpContinuous)
    pC = pl.LpVariable.dicts("PCloud", (F, C), 0, 1, pl.LpContinuous)
    pE = pl.LpVariable.dicts("PEdge", (F, C), 0, 1, pl.LpContinuous)
    pD = pl.LpVariable.dicts("PDrop", (F, C), 0, 1, pl.LpContinuous)

    deadline_satisfaction_prob_local = {}
    deadline_satisfaction_prob_edge = {}
    deadline_satisfaction_prob_cloud = {}

    # TODO: we are assuming exponential distribution
    # Probability of satisfying the deadline
    for f, c in F_C:

        p = 0.0
        if c.max_rt - init_time_local[f] > 0.0:
            p += cold_start_p_local[f] * (1.0 - math.exp(-1.0 / serv_time[f] * (c.max_rt - init_time_local[f])))
        if c.max_rt > 0.0:
            p += (1.0 - cold_start_p_local[f]) * (1.0 - math.exp(-1.0 / serv_time[f] * c.max_rt))
        deadline_satisfaction_prob_local[(f, c)] = p

        p = 0.0
        tx_time = f.inputSizeMean * 8 / 1000 / 1000 / bandwidth_cloud
        if c.max_rt - init_time_cloud[f] - offload_time_cloud - tx_time > 0.0:
            p += cold_start_p_cloud[f] * (1.0 - math.exp(
                -1.0 / serv_time_cloud[f] * (c.max_rt - init_time_cloud[f] - offload_time_cloud - tx_time)))
        if c.max_rt - offload_time_cloud - tx_time > 0.0:
            p += (1.0 - cold_start_p_cloud[f]) * (
                    1.0 - math.exp(-1.0 / serv_time_cloud[f] * (c.max_rt - offload_time_cloud - tx_time)))
        deadline_satisfaction_prob_cloud[(f, c)] = p

        p = 0.0
        try:
            tx_time = f.inputSizeMean * 8 / 1000 / 1000 / bandwidth_edge
            if c.max_rt - init_time_edge[f] - offload_time_edge - tx_time > 0.0:
                p += cold_start_p_edge[f] * (1.0 - math.exp(
                    -1.0 / serv_time_edge[f] * (c.max_rt - init_time_edge[f] - offload_time_edge - tx_time)))
            if c.max_rt - offload_time_edge - tx_time > 0.0:
                p += (1.0 - cold_start_p_edge[f]) * (
                        1.0 - math.exp(-1.0 / serv_time_edge[f] * (c.max_rt - offload_time_edge - tx_time)))
        except:
            pass
        deadline_satisfaction_prob_edge[(f, c)] = p

    log_queue.put("*****************************************************************")
    log_queue.put(f"arrival_rates: {arrival_rates}")
    log_queue.put(f"init_time_local: {init_time_local}")
    log_queue.put(f"serv_time_local: {serv_time}")
    log_queue.put(f"cold_start_local: {cold_start_p_local}")
    log_queue.put(f"init_time_edge: {init_time_edge}")
    log_queue.put(f"serv_time_edge: {serv_time_edge}")
    log_queue.put(f"cold_start_edge: {cold_start_p_edge}")
    log_queue.put(f"offload_time_edge: {offload_time_edge}")
    log_queue.put(f"init_time_cloud: {init_time_cloud}")
    log_queue.put(f"serv_time_cloud: {serv_time_cloud}")
    log_queue.put(f"cold_start_cloud: {cold_start_p_cloud}")
    log_queue.put(f"offload_time_cloud: {offload_time_cloud}")
    log_queue.put("-----------------------------------------------------------------")
    log_queue.put(f"deadline_satis_prob_local: {deadline_satisfaction_prob_local}")
    log_queue.put(f"deadline_satis_prob_edge: {deadline_satisfaction_prob_edge}")
    log_queue.put(f"deadline_satis_prob_cloud: {deadline_satisfaction_prob_cloud}")

    if VERBOSE > 1:
        print("------------------------------")
        print(f"ColdStart ProbL: {cold_start_p_local}")
        print(f"ColdStart ProbC: {cold_start_p_cloud}")
        print(f"ColdStart ProbE: {cold_start_p_edge}")
        print(f"Deadline Sat ProbL: {deadline_satisfaction_prob_local}")
        print(f"Deadline Sat ProbC: {deadline_satisfaction_prob_cloud}")
        print(f"Deadline Sat ProbE: {deadline_satisfaction_prob_edge}")
        print("------------------------------")
        print(f"arrival rates (f,c): {[arrival_rates[(f, c)] for f, c in F_C]}")

    prob += (pl.lpSum([c.utility * arrival_rates[(f, c)] *
                       (pL[f][c] * deadline_satisfaction_prob_local[(f, c)] +
                        pE[f][c] * deadline_satisfaction_prob_edge[(f, c)] +
                        pC[f][c] * deadline_satisfaction_prob_cloud[(f, c)]) for f, c in F_C]) -
             pl.lpSum([c.penalty * arrival_rates[(f, c)] *
                       (pL[f][c] * (1.0 - deadline_satisfaction_prob_local[(f, c)]) +
                        pE[f][c] * (1.0 - deadline_satisfaction_prob_edge[(f, c)]) +
                        pC[f][c] * (1.0 - deadline_satisfaction_prob_cloud[(f, c)])) for f, c in F_C]) -
             BETA_COST * pl.lpSum([cloud_cost * arrival_rates[(f, c)] *
                                   pC[f][c] * serv_time_cloud[f] * f.memory / 1024 for f, c in F_C]), "objUtilCost")

    # Probability
    for f, c in F_C:
        prob += (pL[f][c] + pE[f][c] + pC[f][c] + pD[f][c] == 1.0)

    # Memory
    prob += (pl.lpSum([f.memory * x[f][c] for f, c in F_C]) <= local_usable_memory_coeff * local_total_memory)
    prob += (pl.lpSum([f.memory * y[f][c] for f, c in F_C]) <= aggregated_edge_memory)

    # Share
    for f, c in F_C:
        prob += (pL[f][c] * arrival_rates[(f, c)] * serv_time[f] <= x[f][c])
        prob += (pE[f][c] * arrival_rates[(f, c)] * serv_time_edge[f] <= y[f][c])

    class_arrival_rates = {}
    for c in C:
        class_arrival_rates[c] = sum([arrival_rates[(f, c)] for f in F if c in C])

    # Min completion
    for c in C:
        if c.min_completion_percentage > 0.0 and class_arrival_rates[c] > 0.0:
            prob += (pl.lpSum([pD[f][c] * arrival_rates[(f, c)] for f in F]) / class_arrival_rates[
                c] <= 1 - c.min_completion_percentage)

    # Max hourly budget
    if budget is not None and budget > 0.0:
        prob += (pl.lpSum([cloud_cost * arrival_rates[(f, c)] *
                           pC[f][c] * serv_time_cloud[f] * f.memory / 1024 for f, c in F_C]) <= budget / 3600)

    status = solve(prob)
    if status != "Optimal":
        print(f"WARNING: solution status: {status}")
        return None

    obj = pl.value(prob.objective)
    if obj is None:
        print(f"WARNING: objective is None")
        return None

    shares = {(f, c): pl.value(x[f][c]) for f, c in F_C}

    if VERBOSE > 0:
        print("Obj = ", obj)
        # shares = {(f, c): pl.value(x[f][c]) for f, c in F_C} # fixme prima era qui e ora in riga 151, va bene?
        print(f"Shares: {shares}")

    probs = {(f, c): [pl.value(pL[f][c]),
                      pl.value(pC[f][c]),
                      pl.value(pE[f][c]),
                      pl.value(pD[f][c])] for f, c in F_C}

    # Expected cost
    # ec = 0
    # ctput = 0
    # for f,c in F_C:
    #    ec += cloud.cost*arrival_rates[(f,c)]*pl.value(pC[f][c])*serv_time_cloud[f]*f.memory/1024
    #    ctput += arrival_rates[(f,c)]*pl.value(pC[f][c])
    # print(f"Expected cost: {ec:.5f} ({budget/3600:.5f})")
    # print(f"Expected cloud throughput: {ctput:.1f}")

    # Workaround to avoid numerical issues
    for f, c in F_C:
        s = sum(probs[(f, c)])
        probs[(f, c)] = [x / s for x in probs[(f, c)]]
        if VERBOSE > 0:
            print(f"{f}-{c}: {probs[(f, c)]}")

    log_queue.put(f"solution probs: {probs}")
    log_queue.put("")
    return probs, shares


def solve(problem):
    global warm_start
    solver_name = os.environ.get("PULP_SOLVER", "GLPK_CMD")

    if not solver_name in ["CPLEX_CMD", "GUROBI_CMD", "PULP_CBC_CMD", "CBC_CMD", "CPLEX_PY", "GUROBI"] and warm_start:
        print("WARNING: warmStart not supported by solver {}".format(solver_name))
        warm_start = False

    if not warm_start:
        if solver_name == "GUROBI_CMD":
            solver = pl.getSolver(solver_name, gapRel=0.02, timeLimit=900)
        else:
            solver = pl.getSolver(solver_name, msg=False)
    else:
        solver = pl.getSolver(solver_name, warmStart=warm_start)

    problem.solve(solver)
    return pl.LpStatus[problem.status]
