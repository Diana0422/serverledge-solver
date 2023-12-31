import time
import logging
import queue

from proto import solver_pb2_grpc, solver_pb2
import grpc
from concurrent import futures
import threading
import properties as p, optimizer as opt, infrastructure as infra
from faas import QoSClass, Function

WAIT_TIME_SECONDS = 60

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea una coda per i messaggi di registro
log_queue = queue.Queue()

ARRIVALS_LOCK = threading.Lock()
PREV_ARRIVALS_LOCK = threading.Lock()
ARRIVAL_RATES_LOCK = threading.Lock()


def periodic_show():
    # Execute periodic update of metrics
    ticker = threading.Event()
    while not ticker.wait(WAIT_TIME_SECONDS):
        print("sono qui")
        # Read messages from the queue and read the logs
        while not log_queue.empty():
            message = log_queue.get()
            print(message)
            #logger.info(message)


def _insert_if_not_present(ls: list, key: str, o) -> bool:
    """
    Inserts an object into a list, checking its presence by a key value provided ad input
    :param ls: list
    :param key: key value
    :param o: object to insert
    :return: bool: True if the element is already present, False otherwise
    """
    for elem in ls:
        if key == elem.name:
            i = ls.index(elem)
            ls.pop(i)
            ls.insert(i, o)
            return True
    return False


class NetworkMetrics:

    def __init__(self, network: infra.Network):
        self.network = network
        self.clock_start = time.process_time()  # inizia a contare per raccogliere gli intervalli temporali e calcolare i tassi
        self.time = 0
        self.last_update_time = 0
        self.props = p.Props()

        # general config and functions/classes info
        self.functions = []  # mantiene il riferimento alle funzioni in arrivo [Function]
        self.classes = []  # mantiene il riferimento alle classi in arrivo [QoSClass]
        self.local_usable_memory_coeff = 1.0  # coefficient that explains the local memory available on node
        self.verbosity = self.props.Verbosity  # config
        self.arrival_rate_alpha = self.props.ArrivalAlpha
        # weight of the new rates wrt the old rates in the arrival rates calculation

        self.bandwidth_cloud = 0.0
        self.bandwidth_edge = 0.0
        self.arrivals = {}  # arrivi per (f,c)
        self.prev_arrivals = {}  # arrivi per (f,c) nel precedente intervallo temporale
        self.arrival_rates = {}  # rate di arrivo per (f,c)

        # Info recovered from request sent by client
        self.service_time = {}  # tempo di servizio stimato per esecuzione locale per f (Function, float)
        self.service_time_cloud = {}  # tempo di servizio stimato per esecuzione cloud per f (Function, float)
        self.service_time_edge = {}  # tempo di servizio stimato per esecuzione edge per f (Function, float)
        self.init_time = {}  # tempo di servizio stimato per inizializzazione locale per f (Function, float)
        self.init_time_cloud = {}  # tempo di servizio stimato per inizializzazione cloud per f (Function, float)
        self.init_time_edge = {}  # tempo di servizio stimato per inizializzazione edge per f (Function, float)
        self.offload_time_cloud = 0.0  # tempo di offload (rtt) dal nodo locale al cloud
        self.offload_time_edge = 0.0  # tempo di offload (rtt) dal nodo locale al nodo edge scelto lato client
        self.cold_start = {}  # probabilità di cold start locale per f (Function, float)
        self.cold_start_cloud = {}  # probabilità di cold start cloud per (f,c) (Function, float)
        self.cold_start_edge = {}  # probabilità di cold start edge per (f,c) (Function, float)

        # result
        self.probs = {(f, c): [1.0, 0.0, 0.0, 0.0] for f in self.functions for c in self.classes}
        self.evaluation_time = time.process_time()

    def _search_function(self, f_name: str) -> Function:
        """
        # Search in function array for function with given name
        :param f_name: the func name
        :return: Function
        """
        for foo in self.functions:
            if f_name == foo.name:
                return foo

    def _search_class(self, c_name: str) -> QoSClass:
        """
        # Search in class array for class with given name
        :param c_name: class name
        :return: QoSClass
        """
        for c in self.classes:
            if c_name == c.name:
                return c

    def update_time(self):
        """
        Updates the process time of the new updates (useful to calculates rates)
        :return:
        """
        self.last_update_time = self.time
        self.time = time.process_time()

    def update_functions(self, function: solver_pb2.Function):
        """
        Writes function information in Function class instance and adds the instance to a state dictionary.
        It performs an update if function key is already present in the state dictionary.
        :param function: solver_pb2.Function object used to recover function information from client
        :return: None
        """
        function_name = function.name
        func = Function(name=function_name,
                        memory=function.memory,
                        serviceMean=function.duration,
                        inputSizeMean=function.input_size)
        if not _insert_if_not_present(ls=self.functions, key=function_name, o=func):
            self.functions.append(func)

    def update_classes(self, c: solver_pb2.QosClass):
        """
        Writes class information in QoSClass instance and adds the instance to a state dictionary.
        :param c: solver_pb2.QosClass object used to recover class information from client
        :return: None
        """
        class_name = c.name
        qos_class = QoSClass(name=class_name, min_completion_percentage=c.completed_percentage, arrival_weight=1,
                             max_rt=c.max_response_time)
        print(c.max_response_time)

        if qos_class.max_rt < 0:
            # No constraint on maximum response time for the class
            qos_class.max_rt = float("inf")  # set unlimited constraint

        if not _insert_if_not_present(ls=self.classes, key=class_name, o=qos_class):
            self.classes.append(qos_class)

    def update_function_class(self, function: solver_pb2.Function):
        """
        Adds missing couples (function, class) in arrivals and arrival_rates dictionaries
        :param function: the function to add
        :return: None
        """
        function_name = function.name
        # Search in function array for function f
        f = self._search_function(function_name)

        for c in self.classes:
            with ARRIVAL_RATES_LOCK:
                if (f, c) not in self.arrival_rates.keys():
                    self.arrival_rates.update({(f, c): 0.0})
            with ARRIVALS_LOCK:
                if (f, c) not in self.arrivals.keys():
                    self.arrivals.update({(f, c): 0.0})
        # FIXME AUDIT print(f"arrivals: {self.arrivals}")
        # FIXME AUDIT print(f"arrival rates: {self.arrival_rates}")
        # FIXME AUDIT print(f"prev_arrivals: {self.prev_arrivals}")

    def update_rtt(self, is_cloud_rtt: bool, rtt: float):
        """
        Updates offload time metric, both cloud and edge rtt
        :param is_cloud_rtt: boolean that specifies whether if rtt is intended to be to cloud or to another edge node
        :param rtt: the rtt value to be set
        :return: None
        """
        if is_cloud_rtt:
            self.offload_time_cloud = rtt
        else:
            self.offload_time_edge = rtt

    def update_service_time(self, f: str, service_local: float, service_cloud: float, service_edge: float):
        """
        Updates execution time whether if it's local, in cloud or in the edge network
        :param f: function name
        :param service_local: local execution time
        :param service_cloud: cloud execution time
        :param service_edge: edge execution time
        :return: None
        """
        # Search function with name f in function array
        func = self._search_function(f)

        # Update values in dictionary If the value of the estimated service time is zero, it means that there are not
        # completion locally, on cloud or on edge nodes
        if service_local > 0:
            self.service_time.update({func: service_local})
        else:
            self.service_time.update({func: 0.1})  # set a value != 0 but still very small
        if service_cloud > 0:
            self.service_time_cloud.update({func: service_cloud})
        else:
            self.service_time_cloud.update({func: 0.1})
        if service_edge > 0:
            self.service_time_edge.update({func: service_edge})
        else:
            self.service_time_edge.update({func: 0.1})

    def update_init_time(self, f: str, init_local: float, init_cloud: float, init_edge: float):
        """
        Updates initialization time, whether if it's local, in cloud or on the edge network
        :param f: function name
        :param init_local: local initialization time
        :param init_cloud: cloud initialization time
        :param init_edge: edge initialization time
        :return: None
        """
        # Search in function array for function f
        func = self._search_function(f)

        # Update values in dictionary
        self.init_time.update({func: init_local})
        self.init_time_cloud.update({func: init_cloud})
        self.init_time_edge.update({func: init_edge})

    def update_cold_start(self, f: str, p_cold_local: float, p_cold_cloud: float, p_cold_edge: float):
        """
        Updates cold start probability values, whether if it's local, on cloud or on the edge network
        :param f: function name
        :param p_cold_local: local cold start probability
        :param p_cold_cloud: cloud cold start probability
        :param p_cold_edge: edge cold start probability
        :return: None
        """
        # Search in function array for function f
        func = self._search_function(f)

        # Update values in dictionary
        self.cold_start.update({func: p_cold_local})
        self.cold_start_cloud.update({func: p_cold_cloud})
        self.cold_start_edge.update({func: p_cold_edge})

    def update_arrival_rates(self, func_name: str, class_name: str, arrivals):
        """
        Updates arrival rates for couples of instances (Function, QoSClass)
        :param func_name: function name
        :param class_name: class name
        :param arrivals: new arrival rate for the couple (f,c)
        :return: None
        """
        # Search in function array for function f
        f = self._search_function(func_name)

        # Search in class array for class c
        c = self._search_class(class_name)

        # If it's the first arrival update for the (function,class) pair
        with ARRIVAL_RATES_LOCK:
            if (f, c) not in self.arrival_rates.keys():
                self.arrival_rates.update({(f, c): arrivals})
            else:
                new_rate = arrivals
                self.arrival_rates[(f, c)] = (self.arrival_rate_alpha * new_rate +
                                              (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)])

    def update_bandwidth(self, bw_cloud: float, bw_edge: float):
        """
        Updates bandwidth values, whether if it's on cloud or edge
        :param bw_cloud: bandwidth of the link to the cloud
        :param bw_edge: bandwidth of the link to the edge
        :return: None
        """
        self.bandwidth_edge = bw_edge
        self.bandwidth_cloud = bw_cloud

    def update_local_usable_mem_coefficient(self, c: float):
        """
        Updates the local usable memory coefficient of the node
        :param c: the new value of the coefficient
        :return:
        """
        self.local_usable_memory_coeff = c


# def show_metrics():
#    print("Sto mostrando le metriche")


# def periodic_show():
# Execute periodic update of metrics
#    ticker = threading.Event()
#    while not ticker.wait(WAIT_TIME_SECONDS):
#        show_metrics()


def publish():
    # Publish service
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solver_pb2_grpc.add_SolverServicer_to_server(Estimator(), server)
    properties = p.Props()
    print(f"Python server started at port {properties.ServerPort}")
    server.add_insecure_port("[::]:" + str(properties.ServerPort))
    server.start()
    server.wait_for_termination()


def initializing_network() -> infra.Network:
    # TODO now useless and this is dummy
    region_cloud = infra.Region("cloud", True)
    region_edge1 = infra.Region("edge1", False)
    region_edge2 = infra.Region("edge2", False)
    regions = [region_cloud, region_edge1, region_edge2]
    net_latency = {}
    bandwidth_mbps = {}

    # Add node cloud
    network = infra.Network(regions=regions, network_latency=net_latency, bandwidth_mbps=bandwidth_mbps)
    # network.add_node(infra.Node("nuvola", 1000, region=region_cloud, speedup=1), region=region_cloud)
    # network.add_node(infra.Node("pippo", 100, region=region_edge1, speedup=1), region=region_edge1)
    # network.add_node(infra.Node("pluto", 100, region=region_edge1, speedup=1), region=region_edge1)
    # network.add_node(infra.Node("topolino", 100, region=region_edge2, speedup=1), region=region_edge2)
    return network


def prepare_response(probs: dict[(Function, QoSClass), [float]], shares: dict[(Function, QoSClass), [float]],
                     eval_time: float):
    """
    Sends the response back to the client
    :param eval_time:
    :param shares: dictionary with the shares values for couples (f,c)
    :param probs: dictionary with the solution of the problem for couples (f,c)
    :return: None
    """
    couples = probs.keys()
    f_c_resp = {}  # {Function: [ClassResponse]}

    for f, c in couples:
        c_name = c.name
        # Get corresponding probabilities
        values = probs.get((f, c))
        if len(values) != 0:
            pL = values[0]
            pC = values[1]
            pE = values[2]
            pD = values[3]
            # FIXME AUDIT print(f"pL: {pL}")
            # FIXME AUDIT print(f"pC: {pC}")
            # FIXME AUDIT print(f"pE: {pE}")
            # FIXME AUDIT print(f"pD: {pD}")
            share = shares.get((f, c))
            class_resp = solver_pb2.ClassResponse(name=c_name, pL=pL, pC=pC, pE=pE, pD=pD, share=share)
            if f not in f_c_resp:
                f_c_resp[f] = [class_resp]
            else:
                f_c_resp.get(f).append(class_resp)
        else:
            f_c_resp[f] = []

    f_responses = []
    for f in f_c_resp:
        f_name = f.name
        # FIXME AUDIT print(f"function name: {f_name}")
        c_responses = f_c_resp[f]
        # FIXME AUDIT print(f"c_responses: {c_responses}")
        func_resp = solver_pb2.FunctionResponse(name=f_name)
        func_resp.class_responses.extend(c_responses)
        f_responses.append(func_resp)

    # FIXME AUDIT print(f"f_responses: {f_responses}")
    response = solver_pb2.Response(time_taken=eval_time)
    response.f_response.extend(f_responses)
    # FIXME AUDIT print(f"response: {response}")
    return response


# the gRPC server functions
class Estimator(solver_pb2_grpc.SolverServicer):

    def __init__(self):
        # Initialize network
        print("initializing network")
        self.network = initializing_network()
        self.net_metrics = NetworkMetrics(self.network)

    # this is called by the client when is required the execution of a function
    def Solve(self, request: solver_pb2.Request, context):
        """
        Get the prediction values on request
        :param request: the prediction request
        :param context: the context
        :return: the list of the predictions
        """
        print("Received request\n")
        self.net_metrics.update_time()

        # Recover useful data from incoming request
        # FIXME AUDIT print("incoming functions: ", request.functions, "\n")
        total_memory = request.memory_local
        cloud_cost = request.cost_cloud
        local_budget = request.local_budget
        aggregated_memory = request.memory_aggregate
        self.net_metrics.update_rtt(True, request.offload_latency_cloud)
        self.net_metrics.update_rtt(False, request.offload_latency_edge)
        self.net_metrics.update_local_usable_mem_coefficient(request.usable_memory_coefficient)

        total_new_arrivals = 0

        for c in request.classes:
            self.net_metrics.update_classes(c)

        for function in request.functions:
            self.net_metrics.update_functions(function)
            self.net_metrics.update_function_class(function)

            for inv in function.invocations:
                function_name = function.name  # function invoked
                class_name = inv.qos_class  # class of service of the function invoked

                new_arrivals = inv.arrivals
                total_new_arrivals += new_arrivals

                if new_arrivals != 0:
                    self.net_metrics.update_arrival_rates(function_name, class_name, arrivals=inv.arrivals)

                self.net_metrics.update_service_time(function_name,
                                                     service_local=function.duration,
                                                     service_cloud=function.duration_offloaded_cloud,
                                                     service_edge=function.duration_offloaded_edge)
                self.net_metrics.update_init_time(function_name,
                                                  init_local=function.init_time,
                                                  init_cloud=function.init_time_offloaded_cloud,
                                                  init_edge=function.init_time_offloaded_edge)

                self.net_metrics.update_cold_start(function_name,
                                                   p_cold_local=function.pcold,
                                                   p_cold_cloud=function.pcold_offloaded_cloud,
                                                   p_cold_edge=function.pcold_offloaded_edge)

                self.net_metrics.update_bandwidth(bw_cloud=function.bandwidth_cloud,
                                                  bw_edge=function.bandwidth_edge)

        # Set default probs based on policy
        if request.policy == "edgeCloud":
            self.net_metrics.probs = {(f, c): [0.5, 0.25, 0.25, 0.0] for f in self.net_metrics.functions for c in self.net_metrics.classes}
        else:
            self.net_metrics.probs = {(f, c): [0.5, 0.5, 0.0, 0.0] for f in self.net_metrics.functions for c in self.net_metrics.classes}

        if total_new_arrivals != 0:
            probs, shares = opt.update_probabilities(local_total_memory=total_memory, cloud_cost=cloud_cost,
                                                     aggregated_edge_memory=aggregated_memory, metrics=self.net_metrics,
                                                     arrival_rates=self.net_metrics.arrival_rates,
                                                     serv_time=self.net_metrics.service_time,
                                                     serv_time_cloud=self.net_metrics.service_time_cloud,
                                                     serv_time_edge=self.net_metrics.service_time_edge,
                                                     init_time_local=self.net_metrics.init_time,
                                                     init_time_cloud=self.net_metrics.init_time_cloud,
                                                     init_time_edge=self.net_metrics.init_time_edge,
                                                     offload_time_cloud=self.net_metrics.offload_time_cloud,
                                                     offload_time_edge=self.net_metrics.offload_time_edge,
                                                     bandwidth_cloud=self.net_metrics.bandwidth_cloud,
                                                     bandwidth_edge=self.net_metrics.bandwidth_edge,
                                                     cold_start_p_local=self.net_metrics.cold_start,
                                                     cold_start_p_cloud=self.net_metrics.cold_start_cloud,
                                                     cold_start_p_edge=self.net_metrics.cold_start_edge,
                                                     budget=local_budget,
                                                     local_usable_memory_coeff=self.net_metrics.local_usable_memory_coeff,
                                                     log_queue=log_queue)
        else:
            probs = {(f, c): [] for f in self.net_metrics.functions for c in self.net_metrics.classes}
            shares = {(f, c): [] for f in self.net_metrics.functions for c in self.net_metrics.classes}

        eval_t = time.process_time() - self.net_metrics.evaluation_time
        # Marshal probabilities into gRPC Response and send back to client
        response = prepare_response(probs, shares, eval_t)
        self.net_metrics.evaluation_time = time.process_time()
        return response


def serve():
    # Create a pool with 12 threads to execute code
    pool = futures.ThreadPoolExecutor(max_workers=4)
    # Execute periodic update of metrics
    pool.submit(periodic_show)
    pool.submit(publish)

    # wait for all tasks to complete
    pool.shutdown(wait=True)
