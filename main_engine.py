"""
main_engine.py — Full end-to-end demo combining Dijkstra routing and the AVL
allocation engine with random job workloads.
"""

from __future__ import annotations

import logging
import time

from structures import Machine
from engine import AllocationEngine
from network_routing import NetworkRouting
from job_simulator import generate_jobs, generate_mixed_workload

logging.basicConfig(level=logging.WARNING, format="%(levelname)-8s %(message)s")
log = logging.getLogger(__name__)


# Network topology builder

def build_network() -> tuple[AllocationEngine, NetworkRouting]:
    """
    Construct a sample network and return a fully wired AllocationEngine.

    Topology (edge weights = latency/cost units):

        Scheduler ──5── M2 ──8── M4
              └──10── M1 ──2── M3
    """
    network = NetworkRouting()
    network.add_machine("Scheduler")

    engine = AllocationEngine(network=network)

    # Register machines with varied capacity and cost
    for mid, cap, cost in [
        ("M1", 30,  8),
        ("M2", 60, 15),
        ("M3", 20,  5),
        ("M4", 90, 35),
    ]:
        engine.register_machine(Machine(mid, cap, cost))

    # Wire the network
    engine.add_network_link("Scheduler", "M1", 10)
    engine.add_network_link("Scheduler", "M2",  5)
    engine.add_network_link("M1",        "M3",  2)
    engine.add_network_link("M2",        "M4",  8)

    return engine, network

# Main demo

def run_allocation_system() -> None:
    print("\n" + "=" * 65)
    print("  CORAE — Full Allocation System Demo")
    print("=" * 65)

    engine, network = build_network()

    jobs = generate_mixed_workload(total=12, seed=42)

    print(f"\nDispatching {len(jobs)} mixed jobs …\n")
    print(f"  {'Job':<12} {'Needs':>7}  {'Machine':>8}  {'Path'}")
    print("  " + "-" * 55)

    allocated = 0
    failed = 0

    for job in jobs:
        machine_id = engine.allocate(job, dispatch_point="Scheduler")
        if machine_id:
            path, cost = network.get_full_path("Scheduler", machine_id)
            path_str = " → ".join(path) if path else machine_id
            print(f"  {job.job_id:<12} {job.required_capacity:>7.1f}  {machine_id:>8}  {path_str}  (cost={cost:.1f})")
            allocated += 1
            # Release the machine immediately so the pool doesn't exhaust in this demo
            engine.release_machine(machine_id)
        else:
            print(f"  {job.job_id:<12} {job.required_capacity:>7.1f}  {'—':>8}  no suitable machine")
            failed += 1

    print(f"\n  Allocated: {allocated}   Failed: {failed}")


# Benchmark

def run_benchmark(machine_count: int = 200, job_count: int = 500) -> None:
    """
    Quick allocation benchmark: create a large pool and time many dispatches.
    This gives a rough comparison between AVL+Dijkstra and a hypothetical
    linear scan (O(n) baseline).
    """
    print("\n" + "=" * 65)
    print(f"  CORAE Benchmark  ({machine_count} machines, {job_count} jobs)")
    print("=" * 65)

    import random
    rng = random.Random(0)

    network = NetworkRouting()
    network.add_machine("Scheduler")
    engine = AllocationEngine(network=network)

    # Populate pool
    for i in range(machine_count):
        m = Machine(f"M{i:04d}", capacity=rng.randint(10, 100), cost=rng.randint(1, 50))
        engine.register_machine(m)
        if i > 0:
            # Connect to a random earlier machine to keep the graph connected
            peer = f"M{rng.randint(0, i-1):04d}"
            engine.add_network_link(f"M{i:04d}", peer, rng.randint(1, 20))
        else:
            engine.add_network_link("M0000", "Scheduler", 1)

    jobs = generate_jobs(job_count, seed=1, min_capacity=5, max_capacity=80)

    start = time.perf_counter()
    allocated = 0
    for job in jobs:
        mid = engine.allocate(job, dispatch_point="Scheduler")
        if mid:
            engine.release_machine(mid)
            allocated += 1
    elapsed = time.perf_counter() - start

    print(f"\n  Jobs allocated : {allocated}/{job_count}")
    print(f"  Total time     : {elapsed*1000:.1f} ms")
    print(f"  Per job (avg)  : {elapsed/job_count*1000:.3f} ms")
    print()



# Entry point

if __name__ == "__main__":
    run_allocation_system()
    run_benchmark(machine_count=100, job_count=300)
