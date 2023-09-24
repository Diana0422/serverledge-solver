from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Request(_message.Message):
    __slots__ = ["offload_latency_cloud", "offload_latency_edge", "functions", "classes", "cost_cloud", "memory_local", "cpu_local", "memory_aggregate", "usable_memory_coefficient"]
    OFFLOAD_LATENCY_CLOUD_FIELD_NUMBER: _ClassVar[int]
    OFFLOAD_LATENCY_EDGE_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    CLASSES_FIELD_NUMBER: _ClassVar[int]
    COST_CLOUD_FIELD_NUMBER: _ClassVar[int]
    MEMORY_LOCAL_FIELD_NUMBER: _ClassVar[int]
    CPU_LOCAL_FIELD_NUMBER: _ClassVar[int]
    MEMORY_AGGREGATE_FIELD_NUMBER: _ClassVar[int]
    USABLE_MEMORY_COEFFICIENT_FIELD_NUMBER: _ClassVar[int]
    offload_latency_cloud: float
    offload_latency_edge: float
    functions: _containers.RepeatedCompositeFieldContainer[Function]
    classes: _containers.RepeatedCompositeFieldContainer[QosClass]
    cost_cloud: float
    memory_local: float
    cpu_local: float
    memory_aggregate: float
    usable_memory_coefficient: float
    def __init__(self, offload_latency_cloud: _Optional[float] = ..., offload_latency_edge: _Optional[float] = ..., functions: _Optional[_Iterable[_Union[Function, _Mapping]]] = ..., classes: _Optional[_Iterable[_Union[QosClass, _Mapping]]] = ..., cost_cloud: _Optional[float] = ..., memory_local: _Optional[float] = ..., cpu_local: _Optional[float] = ..., memory_aggregate: _Optional[float] = ..., usable_memory_coefficient: _Optional[float] = ...) -> None: ...

class FunctionInvocation(_message.Message):
    __slots__ = ["qos_class", "arrivals"]
    QOS_CLASS_FIELD_NUMBER: _ClassVar[int]
    ARRIVALS_FIELD_NUMBER: _ClassVar[int]
    qos_class: str
    arrivals: float
    def __init__(self, qos_class: _Optional[str] = ..., arrivals: _Optional[float] = ...) -> None: ...

class Function(_message.Message):
    __slots__ = ["name", "memory", "cpu", "invocations", "duration", "duration_offloaded_cloud", "duration_offloaded_edge", "init_time", "init_time_offloaded_cloud", "init_time_offloaded_edge", "pcold", "pcold_offloaded_cloud", "pcold_offloaded_edge", "bandwidth_cloud", "bandwidth_edge"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    MEMORY_FIELD_NUMBER: _ClassVar[int]
    CPU_FIELD_NUMBER: _ClassVar[int]
    INVOCATIONS_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    DURATION_OFFLOADED_CLOUD_FIELD_NUMBER: _ClassVar[int]
    DURATION_OFFLOADED_EDGE_FIELD_NUMBER: _ClassVar[int]
    INIT_TIME_FIELD_NUMBER: _ClassVar[int]
    INIT_TIME_OFFLOADED_CLOUD_FIELD_NUMBER: _ClassVar[int]
    INIT_TIME_OFFLOADED_EDGE_FIELD_NUMBER: _ClassVar[int]
    PCOLD_FIELD_NUMBER: _ClassVar[int]
    PCOLD_OFFLOADED_CLOUD_FIELD_NUMBER: _ClassVar[int]
    PCOLD_OFFLOADED_EDGE_FIELD_NUMBER: _ClassVar[int]
    BANDWIDTH_CLOUD_FIELD_NUMBER: _ClassVar[int]
    BANDWIDTH_EDGE_FIELD_NUMBER: _ClassVar[int]
    name: str
    memory: int
    cpu: float
    invocations: _containers.RepeatedCompositeFieldContainer[FunctionInvocation]
    duration: float
    duration_offloaded_cloud: float
    duration_offloaded_edge: float
    init_time: float
    init_time_offloaded_cloud: float
    init_time_offloaded_edge: float
    pcold: float
    pcold_offloaded_cloud: float
    pcold_offloaded_edge: float
    bandwidth_cloud: float
    bandwidth_edge: float
    def __init__(self, name: _Optional[str] = ..., memory: _Optional[int] = ..., cpu: _Optional[float] = ..., invocations: _Optional[_Iterable[_Union[FunctionInvocation, _Mapping]]] = ..., duration: _Optional[float] = ..., duration_offloaded_cloud: _Optional[float] = ..., duration_offloaded_edge: _Optional[float] = ..., init_time: _Optional[float] = ..., init_time_offloaded_cloud: _Optional[float] = ..., init_time_offloaded_edge: _Optional[float] = ..., pcold: _Optional[float] = ..., pcold_offloaded_cloud: _Optional[float] = ..., pcold_offloaded_edge: _Optional[float] = ..., bandwidth_cloud: _Optional[float] = ..., bandwidth_edge: _Optional[float] = ...) -> None: ...

class QosClass(_message.Message):
    __slots__ = ["name", "utility", "max_response_time", "completed_percentage"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    UTILITY_FIELD_NUMBER: _ClassVar[int]
    MAX_RESPONSE_TIME_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    name: str
    utility: float
    max_response_time: float
    completed_percentage: float
    def __init__(self, name: _Optional[str] = ..., utility: _Optional[float] = ..., max_response_time: _Optional[float] = ..., completed_percentage: _Optional[float] = ...) -> None: ...

class ClassResponse(_message.Message):
    __slots__ = ["name", "pL", "pC", "pE", "pD", "share"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PL_FIELD_NUMBER: _ClassVar[int]
    PC_FIELD_NUMBER: _ClassVar[int]
    PE_FIELD_NUMBER: _ClassVar[int]
    PD_FIELD_NUMBER: _ClassVar[int]
    SHARE_FIELD_NUMBER: _ClassVar[int]
    name: str
    pL: float
    pC: float
    pE: float
    pD: float
    share: float
    def __init__(self, name: _Optional[str] = ..., pL: _Optional[float] = ..., pC: _Optional[float] = ..., pE: _Optional[float] = ..., pD: _Optional[float] = ..., share: _Optional[float] = ...) -> None: ...

class FunctionResponse(_message.Message):
    __slots__ = ["name", "class_responses"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CLASS_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    name: str
    class_responses: _containers.RepeatedCompositeFieldContainer[ClassResponse]
    def __init__(self, name: _Optional[str] = ..., class_responses: _Optional[_Iterable[_Union[ClassResponse, _Mapping]]] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["f_response", "time_taken"]
    F_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    TIME_TAKEN_FIELD_NUMBER: _ClassVar[int]
    f_response: _containers.RepeatedCompositeFieldContainer[FunctionResponse]
    time_taken: float
    def __init__(self, f_response: _Optional[_Iterable[_Union[FunctionResponse, _Mapping]]] = ..., time_taken: _Optional[float] = ...) -> None: ...
