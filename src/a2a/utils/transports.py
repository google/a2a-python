"""Defines standard protocol transport labels."""
from enum import Enum

class Transports(str, Enum):
    GRPC = "GRPC"
    JSONRPC = "JSONRPC"
    RESTful = "HTTP+JSON"
