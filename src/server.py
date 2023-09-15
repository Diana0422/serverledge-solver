import time

from proto import solver_pb2_grpc, solver_pb2
import grpc
from concurrent import futures
import threading
import properties as p
from infrastructure import Network
from faas import Node

import optimizer as opt

WAIT_TIME_SECONDS = 120


class NetworkMetrics:

    def __init__(self, network: Network):
        self.network = network
        self.clock_start = time.clock()  # inizia a contare per raccogliere gli intervalli temporali e calcolare i tassi

        self.functions = {}  # mantiene il riferimento alle funzioni in arrivo (nome_funzione: Function)
        self.classes = {}  # mantiene il riferimento alle classi in arrivo (nome_classe: QoSClass)
        self.verbosity = 1  # TODO: impostare config
        self.cloud_cost = 0  # TODO: impostare config
        self.budget = 100    # TODO: impostare config
        self.local_budget = self.budget / len(self.network.get_edge_nodes())

        self.aggregated_edge_memory = 0.0  # memoria aggregata nell'edge per f
        self.bandwidth_cloud = 0.0
        self.bandwidth_edge = 0.0
        self.arrival_rates = {}  # rate di arrivo per (f,c)
        self.service_time = {}  # tempo di servizio stimato per esecuzione locale per f
        self.service_time_cloud = {}  # tempo di servizio stimato per esecuzione cloud per f
        self.service_time_edge = {}  # tempo di servizio stimato per esecuzione edge per f
        self.init_time = {}  # tempo di servizio stimato per inizializzazione locale per f
        self.init_time_cloud = {}  # tempo di servizio stimato per inizializzazione cloud per f
        self.init_time_edge = {}  # tempo di servizio stimato per inizializzazione edge per f
        self.cold_start = {}  # probabilità di cold start locale per (f,c)
        self.cold_start_cloud = {}  # probabilità di cold start cloud per (f,c)
        self.cold_start_edge = {}  # probabilità di cold start edge per (f,c)

        # self.init_time_local = {f: simulation.init_time[(f,self.node)] for f in simulation.functions}
        # self.init_time_cloud = {f: simulation.init_time[(f,self.cloud)] for f in simulation.functions}
        # self.init_time_edge = {} # updated periodically

    def update_aggregated_edge_memory(self):
        # FIXME: capire come raccogliere i dati sulla memoria dei nodi vicini
        pass

    def update_bandwidth(self, x: Node, y: Node):
        # FIXME: capire come raccogliere la larghezza di banda dai nodi vicini, e capire se ogni nodo li mantiene
        #  oppure se vengono recuperati dal decisore raccogliere la largezza di banda tra nodo x e nodo y (incluso il
        #  nodo cloud)
        pass

    def update_rtt(self, x: Node, y: Node):
        # calcolare rtt tra nodo x e nodo y (incluso nodo cloud)
        pass

    def update_arrival_rates(self, f: str, c: str, arrivals):
        """
        Aggiorna i tassi di arrivo per coppie (f,c)
        :param f: nome della funzione
        :param c: nome della classe di appartenenza della funzione
        :param arrivals: numero di arrivi della coppia (f,c)
        :return: None
        """
        # Aggiorna il clock per l'intervallo di calcolo successivo
        clock_stop = time.clock()
        t = clock_stop - self.clock_start
        self.clock_start = clock_stop

        # Calcola il tasso di arrivo sulla base della funzione e della classe che ha richiesto la valutazione
        new_arrival_rate = arrivals / t
        self.arrival_rates.update({(f, c): new_arrival_rate})

    def update_service_time(self, f: str, service_local: float, service_cloud: float, service_edge: float):
        """
        Aggiorno il tempo di esecuzione locale, nel cloud e nell'edge sulla rete
        :param f: nome della funzione
        :param service_local: tempo di esecuzione locale
        :param service_cloud: tempo di esecuzione nel cloud
        :param service_edge: tempo di esecuzione nell'edge
        :return: None
        """
        # I dati in input sono già forniti dal client quando arriva una richiesta di aggiornamento delle probabilità
        self.service_time.update({f: service_local})
        self.service_time_cloud.update({f: service_cloud})
        self.service_time_edge.update({f: service_edge})

    def update_init_time(self, f: str, init_local: float, init_cloud: float, init_edge: float):
        """
        Aggiorna il tempo di inizializzazione locale, nel cloud e nell'edge sulla rete
        :param f: nome della funzione
        :param init_local: tempo di inizializzazione locale
        :param init_cloud: tempo di inizializzazione nel cloud
        :param init_edge: tempo di inizializzazione nell'edge
        :return: None
        """
        # I dati in input sono già forniti dal client quando arriva una richiesta di aggiornamento delle probabilità
        self.init_time.update({f: init_local})
        self.init_time_cloud.update({f: init_cloud})
        self.init_time_edge.update({f: init_edge})

    def update_cold_start(self, f: str, c: str, p_cold_local: float, p_cold_cloud: float, p_cold_edge: float):
        """
        Aggiorna la probabilità di cold start locale, nel cloud e nell'edge nella rete
        :param f: nome della funzione
        :param c: nome della classe
        :param p_cold_local: probabilità di cold start locale
        :param p_cold_cloud: probabilità di cold start nel cloud
        :param p_cold_edge: probabilità di cold start nell'edge
        :return:
        """
        # I dati in input sono già forniti dal client quando arriva una richiesta di aggiornamento delle probabilità
        self.cold_start.update({(f, c): p_cold_local})
        self.cold_start_cloud.update({(f, c): p_cold_cloud})
        self.cold_start_edge.update({(f, c): p_cold_edge})


def show_metrics():
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


def update_membership() -> Node:
    """
    Aggiorna la membership dei nodi della rete e ritorna il nodo da cui proviene la richiesta di esecuzione
    :return: Node (local)
    """
    # check if nodo è presente nella lista dei nodi della rete
    # se è presente allora non aggiungerlo
    # se non è presente allora aggiungilo


# the gRPC server functions
class Estimator(solver_pb2_grpc.SolverServicer):

    def __init__(self):
        # Initialize network
        # TODO set regions, latency and bandwidth from config
        regions = 1
        net_latency = {(): 0.0}
        bandwidth_mbps = {(): 1}

        self.network = Network(regions=regions, network_latency=net_latency, bandwidth_mbps=bandwidth_mbps)
        self.net_metrics = NetworkMetrics(self.network)

    # this is called by the client when is required the execution of a function
    def Solve(self, request: solver_pb2.Request, context):
        """
        Get the prediction values on request
        :param request: the prediction request
        :param context: the context
        :return: the list of the predictions
        """
        print("Received request")

        # Set local node and update membership
        local = update_membership()

        # Get a cloud node
        # fixme: get a random cloud node
        cloud = self.network.get_cloud_nodes()[0]

        # Call metrics update
        for _, function in request.functions:
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

                self.net_metrics.update_cold_start(function_name, class_name,
                                                   p_cold_local=function.pcold,
                                                   p_cold_cloud=function.pcold_offloaded_cloud,
                                                   p_cold_edge=function.pcold_offloaded_edge)

        # FIXME: mancano alcuni dati da calcolare
        opt.update_probabilities(local, cloud,
                                 aggregated_edge_memory=0, #fixme da calcolare
                                 metrics=self.net_metrics,
                                 arrival_rates=self.net_metrics.arrival_rates,
                                 serv_time=self.net_metrics.service_time,
                                 serv_time_cloud=self.net_metrics.service_time_cloud,
                                 serv_time_edge=self.net_metrics.service_time_edge,
                                 init_time_local=self.net_metrics.init_time,
                                 init_time_cloud=self.net_metrics.init_time_cloud,
                                 init_time_edge=self.net_metrics.init_time_edge,
                                 offload_time_cloud=0.0, offload_time_edge=0.0, #fixme da calcolare
                                 bandwidth_cloud=1, bandwidth_edge=1, #fixme da calcolare
                                 cold_start_p_local=self.net_metrics.cold_start,
                                 cold_start_p_cloud=self.net_metrics.cold_start_cloud,
                                 cold_start_p_edge=self.net_metrics.cold_start_edge,
                                 budget=self.net_metrics.local_budget,
                                 local_usable_memory_coeff=1.0 #fixme da calcolare
        )

        # TODO impacchetta le probabilità aggiornate e restituisci al client


def serve():
    # Create a pool with 12 threads to execute code
    pool = futures.ThreadPoolExecutor(max_workers=12)
    # Execute periodic update of metrics
    pool.submit(periodic_show)
    pool.submit(publish)

    # wait for all tasks to complete
    pool.shutdown(wait=True)
