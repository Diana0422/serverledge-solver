# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: solver.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0csolver.proto\x12\x06solver\"\x88\x02\n\x07Request\x12\x1d\n\x15offload_latency_cloud\x18\x01 \x02(\x02\x12\x1c\n\x14offload_latency_edge\x18\x02 \x02(\x02\x12#\n\tfunctions\x18\x03 \x03(\x0b\x32\x10.solver.Function\x12!\n\x07\x63lasses\x18\x04 \x03(\x0b\x32\x10.solver.QosClass\x12\x12\n\ncost_cloud\x18\x05 \x02(\x02\x12\x14\n\x0cmemory_local\x18\n \x02(\x02\x12\x11\n\tcpu_local\x18\x0b \x02(\x02\x12\x18\n\x10memory_aggregate\x18\x0c \x02(\x02\x12!\n\x19usable_memory_coefficient\x18\r \x02(\x02\"9\n\x12\x46unctionInvocation\x12\x11\n\tqos_class\x18\x01 \x02(\t\x12\x10\n\x08\x61rrivals\x18\x02 \x02(\x02\"\x90\x03\n\x08\x46unction\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0e\n\x06memory\x18\x02 \x02(\x05\x12\x0b\n\x03\x63pu\x18\x03 \x02(\x02\x12/\n\x0binvocations\x18\x04 \x03(\x0b\x32\x1a.solver.FunctionInvocation\x12\x10\n\x08\x64uration\x18\x05 \x02(\x02\x12 \n\x18\x64uration_offloaded_cloud\x18\x06 \x02(\x02\x12\x1f\n\x17\x64uration_offloaded_edge\x18\x07 \x02(\x02\x12\x11\n\tinit_time\x18\x08 \x02(\x02\x12!\n\x19init_time_offloaded_cloud\x18\t \x02(\x02\x12 \n\x18init_time_offloaded_edge\x18\n \x02(\x02\x12\r\n\x05pcold\x18\x0b \x02(\x02\x12\x1d\n\x15pcold_offloaded_cloud\x18\x0c \x02(\x02\x12\x1c\n\x14pcold_offloaded_edge\x18\r \x02(\x02\x12\x17\n\x0f\x62\x61ndwidth_cloud\x18\x0e \x02(\x02\x12\x16\n\x0e\x62\x61ndwidth_edge\x18\x0f \x02(\x02\"b\n\x08QosClass\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0f\n\x07utility\x18\x02 \x02(\x02\x12\x19\n\x11max_response_time\x18\x03 \x02(\x02\x12\x1c\n\x14\x63ompleted_percentage\x18\x04 \x02(\x02\"\\\n\rClassResponse\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\n\n\x02pL\x18\x02 \x02(\x02\x12\n\n\x02pC\x18\x03 \x02(\x02\x12\n\n\x02pE\x18\x04 \x02(\x02\x12\n\n\x02pD\x18\x05 \x02(\x02\x12\r\n\x05share\x18\x06 \x02(\x02\"P\n\x10\x46unctionResponse\x12\x0c\n\x04name\x18\x01 \x02(\t\x12.\n\x0f\x63lass_responses\x18\x02 \x03(\x0b\x32\x15.solver.ClassResponse\"L\n\x08Response\x12,\n\nf_response\x18\x01 \x03(\x0b\x32\x18.solver.FunctionResponse\x12\x12\n\ntime_taken\x18\x02 \x02(\x02\x32\x34\n\x06Solver\x12*\n\x05Solve\x12\x0f.solver.Request\x1a\x10.solver.ResponseB$Z\"github.com/grussorusso/serverledge')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'solver_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'Z\"github.com/grussorusso/serverledge'
  _globals['_REQUEST']._serialized_start=25
  _globals['_REQUEST']._serialized_end=289
  _globals['_FUNCTIONINVOCATION']._serialized_start=291
  _globals['_FUNCTIONINVOCATION']._serialized_end=348
  _globals['_FUNCTION']._serialized_start=351
  _globals['_FUNCTION']._serialized_end=751
  _globals['_QOSCLASS']._serialized_start=753
  _globals['_QOSCLASS']._serialized_end=851
  _globals['_CLASSRESPONSE']._serialized_start=853
  _globals['_CLASSRESPONSE']._serialized_end=945
  _globals['_FUNCTIONRESPONSE']._serialized_start=947
  _globals['_FUNCTIONRESPONSE']._serialized_end=1027
  _globals['_RESPONSE']._serialized_start=1029
  _globals['_RESPONSE']._serialized_end=1105
  _globals['_SOLVER']._serialized_start=1107
  _globals['_SOLVER']._serialized_end=1159
# @@protoc_insertion_point(module_scope)
