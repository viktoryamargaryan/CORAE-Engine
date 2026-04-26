from __future__ import annotations

import logging
from typing import Optional

from structures import AVLTree, Machine, Job
from network_routing import NetworkRouting

logger = logging.getLogger(__name__)


class AllocationEngine:
    """
    Central dispatch engine that combines:
      - AVL Tree  → O(log n) best-fit capacity lookup
      - Hash Map  → O(1) machine state validation
      - Dijkstra  → cheapest network path among capacity-qualified machines
    """

    def __init__(self, network: Optional[NetworkRouting] = None) -> None:
        self._tree = AVLTree()
        self._root = None                          # AVL tree root
        self._machines: dict[str, Machine] = {}   # Hash Map: id → Machine
        self._network: NetworkRouting = network or NetworkRouting()

    
    # Machine lifecycle
    
    def register_machine(self, machine: Machine) -> None:
        """
        Add a machine to the resource pool.
        Inserts into AVL tree (O log n) and hash map (O 1), and registers
        the node in the network graph so Dijkstra can route to it.
        """
        if machine.machine_id in self._machines:
            logger.warning("Machine %s already registered; skipping.", machine.machine_id)
            return

        self._root = self._tree.insert(self._root, machine)
        self._machines[machine.machine_id] = machine
        self._network.add_machine(machine.machine_id)
        logger.info("Registered machine %s (capacity=%s, cost=%s)",
                    machine.machine_id, machine.capacity, machine.cost)

    def remove_machine(self, machine_id: str) -> bool:
        """
        Remove a machine from the pool at runtime.
        Returns True if the machine was found and removed, False otherwise.
        """
        if machine_id not in self._machines:
            logger.warning("remove_machine: %s not found.", machine_id)
            return False

        self._root = self._tree.delete(self._root, machine_id)
        del self._machines[machine_id]
        logger.info("Removed machine %s from pool.", machine_id)
        return True

    def release_machine(self, machine_id: str) -> bool:
        """
        Mark a machine as available again after its job finishes.
        Returns True on success.
        """
        machine = self._machines.get(machine_id)
        if machine is None:
            logger.warning("release_machine: %s not found.", machine_id)
            return False

        machine.status = "available"
        machine.current_load = 0.0
        logger.info("Machine %s is now available.", machine_id)
        return True

    def add_network_link(self, from_id: str, to_id: str, weight: float) -> None:
        """Add a weighted edge to the network graph (used for Dijkstra routing)."""
        self._network.add_connection(from_id, to_id, weight)

    
    # Core allocation

    def allocate(
        self,
        job: Job,
        dispatch_point: str = "Scheduler",
    ) -> Optional[str]:
        """
        Find the optimal machine for *job* and mark it busy.

        Strategy:
          1. AVL Tree → find the best-fit machine by capacity (O log n).
          2. Collect up to `candidate_limit` additional machines that qualify.
          3. Dijkstra on the network graph → pick the cheapest reachable one.
          4. Mark the winner busy and return its ID.

        Returns machine_id on success, None when no suitable machine exists.
        """
        # Step 1: collect all available machines that meet the capacity requirement
        # (inorder traversal of AVL tree gives ascending-capacity order)
        candidates = [
            m.machine_id
            for m in self._tree.inorder(self._root)
            if m.capacity >= job.required_capacity and m.status == "available"
        ]

        if not candidates:
            logger.warning("No available machines for job %s (needs %s).",
                           job.job_id, job.required_capacity)
            return None

        # Step 2: Dijkstra to pick cheapest reachable candidate
        best_machine_id, network_cost = self._network.find_optimal_machine(
            dispatch_point, candidates
        )

        if best_machine_id is None:
            # Dijkstra found no network path — fall back to AVL best-fit
            best_fit = self._tree.find_best_fit(self._root, job.required_capacity)
            if best_fit is None:
                return None
            best_machine_id = best_fit.machine_id
            network_cost = 0.0
            logger.info(
                "No network path found; falling back to AVL best-fit: %s",
                best_machine_id,
            )

        # Step 3: guard — machine may have been removed after Dijkstra ran
        if best_machine_id not in self._machines:
            logger.warning("Dijkstra selected %s but it was removed; retrying.",
                           best_machine_id)
            candidates = [c for c in candidates if c != best_machine_id]
            if not candidates:
                return None
            best_machine_id = candidates[0]
            network_cost = 0.0

        # Step 4: mark the chosen machine busy
        chosen = self._machines[best_machine_id]
        chosen.status = "busy"
        chosen.current_load = job.required_capacity
        chosen.job_history.append(job.job_id)

        logger.info(
            "Job %s → Machine %s  (capacity=%s, network_cost=%s)",
            job.job_id, best_machine_id, chosen.capacity, network_cost,
        )
        return best_machine_id

    

    # Queries
    
    def get_machine_info(self, machine_id: str) -> Optional[Machine]:
        """O(1) lookup via hash map. Returns None if not found."""
        return self._machines.get(machine_id)

    def get_all_machines(self) -> list[Machine]:
        """Return all machines in ascending capacity order (inorder traversal)."""
        return list(self._tree.inorder(self._root))

    def pool_summary(self) -> dict:
        """Return a concise summary dict suitable for JSON serialisation."""
        machines = self.get_all_machines()
        return {
            "total": len(machines),
            "available": sum(1 for m in machines if m.status == "available"),
            "busy": sum(1 for m in machines if m.status == "busy"),
            "offline": sum(1 for m in machines if m.status == "offline"),
            "machines": [
                {
                    "id": m.machine_id,
                    "capacity": m.capacity,
                    "cost": m.cost,
                    "status": m.status,
                    "current_load": m.current_load,
                }
                for m in machines
            ],
        }
