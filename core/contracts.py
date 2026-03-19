"""
This module defines a set of rules (interfaces) that different parts of the program follow to communicate with each other. 
So instead of modules directly depending on one another, they rely on these shared rules, which helps to keep the code clean, flexible, and easier to maintain. 
"""

from typing import Protocol, List, Dict, Any


class DataSink(Protocol):
# This DataSink is used by the Core to send the processed data to the Output.
# The Output module uses this method, so that the Core does not need to know about the GUI.
    def write(self, records: List[Dict[str, Any]]) -> None:
        ...


class PipelineService(Protocol):
# This PipelineService is used by the Input part to send data to the Core.
# The Core uses this method, so that the Input does not need to know about Core directly.
    def process_packet(self, packet: Dict[str, Any]) -> None:
        ...


class TelemetryObserver(Protocol):
# This means any kind of class that wants to get updates must utilize this method.
# For example, DashboardGUI uses it to receive data.
# This method is called when new data is available.
    def update(self, telemetry_data: Dict[str, Any]) -> None:
        ...
