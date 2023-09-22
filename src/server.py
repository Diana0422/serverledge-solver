import time
import logging

from proto import solver_pb2_grpc, solver_pb2
import grpc
from concurrent import futures
import threading
import properties as p, optimizer as opt, infrastructure as infra
from faas import QoSClass, Function

WAIT_TIME_SECONDS = 120

logging.basicConfig(level=logging.INFO)


class NetworkMetrics:

    def __init__(self, network: infra.Network):
        self.network = network
        self.clock_start = time.process_time()  # inizia a contare per raccogliere gli intervalli temporali e calcolare i tassi

        # general config and functions/classes info
        self.functions = []  # mantiene il riferimento alle funzioni in arrivo [Function]
        self.classes = []  # mantiene il riferimento alle classi in arrivo [QoSClass]
        self.verbosity = 2  # TODO: impostare config
        self.cloud_cost = 0  # TODO: impostare config
        self.budget = 100  # TODO: impostare config
        self.local_budget = self.budget  # TODO oppure self.budget / len(self.network.get_edge_nodes())

        # TODO Info to be calculated
        self.bandwidth_cloud = 0.0  # fixme in realtà ho un valore diverso per ogni funzione?
        self.bandwidth_edge = 0.0  # fixme in realtà ho un valore diverso per ogni funzione?
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

    def update_functions(self, function: solver_pb2.Function):
        """
        Writes function information in Function class instance and adds the instance to a state dictionary.
        It performs an update if function key is already present in the state dictionary.
        :param function: solver_pb2.Function object used to recover function information from client
        :return: None
        """
        function_name = function.name
        f = Function(name=function_name, memory=function.memory, serviceMean=function.duration)
        for f in self.functions:
            if function_name == f.name:
                return
        self.functions.append(f)
        print(self.functions)

    def update_classes(self, c: solver_pb2.QosClass):
        """
        Writes class information in QoSClass instance and adds the instance to a state dictionary.
        :param c: solver_pb2.QosClass object used to recover class information from client
        :return: None
        """
        print("In update classes")
        class_name = c.name
        print(f"class: {class_name}")
        cl = QoSClass(name=class_name, min_completion_percentage=c.completed_percentage, arrival_weight=1,
                      max_rt=c.max_response_time)
        if cl not in self.classes:
            self.classes.append(cl)
        print(self.classes)

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

        # Update values in dictionary
        self.service_time.update({func: service_local})
        self.service_time_cloud.update({func: service_cloud})
        self.service_time_edge.update({func: service_edge})

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

    def update_arrival_rates(self, f: str, c: str, arrivals):
        """
        Updates arrival rates for couples of instances (Function, QoSClass)
        :param f: function name
        :param c: class name
        :param arrivals: number of arrivals for couples (f,c)
        :return: None
        """
        # Update the clock and get the time interval
        clock_stop = time.process_time()
        print(f"clock start: {self.clock_start}")
        print(f"clock stop: {clock_stop}")
        t = clock_stop - self.clock_start
        print(f"clock stop - clock start: {t}")

        # Search in function array for function f
        func = self._search_function(f)

        # Search in class array for class c
        cl = self._search_class(c)

        # Calculate new arrivals rates
        print(f"arrivals: {arrivals}")
        new_arrival_rate = arrivals / t
        print(f"arrival_rate: {new_arrival_rate}\n")
        self.arrival_rates.update({(func, cl): new_arrival_rate})

    def update_bandwidth(self, bw_cloud: float, bw_edge: float):
        """
        Updates bandwidth values, whether if it's on cloud or edge
        :param bw_cloud: bandwidth of the link to the cloud
        :param bw_edge: bandwidth of the link to the edge
        :return: None
        """
        # Check rtt, if it's zero then it means that local execution happened
        if self.offload_time_edge == 0:
            self.bandwidth_edge = float("inf")
        else:
            self.bandwidth_edge = bw_edge
        if self.offload_time_cloud == 0:
            self.bandwidth_cloud = float("inf")
        else:
            self.bandwidth_cloud = bw_cloud


def show_metrics():
    # TODO
    print("Sto mostrando le metriche")


def periodic_show():
    # Execute periodic update of metrics
    ticker = threading.Event()
    while not ticker.wait(WAIT_TIME_SECONDS):
        show_metrics()


def publish():
    # Publish service
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solver_pb2_grpc.add_SolverServicer_to_server(Estimator(), server)
    properties = p.Props()
    print(f"Python server started at port {properties.ServerPort}")
    server.add_insecure_port("[::]:" + str(properties.ServerPort))
    server.start()
    server.wait_for_termination()


def update_membership() -> infra.Node:
    """
    Aggiorna la membership dei nodi della rete e ritorna il nodo da cui proviene la richiesta di esecuzione
    :return: Node (local)
    """
    # TODO
    # check if nodo è presente nella lista dei nodi della rete
    # se è presente allora non aggiungerlo
    # se non è presente allora aggiungilo


def initializing_network() -> infra.Network:
    # TODO set regions, latency and bandwidth from config
    region_cloud = infra.Region("cloud", True)
    region_edge1 = infra.Region("edge1", False)
    region_edge2 = infra.Region("edge2", False)
    regions = [region_cloud, region_edge1, region_edge2]
    net_latency = {}
    bandwidth_mbps = {}

    # Add node cloud
    network = infra.Network(regions=regions, network_latency=net_latency, bandwidth_mbps=bandwidth_mbps)
    network.add_node(infra.Node("nuvola", 1000, region=region_cloud, speedup=1), region=region_cloud)
    network.add_node(infra.Node("pippo", 100, region=region_edge1, speedup=1), region=region_edge1)
    network.add_node(infra.Node("pluto", 100, region=region_edge1, speedup=1), region=region_edge1)
    network.add_node(infra.Node("topolino", 100, region=region_edge2, speedup=1), region=region_edge2)
    print(network)
    return network


def prepare_response(probs: dict[(Function, QoSClass), [float]], shares: dict[(Function, QoSClass), [float]]):
    """
    Sends the response back to the client
    :param shares: dictionary with the shares values for couples (f,c)
    :param probs: dictionary with the solution of the problem for couples (f,c)
    :return: None
    """
    couples = probs.keys()
    f_c_resp = {}  # {Function: [ClassResponse]}

    for f, c in couples:
        c_name = c.name
        print(c_name)

        # Get corresponding probabilities
        values = probs.get((f, c))
        pL = values[0]
        pC = values[1]
        pE = values[2]
        pD = values[3]
        print(f"pL: {pL}")
        print(f"pC: {pC}")
        print(f"pE: {pE}")
        print(f"pD: {pD}")
        share = shares.get((f, c))
        print(share)
        class_resp = solver_pb2.ClassResponse(name=c_name, pL=pL, pC=pC, pE=pE, pD=pD, share=share)
        if f not in f_c_resp:
            f_c_resp[f] = [class_resp]
        else:
            f_c_resp.get(f).append(class_resp)

    f_responses = []
    for f in f_c_resp:
        f_name = f.name
        print(f"function name: {f_name}")
        c_responses = f_c_resp[f]
        print(f"c_responses: {c_responses}")
        func_resp = solver_pb2.FunctionResponse(name=f_name)
        func_resp.class_responses.extend(c_responses)
        f_responses.append(func_resp)

    print(f"f_responses: {f_responses}")
    response = solver_pb2.Response(time_taken=0.0)
    response.f_response.extend(f_responses)
    print(f"response: {response}")
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

        # Recover useful data from incoming request
        print("incoming functions: ", request.functions, "\n")
        total_memory = request.memory_local
        cloud_cost = request.cost_cloud
        aggregated_memory = request.memory_aggregate
        self.net_metrics.update_rtt(True, request.offload_latency_cloud)
        self.net_metrics.update_rtt(False, request.offload_latency_edge)

        for c in request.classes:
            self.net_metrics.update_classes(c)

        for function in request.functions:
            self.net_metrics.update_functions(function)

            for inv in function.invocations:
                function_name = function.name
                class_name = inv.qos_class

                self.net_metrics.update_service_time(function_name,
                                                     service_local=function.duration,
                                                     service_cloud=function.duration_offloaded_cloud,
                                                     service_edge=function.duration_offloaded_edge)
                self.net_metrics.update_init_time(function_name,
                                                  init_local=function.init_time,
                                                  init_cloud=function.init_time_offloaded_cloud,
                                                  init_edge=function.init_time_offloaded_edge)

                self.net_metrics.update_arrival_rates(function_name, class_name, arrivals=inv.arrivals)

                self.net_metrics.update_cold_start(function_name,
                                                   p_cold_local=function.pcold,
                                                   p_cold_cloud=function.pcold_offloaded_cloud,
                                                   p_cold_edge=function.pcold_offloaded_edge)

                self.net_metrics.update_bandwidth(bw_cloud=function.bandwidth_cloud, bw_edge=function.bandwidth_edge)

        probs, shares = opt.update_probabilities(local_total_memory=total_memory,
                                                 # mi interessa solamente la memoria locale, che posso fare arrivare come informazione dal lato client
                                                 cloud_cost=cloud_cost,
                                                 # di questo mi interessa solo il costo, che arriva già nella richiesta originale (Request.cost)
                                                 aggregated_edge_memory=aggregated_memory,
                                                 # lo facciamo arrivare con la richiesta perché la posso calcolare tramite il registry locale
                                                 metrics=self.net_metrics,
                                                 arrival_rates=self.net_metrics.arrival_rates, # fixme considera solo intervalli
                                                 serv_time=self.net_metrics.service_time,
                                                 serv_time_cloud=self.net_metrics.service_time_cloud,
                                                 serv_time_edge=self.net_metrics.service_time_edge,
                                                 init_time_local=self.net_metrics.init_time,
                                                 init_time_cloud=self.net_metrics.init_time_cloud,
                                                 init_time_edge=self.net_metrics.init_time_edge,
                                                 offload_time_cloud=self.net_metrics.offload_time_cloud,
                                                 offload_time_edge=self.net_metrics.offload_time_edge,  # lo facciamo
                                                 # arrivare con la richiesta perché la posso calcolare sempre tramite vivaldi
                                                 # (la ho come input lato client)
                                                 bandwidth_cloud=self.net_metrics.bandwidth_cloud, # fixme config
                                                 bandwidth_edge=self.net_metrics.bandwidth_edge, # fixme config
                                                 # viene calcolato lato client e semplicemente recuperiamo il valore dal messaggio
                                                 cold_start_p_local=self.net_metrics.cold_start,
                                                 cold_start_p_cloud=self.net_metrics.cold_start_cloud,
                                                 cold_start_p_edge=self.net_metrics.cold_start_edge,
                                                 budget=self.net_metrics.local_budget, #fixme config
                                                 local_usable_memory_coeff=1.0  # fixme vedi come fatto nel simulatore aggiungendo fattore di loss + aggiungere contatori per eseguiti locale e bloccati + ogni volta azzerati
                                                 )

        # Marshal probabilities into gRPC Response and send back to client
        print(probs)
        response = prepare_response(probs, shares)
        return response


def serve():
    # Create a pool with 12 threads to execute code
    pool = futures.ThreadPoolExecutor(max_workers=12)
    # Execute periodic update of metrics
    pool.submit(periodic_show)
    pool.submit(publish)

    # wait for all tasks to complete
    pool.shutdown(wait=True)
