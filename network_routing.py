from __future__ import annotations

import heapq
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NetworkRouting:
    """
    Weighted undirected graph representing the machine infrastructure.

    Nodes  = machine IDs (str)
    Edges  = (machine_a, machine_b, weight)  where weight = network latency / cost

    Core operation: find_optimal_machine(source, candidates) runs Dijkstra
    from *source* and returns the candidate with the lowest path cost.
    """

    def __init__(self) -> None:
        # adjacency list: node_id → list of (neighbour_id, weight)
        self._graph: dict[str, list[tuple[str, float]]] = {}


    # Graph mutation
    
    def add_machine(self, machine_id: str) -> None:
        """Register a node in the graph (idempotent)."""
        if machine_id not in self._graph:
            self._graph[machine_id] = []
            logger.debug("NetworkRouting: added node %s", machine_id)

    def remove_machine(self, machine_id: str) -> bool:
        """
        Remove a node and all edges incident to it.
        Returns True if the node existed, False otherwise.
        """
        if machine_id not in self._graph:
            return False

        del self._graph[machine_id]
        # Remove all edges pointing to this node
        for neighbours in self._graph.values():
            neighbours[:] = [(n, w) for n, w in neighbours if n != machine_id]

        logger.debug("NetworkRouting: removed node %s", machine_id)
        return True

    def add_connection(self, from_id: str, to_id: str, weight: float) -> None:
        """
        Add an undirected edge between two machines.
        Both nodes are auto-created if they don't exist yet.
        Raises ValueError if weight is non-positive.
        """
        if weight <= 0:
            raise ValueError(f"Edge weight must be positive, got {weight!r}")

        self.add_machine(from_id)
        self.add_machine(to_id)

        self._graph[from_id].append((to_id, weight))
        self._graph[to_id].append((from_id, weight))
        logger.debug("NetworkRouting: added edge %s ↔ %s (weight=%s)", from_id, to_id, weight)

    def remove_connection(self, from_id: str, to_id: str) -> bool:
        """Remove the undirected edge between two nodes (if it exists)."""
        changed = False
        if from_id in self._graph:
            before = len(self._graph[from_id])
            self._graph[from_id] = [(n, w) for n, w in self._graph[from_id] if n != to_id]
            changed = len(self._graph[from_id]) < before
        if to_id in self._graph:
            self._graph[to_id] = [(n, w) for n, w in self._graph[to_id] if n != from_id]
        return changed

    
    # Dijkstra


    def _dijkstra(self, source: str) -> dict[str, float]:
        """
        Run Dijkstra from *source* and return a dict mapping every reachable
        node to its shortest-path cost from source.
        """
        if source not in self._graph:
            raise KeyError(f"Source node {source!r} not in graph.")

        dist: dict[str, float] = {node: math.inf for node in self._graph}
        dist[source] = 0.0

        # min-heap entries: (cost, node_id)
        heap: list[tuple[float, str]] = [(0.0, source)]

        while heap:
            current_cost, current_node = heapq.heappop(heap)

            # Stale entry — skip
            if current_cost > dist[current_node]:
                continue

            for neighbour, weight in self._graph.get(current_node, []):
                new_cost = current_cost + weight
                if new_cost < dist[neighbour]:
                    dist[neighbour] = new_cost
                    heapq.heappush(heap, (new_cost, neighbour))

        return dist

    def _dijkstra_with_path(
        self, source: str
    ) -> tuple[dict[str, float], dict[str, Optional[str]]]:
        """
        Dijkstra that also tracks the predecessor of each node so that the
        full path can be reconstructed.

        Returns (dist, prev) where prev[node] = the node visited just before
        it on the shortest path from source.
        """
        if source not in self._graph:
            raise KeyError(f"Source node {source!r} not in graph.")

        dist: dict[str, float] = {node: math.inf for node in self._graph}
        prev: dict[str, Optional[str]] = {node: None for node in self._graph}
        dist[source] = 0.0

        heap: list[tuple[float, str]] = [(0.0, source)]

        while heap:
            current_cost, current_node = heapq.heappop(heap)
            if current_cost > dist[current_node]:
                continue
            for neighbour, weight in self._graph.get(current_node, []):
                new_cost = current_cost + weight
                if new_cost < dist[neighbour]:
                    dist[neighbour] = new_cost
                    prev[neighbour] = current_node
                    heapq.heappush(heap, (new_cost, neighbour))

        return dist, prev

    @staticmethod
    def _reconstruct_path(prev: dict[str, Optional[str]], target: str) -> list[str]:
        path: list[str] = []
        current: Optional[str] = target
        while current is not None:
            path.append(current)
            current = prev.get(current)
        return list(reversed(path))

    
    # Public routing API

    def find_optimal_machine(
        self,
        source: str,
        candidates: list[str],
    ) -> tuple[Optional[str], float]:
        """
        From *source*, find the candidate machine with the lowest Dijkstra
        path cost.

        Returns (best_machine_id, cost).
        Returns (None, inf) if no candidate is reachable.
        """
        if not candidates:
            return None, math.inf

        try:
            dist = self._dijkstra(source)
        except KeyError as exc:
            logger.error("find_optimal_machine: %s", exc)
            return None, math.inf

        best_id: Optional[str] = None
        best_cost: float = math.inf

        for candidate in candidates:
            cost = dist.get(candidate, math.inf)
            if cost < best_cost:
                best_cost = cost
                best_id = candidate

        if best_id is None:
            logger.warning(
                "No reachable candidate from %s among %s", source, candidates
            )

        return best_id, best_cost

    def get_path_cost(self, source: str, target: str) -> float:
        """Return the shortest path cost between two nodes. Returns inf if unreachable."""
        try:
            dist = self._dijkstra(source)
            return dist.get(target, math.inf)
        except KeyError:
            return math.inf

    def get_full_path(self, source: str, target: str) -> tuple[list[str], float]:
        """
        Return (path, cost) where path is the list of nodes on the shortest
        route from source to target. path is empty if unreachable.
        """
        try:
            dist, prev = self._dijkstra_with_path(source)
        except KeyError:
            return [], math.inf

        cost = dist.get(target, math.inf)
        if cost == math.inf:
            return [], math.inf

        return self._reconstruct_path(prev, target), cost

    # Introspection

    @property
    def nodes(self) -> list[str]:
        return list(self._graph.keys())

    @property
    def edge_count(self) -> int:
        return sum(len(neighbours) for neighbours in self._graph.values()) // 2

    def __repr__(self) -> str:
        return f"NetworkRouting(nodes={len(self._graph)}, edges={self.edge_count})"
