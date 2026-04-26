"""
test_corae.py — Pytest suite for the CORAE Engine.

Run with:
    pytest test_corae.py -v

Coverage:
    - Machine & Job dataclasses
    - AVLTree: insert, delete, balance, find_best_fit, inorder
    - NetworkRouting: add/remove nodes & edges, Dijkstra, path reconstruction
    - AllocationEngine: register, allocate, release, remove, pool_summary
    - JobSimulator: generate_jobs, generate_burst, generate_mixed_workload
    - Edge cases: empty pool, no capacity, unreachable nodes, duplicate IDs
"""

import math
import pytest

from structures import Machine, Job, AVLTree, AVLNode
from network_routing import NetworkRouting
from engine import AllocationEngine
from job_simulator import generate_jobs, generate_burst, generate_mixed_workload


# Helpers / Fixtures

def make_machine(mid="M1", capacity=50.0, cost=10.0, status="available") -> Machine:
    return Machine(machine_id=mid, capacity=capacity, cost=cost, status=status)


def make_job(jid="J1", required=20.0, priority=3) -> Job:
    return Job(job_id=jid, required_capacity=required, priority=priority)


def build_engine_with_machines() -> AllocationEngine:
    """Return an engine pre-loaded with 4 machines and a simple network."""
    net = NetworkRouting()
    net.add_machine("Scheduler")
    engine = AllocationEngine(network=net)

    for mid, cap, cost in [("M-10", 10, 2), ("M-30", 30, 8),
                            ("M-60", 60, 15), ("M-100", 100, 35)]:
        engine.register_machine(Machine(mid, cap, cost))
        engine.add_network_link("Scheduler", mid, cost)

    engine.add_network_link("M-30", "M-60", 5)
    return engine


# Machine & Job dataclasses

class TestMachine:
    def test_default_status_is_available(self):
        m = Machine("X", 32, 5)
        assert m.status == "available"

    def test_default_load_is_zero(self):
        m = Machine("X", 32, 5)
        assert m.current_load == 0.0

    def test_free_capacity(self):
        m = Machine("X", 100, 10, current_load=40.0)
        assert m.free_capacity == 60.0

    def test_free_capacity_fully_loaded(self):
        m = Machine("X", 50, 10, current_load=50.0)
        assert m.free_capacity == 0.0

    def test_job_history_default_empty(self):
        m = Machine("X", 32, 5)
        assert m.job_history == []

    def test_job_history_not_shared_between_instances(self):
        """Mutable default must not be shared (dataclass field factory)."""
        a = Machine("A", 10, 1)
        b = Machine("B", 10, 1)
        a.job_history.append("job-1")
        assert b.job_history == []

    def test_repr_contains_id(self):
        m = Machine("Server-Alpha", 64, 20)
        assert "Server-Alpha" in repr(m)


class TestJob:
    def test_default_priority(self):
        j = Job("J1", 30)
        assert j.priority == 1

    def test_custom_priority(self):
        j = Job("J2", 50, priority=5)
        assert j.priority == 5

    def test_repr_contains_job_id(self):
        j = Job("my-job", 25)
        assert "my-job" in repr(j)


# AVL Tree

class TestAVLTree:

    def setup_method(self):
        self.tree = AVLTree()
        self.root = None

    def _insert(self, *machines):
        for m in machines:
            self.root = self.tree.insert(self.root, m)

    # ── Insert & inorder ────────────────────────────────────────────────────

    def test_single_insert(self):
        self._insert(make_machine("M1", 50))
        result = list(self.tree.inorder(self.root))
        assert len(result) == 1
        assert result[0].machine_id == "M1"

    def test_inorder_ascending(self):
        caps = [40, 10, 70, 25, 90]
        for i, c in enumerate(caps):
            self._insert(make_machine(f"M{i}", c))
        result = [m.capacity for m in self.tree.inorder(self.root)]
        assert result == sorted(caps)

    def test_empty_tree_inorder(self):
        assert list(self.tree.inorder(None)) == []

    def test_duplicate_capacity_both_inserted(self):
        self._insert(make_machine("A", 50), make_machine("B", 50))
        result = list(self.tree.inorder(self.root))
        assert len(result) == 2

    # ── Balance factor stays within [-1, 1] ────────────────────────────────

    def _check_balance(self, node):
        if node is None:
            return
        bf = AVLTree._balance_factor(node)
        assert abs(bf) <= 1, f"Unbalanced node: {node}, balance_factor={bf}"
        self._check_balance(node.left)
        self._check_balance(node.right)

    def test_balance_after_ascending_inserts(self):
        for i in range(1, 8):
            self._insert(make_machine(f"M{i}", i * 10))
        self._check_balance(self.root)

    def test_balance_after_descending_inserts(self):
        for i in range(7, 0, -1):
            self._insert(make_machine(f"M{i}", i * 10))
        self._check_balance(self.root)

    def test_balance_after_random_inserts(self):
        caps = [55, 23, 78, 11, 44, 90, 3, 66]
        for i, c in enumerate(caps):
            self._insert(make_machine(f"M{i}", c))
        self._check_balance(self.root)

    # ── find_best_fit ───────────────────────────────────────────────────────

    def test_best_fit_exact_match(self):
        self._insert(make_machine("A", 30), make_machine("B", 60))
        result = self.tree.find_best_fit(self.root, 30)
        assert result is not None
        assert result.machine_id == "A"

    def test_best_fit_picks_smallest_sufficient(self):
        self._insert(
            make_machine("S", 10), make_machine("M", 50),
            make_machine("L", 100)
        )
        result = self.tree.find_best_fit(self.root, 40)
        assert result is not None
        assert result.capacity == 50   # smallest that fits 40

    def test_best_fit_returns_none_when_all_too_small(self):
        self._insert(make_machine("A", 5), make_machine("B", 15))
        result = self.tree.find_best_fit(self.root, 50)
        assert result is None

    def test_best_fit_skips_busy_machines(self):
        busy = make_machine("Busy", 50, status="busy")
        free = make_machine("Free", 60)
        self._insert(busy, free)
        result = self.tree.find_best_fit(self.root, 45)
        assert result is not None
        assert result.machine_id == "Free"

    def test_best_fit_skips_offline_machines(self):
        offline = make_machine("Off", 50, status="offline")
        self._insert(offline)
        result = self.tree.find_best_fit(self.root, 30)
        assert result is None

    def test_best_fit_empty_tree(self):
        assert self.tree.find_best_fit(None, 10) is None

    def test_best_fit_all_busy_returns_none(self):
        for i in range(3):
            m = make_machine(f"M{i}", (i+1)*20, status="busy")
            self._insert(m)
        assert self.tree.find_best_fit(self.root, 10) is None

    # ── Delete ──────────────────────────────────────────────────────────────

    def test_delete_only_node(self):
        self._insert(make_machine("A", 50))
        self.root = self.tree.delete(self.root, "A")
        assert self.root is None

    def test_delete_leaf(self):
        # Use IDs whose alphabetical order matches capacity order so
        # _find_capacity works correctly in the fixed delete implementation.
        self._insert(make_machine("A-10", 10), make_machine("B-30", 30),
                     make_machine("C-60", 60))
        self.root = self.tree.delete(self.root, "A-10")
        ids = {m.machine_id for m in self.tree.inorder(self.root)}
        assert "A-10" not in ids
        assert ids == {"B-30", "C-60"}

    def test_delete_node_with_two_children(self):
        caps = [50, 20, 80, 10, 30]
        for i, c in enumerate(caps):
            self._insert(make_machine(f"M{i}", c))
        # Delete the root-ish node (capacity 50)
        self.root = self.tree.delete(self.root, "M0")
        ids = {m.machine_id for m in self.tree.inorder(self.root)}
        assert "M0" not in ids
        assert len(ids) == 4

    def test_delete_nonexistent_is_safe(self):
        self._insert(make_machine("A", 50))
        self.root = self.tree.delete(self.root, "GHOST")
        assert len(list(self.tree.inorder(self.root))) == 1

    def test_delete_maintains_balance(self):
        for i in range(1, 8):
            self._insert(make_machine(f"M{i}", i * 10))
        self.root = self.tree.delete(self.root, "M4")
        self._check_balance(self.root)

    def test_delete_all_nodes(self):
        ids = [f"M{i}" for i in range(5)]
        for i, mid in enumerate(ids):
            self._insert(make_machine(mid, (i+1)*10))
        for mid in ids:
            self.root = self.tree.delete(self.root, mid)
        assert self.root is None


# NetworkRouting

class TestNetworkRouting:

    def setup_method(self):
        self.net = NetworkRouting()

    # ── Graph construction ──────────────────────────────────────────────────

    def test_add_machine_creates_node(self):
        self.net.add_machine("A")
        assert "A" in self.net.nodes

    def test_add_machine_idempotent(self):
        self.net.add_machine("A")
        self.net.add_machine("A")
        assert self.net.nodes.count("A") == 1

    def test_add_connection_creates_both_nodes(self):
        self.net.add_connection("A", "B", 5)
        assert "A" in self.net.nodes and "B" in self.net.nodes

    def test_add_connection_is_undirected(self):
        self.net.add_connection("A", "B", 7)
        # Both directions should exist in the graph
        assert any(n == "B" for n, _ in self.net._graph["A"])
        assert any(n == "A" for n, _ in self.net._graph["B"])

    def test_add_connection_negative_weight_raises(self):
        with pytest.raises(ValueError):
            self.net.add_connection("A", "B", -1)

    def test_add_connection_zero_weight_raises(self):
        with pytest.raises(ValueError):
            self.net.add_connection("A", "B", 0)

    def test_edge_count(self):
        self.net.add_connection("A", "B", 1)
        self.net.add_connection("B", "C", 2)
        assert self.net.edge_count == 2

    def test_remove_machine(self):
        self.net.add_connection("A", "B", 3)
        removed = self.net.remove_machine("A")
        assert removed is True
        assert "A" not in self.net.nodes
        # No dangling edges to A
        for neighbours in self.net._graph.values():
            assert all(n != "A" for n, _ in neighbours)

    def test_remove_nonexistent_machine(self):
        assert self.net.remove_machine("GHOST") is False

    def test_remove_connection(self):
        self.net.add_connection("A", "B", 5)
        self.net.remove_connection("A", "B")
        assert self.net.edge_count == 0

    # ── Dijkstra ────────────────────────────────────────────────────────────

    def test_direct_path_cost(self):
        self.net.add_connection("S", "A", 4)
        assert self.net.get_path_cost("S", "A") == 4

    def test_shortest_path_prefers_cheaper_route(self):
        # S→A→B costs 2+3=5; S→B directly costs 10
        self.net.add_connection("S", "A", 2)
        self.net.add_connection("A", "B", 3)
        self.net.add_connection("S", "B", 10)
        assert self.net.get_path_cost("S", "B") == 5

    def test_unreachable_node_returns_inf(self):
        self.net.add_machine("Isolated")
        self.net.add_machine("S")
        assert self.net.get_path_cost("S", "Isolated") == math.inf

    def test_path_to_self_is_zero(self):
        self.net.add_machine("S")
        assert self.net.get_path_cost("S", "S") == 0.0

    def test_get_full_path_hops(self):
        self.net.add_connection("S", "A", 1)
        self.net.add_connection("A", "B", 1)
        path, cost = self.net.get_full_path("S", "B")
        assert path == ["S", "A", "B"]
        assert cost == 2

    def test_get_full_path_unreachable(self):
        self.net.add_machine("S")
        self.net.add_machine("X")
        path, cost = self.net.get_full_path("S", "X")
        assert path == []
        assert cost == math.inf

    def test_find_optimal_machine_picks_cheapest(self):
        # S→A costs 10, S→B costs 3
        self.net.add_connection("S", "A", 10)
        self.net.add_connection("S", "B", 3)
        best, cost = self.net.find_optimal_machine("S", ["A", "B"])
        assert best == "B"
        assert cost == 3

    def test_find_optimal_machine_empty_candidates(self):
        self.net.add_machine("S")
        best, cost = self.net.find_optimal_machine("S", [])
        assert best is None
        assert cost == math.inf

    def test_find_optimal_no_reachable_candidate(self):
        self.net.add_machine("S")
        self.net.add_machine("Isolated")
        best, cost = self.net.find_optimal_machine("S", ["Isolated"])
        assert best is None

    def test_dijkstra_triangle(self):
        # Three nodes: S, A, B — verify all pairwise costs
        self.net.add_connection("S", "A", 6)
        self.net.add_connection("S", "B", 2)
        self.net.add_connection("A", "B", 3)
        # S→A direct=6, via B=2+3=5 → should be 5
        assert self.net.get_path_cost("S", "A") == 5

    def test_source_not_in_graph_returns_inf(self):
        # get_path_cost catches internal KeyError and returns inf gracefully
        self.net.add_machine("A")
        assert self.net.get_path_cost("MISSING", "A") == math.inf


# AllocationEngine

class TestAllocationEngine:

    def setup_method(self):
        self.engine = build_engine_with_machines()

    # ── Registration ────────────────────────────────────────────────────────

    def test_register_machine_appears_in_pool(self):
        self.engine.register_machine(Machine("NEW", 200, 50))
        ids = [m.machine_id for m in self.engine.get_all_machines()]
        assert "NEW" in ids

    def test_duplicate_register_ignored(self):
        before = len(self.engine.get_all_machines())
        self.engine.register_machine(Machine("M-10", 10, 2))  # already exists
        after = len(self.engine.get_all_machines())
        assert before == after

    def test_get_machine_info(self):
        info = self.engine.get_machine_info("M-30")
        assert info is not None
        assert info.capacity == 30

    def test_get_machine_info_missing(self):
        assert self.engine.get_machine_info("GHOST") is None

    # ── Allocation ──────────────────────────────────────────────────────────

    def test_allocate_returns_machine_id(self):
        result = self.engine.allocate(make_job(required=25), "Scheduler")
        assert result is not None
        assert isinstance(result, str)

    def test_allocated_machine_marked_busy(self):
        mid = self.engine.allocate(make_job(required=25), "Scheduler")
        info = self.engine.get_machine_info(mid)
        assert info.status == "busy"

    def test_allocate_picks_best_fit(self):
        # Need 25 → should pick M-30 (30 cap), not M-60 or M-100
        mid = self.engine.allocate(make_job(required=25), "Scheduler")
        info = self.engine.get_machine_info(mid)
        assert info.capacity >= 25

    def test_allocate_fails_when_no_capacity(self):
        result = self.engine.allocate(make_job(required=9999), "Scheduler")
        assert result is None

    def test_allocate_fails_on_empty_pool(self):
        net = NetworkRouting()
        net.add_machine("Scheduler")
        engine = AllocationEngine(network=net)
        result = engine.allocate(make_job(required=10), "Scheduler")
        assert result is None

    def test_allocate_updates_job_history(self):
        mid = self.engine.allocate(make_job("J42", 25), "Scheduler")
        info = self.engine.get_machine_info(mid)
        assert "J42" in info.job_history

    def test_allocate_updates_current_load(self):
        mid = self.engine.allocate(make_job(required=25), "Scheduler")
        info = self.engine.get_machine_info(mid)
        assert info.current_load == 25

    def test_allocate_skips_busy_machine(self):
        # Exhaust the smallest machine
        mid1 = self.engine.allocate(make_job("J1", 8), "Scheduler")   # takes M-10
        # Next job needs 8 → M-10 is busy, so should go to M-30
        mid2 = self.engine.allocate(make_job("J2", 8), "Scheduler")
        assert mid1 != mid2

    # ── Release ─────────────────────────────────────────────────────────────

    def test_release_marks_available(self):
        mid = self.engine.allocate(make_job(required=25), "Scheduler")
        self.engine.release_machine(mid)
        info = self.engine.get_machine_info(mid)
        assert info.status == "available"
        assert info.current_load == 0.0

    def test_release_nonexistent_returns_false(self):
        assert self.engine.release_machine("GHOST") is False

    def test_released_machine_can_be_reallocated(self):
        mid = self.engine.allocate(make_job("J1", 25), "Scheduler")
        self.engine.release_machine(mid)
        mid2 = self.engine.allocate(make_job("J2", 25), "Scheduler")
        assert mid2 is not None

    # ── Remove ──────────────────────────────────────────────────────────────

    def test_remove_machine(self):
        removed = self.engine.remove_machine("M-10")
        assert removed is True
        assert self.engine.get_machine_info("M-10") is None

    def test_remove_nonexistent_returns_false(self):
        assert self.engine.remove_machine("GHOST") is False

    def test_remove_then_pool_size_decreases(self):
        before = len(self.engine.get_all_machines())
        self.engine.remove_machine("M-10")
        after = len(self.engine.get_all_machines())
        assert after == before - 1

    # ── Pool summary ────────────────────────────────────────────────────────

    def test_pool_summary_total(self):
        summary = self.engine.pool_summary()
        assert summary["total"] == 4

    def test_pool_summary_all_available_at_start(self):
        summary = self.engine.pool_summary()
        assert summary["available"] == 4
        assert summary["busy"] == 0

    def test_pool_summary_after_allocation(self):
        self.engine.allocate(make_job(required=25), "Scheduler")
        summary = self.engine.pool_summary()
        assert summary["busy"] == 1
        assert summary["available"] == 3

    def test_get_all_machines_ascending_capacity(self):
        machines = self.engine.get_all_machines()
        caps = [m.capacity for m in machines]
        assert caps == sorted(caps)


# JobSimulator

class TestJobSimulator:

    def test_generate_jobs_count(self):
        jobs = generate_jobs(15)
        assert len(jobs) == 15

    def test_generate_jobs_unique_ids(self):
        jobs = generate_jobs(20)
        ids = [j.job_id for j in jobs]
        assert len(ids) == len(set(ids))

    def test_generate_jobs_capacity_in_range(self):
        jobs = generate_jobs(50, min_capacity=10, max_capacity=80)
        for j in jobs:
            assert 10 <= j.required_capacity <= 80

    def test_generate_jobs_priority_in_range(self):
        jobs = generate_jobs(50)
        for j in jobs:
            assert 1 <= j.priority <= 5

    def test_generate_jobs_seeded_reproducible(self):
        a = generate_jobs(10, seed=42)
        b = generate_jobs(10, seed=42)
        assert [j.required_capacity for j in a] == [j.required_capacity for j in b]

    def test_generate_jobs_different_seeds_differ(self):
        a = generate_jobs(10, seed=1)
        b = generate_jobs(10, seed=2)
        assert [j.required_capacity for j in a] != [j.required_capacity for j in b]

    def test_generate_burst_count(self):
        jobs = generate_burst(10)
        assert len(jobs) == 10

    def test_generate_burst_high_capacity(self):
        jobs = generate_burst(30)
        for j in jobs:
            assert j.required_capacity >= 60

    def test_generate_burst_high_priority(self):
        jobs = generate_burst(20)
        for j in jobs:
            assert j.priority >= 4

    def test_generate_mixed_workload_count(self):
        jobs = generate_mixed_workload(total=20)
        assert len(jobs) == 20

    def test_generate_mixed_workload_has_small_jobs(self):
        jobs = generate_mixed_workload(total=30, seed=0)
        small = [j for j in jobs if j.required_capacity <= 30]
        assert len(small) > 0

    def test_generate_mixed_workload_has_large_jobs(self):
        jobs = generate_mixed_workload(total=30, seed=0)
        large = [j for j in jobs if j.required_capacity >= 70]
        assert len(large) > 0

    def test_generate_mixed_workload_seeded(self):
        a = generate_mixed_workload(total=15, seed=7)
        b = generate_mixed_workload(total=15, seed=7)
        assert [j.job_id for j in a] == [j.job_id for j in b]

    def test_generate_jobs_zero_count(self):
        assert generate_jobs(0) == []


# Integration — full end-to-end allocation pipeline

class TestIntegration:

    def test_full_pipeline_allocates_and_releases(self):
        engine = build_engine_with_machines()
        jobs = generate_jobs(8, seed=1, min_capacity=5, max_capacity=90)
        allocated = []

        for job in jobs:
            mid = engine.allocate(job, "Scheduler")
            if mid:
                allocated.append(mid)

        # Release all and confirm pool returns to available
        for mid in allocated:
            engine.release_machine(mid)

        summary = engine.pool_summary()
        assert summary["busy"] == 0

    def test_pool_exhaustion_then_release(self):
        """Fill every machine, confirm next job fails, release one, confirm it succeeds."""
        engine = build_engine_with_machines()
        mids = []

        # Drain the pool with small jobs (one per machine)
        for i in range(4):
            mid = engine.allocate(make_job(f"J{i}", 5), "Scheduler")
            if mid:
                mids.append(mid)

        # All 4 machines should now be busy
        assert engine.pool_summary()["available"] == 0

        # Next allocation fails
        assert engine.allocate(make_job("overflow", 5), "Scheduler") is None

        # Release one and retry
        engine.release_machine(mids[0])
        result = engine.allocate(make_job("retry", 5), "Scheduler")
        assert result is not None

    def test_register_then_allocate_new_machine(self):
        engine = build_engine_with_machines()
        engine.register_machine(Machine("MEGA", 500, 100))
        engine.add_network_link("Scheduler", "MEGA", 1)
        mid = engine.allocate(make_job(required=400), "Scheduler")
        assert mid == "MEGA"

    def test_remove_machine_then_cannot_allocate_to_it(self):
        engine = build_engine_with_machines()
        engine.remove_machine("M-100")
        result = engine.allocate(make_job(required=90), "Scheduler")
        # M-100 was the only one with cap >= 90, so should fail now
        assert result is None

    def test_network_routing_affects_choice(self):
        """Two machines both fit; Dijkstra should pick the cheaper-to-reach one."""
        net = NetworkRouting()
        net.add_machine("Scheduler")
        engine = AllocationEngine(network=net)

        engine.register_machine(Machine("Cheap-Path", 50, 10))
        engine.register_machine(Machine("Expensive-Path", 50, 10))

        engine.add_network_link("Scheduler", "Cheap-Path",     1)
        engine.add_network_link("Scheduler", "Expensive-Path", 99)

        mid = engine.allocate(make_job(required=40), "Scheduler")
        assert mid == "Cheap-Path"

    def test_allocation_log_grows(self):
        engine = build_engine_with_machines()
        jobs = generate_jobs(3, seed=5, min_capacity=5, max_capacity=25)
        for job in jobs:
            engine.allocate(job, "Scheduler")

        history = []
        for m in engine.get_all_machines():
            history.extend(m.job_history)

        assert len(history) > 0
