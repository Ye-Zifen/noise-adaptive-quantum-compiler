from __future__ import annotations

import math
from typing import Literal

import networkx as nx
from pydantic.v1 import BaseModel, Field, root_validator, validator

TRACK_A_BASIS = (
    "x",
    "y",
    "z",
    "h",
    "s",
    "sdg",
    "t",
    "tdg",
    "rx",
    "ry",
    "rz",
    "cx",
    "measure",
)
TRACK_B_CLIFFORD_BASIS = ("x", "y", "z", "h", "s", "sdg", "cx", "measure")
SUPPORTED_BASIS = set(TRACK_A_BASIS)


class CompetitionBackend(BaseModel):
    schema_version: str = Field(..., min_length=1)
    snapshot_id: str = Field(..., min_length=1)
    size_class: Literal["small", "medium", "large"]
    num_qubits: int = Field(..., ge=1)
    basis_gates: list[str]
    coupling_map: list[tuple[int, int]]
    two_qubit_error: dict[str, float]
    readout_error: dict[str, float]
    single_qubit_error: float = Field(0.0, ge=0.0, lt=1.0)

    @validator("basis_gates")
    def validate_basis_gates(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("basis_gates must not contain duplicates")
        if "measure" not in value:
            raise ValueError("basis_gates must include measure")
        if "swap" in value:
            raise ValueError("swap is not a v1 basis gate; decompose swaps into cx gates")
        unsupported = sorted(set(value) - SUPPORTED_BASIS)
        if unsupported:
            raise ValueError(f"unsupported basis gates: {unsupported}")
        return value

    @root_validator
    def validate_connectivity(cls, values: dict) -> dict:
        if values.get("schema_version") != "2.0":
            raise ValueError("backend schema_version must be 2.0")
        num_qubits = values["num_qubits"]
        valid_ids = set(range(num_qubits))
        coupling_map = values["coupling_map"]
        edge_keys = values["two_qubit_error"]
        readout = values["readout_error"]

        if set(int(key) for key in readout) != valid_ids:
            raise ValueError("readout_error must cover all physical qubits")
        for qubit, error in readout.items():
            if not 0 <= error < 1:
                raise ValueError(f"readout_error for qubit {qubit} must be in [0, 1)")

        coupling_edges = {tuple(edge) for edge in coupling_map}
        if len(coupling_edges) != len(coupling_map):
            raise ValueError("coupling_map must not contain duplicate edges")
        for control, target in coupling_edges:
            if control not in valid_ids or target not in valid_ids:
                raise ValueError("coupling_map references unknown qubits")
            if control == target:
                raise ValueError("coupling_map cannot contain self loops")
        for edge_key in edge_keys:
            control, target = _parse_edge_key(edge_key)
            if (control, target) not in coupling_edges and (target, control) not in coupling_edges:
                raise ValueError(f"two_qubit_error edge {edge_key} missing from coupling_map")
            if not 0 <= edge_keys[edge_key] < 1:
                raise ValueError(f"two_qubit_error for edge {edge_key} must be in [0, 1)")
        missing = [
            f"{control}-{target}"
            for control, target in coupling_edges
            if f"{control}-{target}" not in edge_keys and f"{target}-{control}" not in edge_keys
        ]
        if missing:
            raise ValueError(f"two_qubit_error missing coupling edges: {missing}")
        return values

    def graph(self) -> nx.Graph:
        graph = nx.Graph()
        for qubit in range(self.num_qubits):
            graph.add_node(qubit, readout_reliability=1.0 - self.readout_error[str(qubit)])
        for control, target in self.coupling_map:
            reliability = 1.0 - self.edge_error(control, target)
            graph.add_edge(control, target, reliability=max(reliability, 1e-9), cost=-math.log(max(reliability, 1e-9)))
        return graph

    def edge_error(self, control: int, target: int) -> float:
        for key in (f"{control}-{target}", f"{target}-{control}"):
            if key in self.two_qubit_error:
                return self.two_qubit_error[key]
        raise KeyError(f"missing two_qubit_error for edge {(control, target)}")

    def readout(self, qubit: int) -> float:
        return self.readout_error[str(qubit)]

    def shortest_path(self, start: int, stop: int) -> list[int]:
        return nx.shortest_path(self.graph(), start, stop)

    def most_reliable_path(self, start: int, stop: int) -> list[int]:
        return nx.shortest_path(self.graph(), start, stop, weight="cost")


def _parse_edge_key(value: str) -> tuple[int, int]:
    left, right = value.split("-")
    return int(left), int(right)
