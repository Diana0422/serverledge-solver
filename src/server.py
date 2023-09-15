from proto import solver_pb2_grpc, solver_pb2
import grpc
from concurrent import futures
import threading
import properties as p
import optimizer as opt

WAIT_TIME_SECONDS = 120


def update_metrics():
    print("Sto aggiornando le metriche")
    # TODO: aggiorna aggregated_edge_memory
    # TODO: aggiorna arrival rates
    # TODO: aggiorna bandwidth cloud
    # TODO: aggiorna bandwidth edge

    # TODO (forse): aggiorna service_time
    # TODO (forse): aggiorna service_time_cloud
    # TODO (forse): aggiorna service_time_edge
    # TODO (forse): aggiorna init_time
    # TODO (forse): aggiorna init_time_cloud
    # TODO (forse): aggiorna init_time_edge
    # TODO (forse): aggiorna cold_start
    # TODO (forse): aggiorna cold_start_cloud
    # TODO (forse): aggiorna cold_start_edge


def periodic_update():
    # Execute periodic update of metrics
    ticker = threading.Event()
    while not ticker.wait(WAIT_TIME_SECONDS):
        update_metrics()


def publish():
    # Publish service
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solver_pb2_grpc.add_SolverServicer_to_server(Estimator(), server)
    properties = p.Props()
    print(f"Python server started at port {properties.ServerPort}")
    server.add_insecure_port("[::]:" + str(properties.ServerPort))
    server.start()
    server.wait_for_termination()


# the gRPC server functions
class Estimator(solver_pb2_grpc.SolverServicer):

    # this is called by the client when is required the execution of a function
    def Solve(self, request: solver_pb2.Request, context):
        """
        Get the prediction values on request
        :param request: the prediction request
        :param context: the context
        :return: the list of the predictions
        """
        print("Received request")

        # TODO: impostare param local
        # local è il contesto del nodo che ha inviato la richiesta e mantiene tutte le info che lo riguardano, tipo la memoria disponibile
        # TODO: impostare param cloud
        # cloud è il contesto del nodo "cloud" e mantiene tutte le info che lo riguardano, tipo la memoria disponibile
        # TODO: raccogli param aggregated_edge_memory
        # TODO: raccogli param sim
        # TODO: raccogli param arrival_rates
        # Function parameters (given)
        for _, function in request.functions:
            serviceTime = function.duration
            serviceTimeCloud = function.duration_offloaded_cloud
            serviceTimeEdge = function.init_time_offloaded_edge
            initTime = function.init_time
            initTimeCloud = function.init_time_offloaded_cloud
            initTimeEdge = function.init_time_offloaded_edge
            coldStart = function.pcold
            coldStartCloud = function.pcold_offloaded_cloud
            coldStartEdge = function.pcold_offloaded_edge

        # TODO opt.update_probabilities()

        # TODO impacchetta le probabilità aggiornate e restituisci al client


def serve():
    # Create a pool with 12 threads to execute code
    pool = futures.ThreadPoolExecutor(max_workers=12)
    # Execute periodic update of metrics
    pool.submit(periodic_update)
    pool.submit(publish)

    # wait for all tasks to complete
    pool.shutdown(wait=True)
