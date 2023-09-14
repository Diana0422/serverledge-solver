from proto import solver_pb2_grpc, solver_pb2
import grpc
from concurrent import futures
import properties as p


# the gRPC server functions
class Estimator(solver_pb2_grpc.SolverServicer):

    # this is called by the frontend when asking the consumptions for all product in pantry
    def Solve(self, request: solver_pb2.Request, context):
        """
        Get the prediction values on request
        :param request: the prediction request
        :param context: the context
        :return: the list of the predictions
        """
        print("Received request")


def serve():
    # Publish service
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solver_pb2_grpc.add_SolverServicer_to_server(Estimator(), server)
    properties = p.Props()
    print(f"Python server started at port {properties.ServerPort}")
    server.add_insecure_port("[::]:" + str(properties.ServerPort))
    server.start()
    server.wait_for_termination()
