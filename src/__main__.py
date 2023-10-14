# !/usr/bin/python3
import sys
import server


# python -m grpc_tools.protoc -I ../../proto --python_out=. --pyi_out=. --grpc_python_out=. ../../proto/*.proto
# --experimental_allow_proto3_optional

def exception_handler(exception_type, exception, traceback):
    # All your trace are belong to us! This is the format for the stack traces:
    print("%s: %s" % (exception_type.__name__, exception))


def main():
    # this is needed to print less stack trace!
    sys.excepthook = exception_handler
    # Start the gRPC server
    server.serve()


main()
