# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import solver_pb2 as solver__pb2


class SolverStub(object):
    """service which can be executed
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Solve = channel.unary_unary(
                '/solver.Solver/Solve',
                request_serializer=solver__pb2.Request.SerializeToString,
                response_deserializer=solver__pb2.Response.FromString,
                )


class SolverServicer(object):
    """service which can be executed
    """

    def Solve(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_SolverServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Solve': grpc.unary_unary_rpc_method_handler(
                    servicer.Solve,
                    request_deserializer=solver__pb2.Request.FromString,
                    response_serializer=solver__pb2.Response.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'solver.Solver', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Solver(object):
    """service which can be executed
    """

    @staticmethod
    def Solve(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/solver.Solver/Solve',
            solver__pb2.Request.SerializeToString,
            solver__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
