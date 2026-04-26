"""
app.py — Flask REST API that exposes the CORAE Engine over HTTP.

This is the backend for the CORAE web dashboard.

Endpoints
---------
GET  /api/status            → engine health + pool summary
GET  /api/machines          → list all machines
POST /api/machines          → register a new machine
DELETE /api/machines/<id>   → remove a machine
POST /api/machines/<id>/release  → free a busy machine
POST /api/allocate          → allocate a job to a machine
GET  /api/network/topology  → return graph edges for visualisation
POST /api/network/link      → add a network edge
POST /api/simulate          → run a batch simulation

Run with:
    python app.py          (development, port 5000)
"""

from __future__ import annotations

import math
import random
import time

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from structures import Machine, Job
from engine import AllocationEngine
from network_routing import NetworkRouting

app = Flask(__name__)
CORS(app)  


# Bootstrap a sample engine instance

def _bootstrap() -> tuple[AllocationEngine, NetworkRouting]:
    network = NetworkRouting()
    network.add_machine("Scheduler")
    engine = AllocationEngine(network=network)

    seed_machines = [
        Machine("Server-Alpha",   capacity=32,  cost=8),
        Machine("Server-Beta",    capacity=64,  cost=18),
        Machine("Server-Gamma",   capacity=16,  cost=4),
        Machine("Server-Delta",   capacity=128, cost=40),
        Machine("Server-Epsilon", capacity=96,  cost=30),
    ]
    for m in seed_machines:
        engine.register_machine(m)

    # Network topology
    links = [
        ("Scheduler",      "Server-Alpha",   10),
        ("Scheduler",      "Server-Beta",     5),
        ("Server-Alpha",   "Server-Gamma",    2),
        ("Server-Beta",    "Server-Delta",    8),
        ("Server-Delta",   "Server-Epsilon",  3),
        ("Server-Alpha",   "Server-Beta",    12),
    ]
    for a, b, w in links:
        engine.add_network_link(a, b, w)

    return engine, network


network = NetworkRouting()
engine, network = _bootstrap()
_job_counter = 0
_allocation_log: list[dict] = []


# Helpers

def _machine_to_dict(m: Machine) -> dict:
    return {
        "id": m.machine_id,
        "capacity": m.capacity,
        "cost": m.cost,
        "status": m.status,
        "current_load": m.current_load,
        "job_history": m.job_history[-10:],  # last 10 only
    }


# Routes

@app.route("/")
def index():
    """Serve the web dashboard directly — avoids file:// CORS issues."""
    here = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(here, "corae_webapp.html")


@app.route("/api/status")
def status():
    summary = engine.pool_summary()
    return jsonify({
        "ok": True,
        "engine": "CORAE v1.0",
        "pool": summary,
        "allocation_count": len(_allocation_log),
    })


@app.route("/api/machines", methods=["GET"])
def list_machines():
    machines = engine.get_all_machines()
    return jsonify([_machine_to_dict(m) for m in machines])


@app.route("/api/machines", methods=["POST"])
def add_machine():
    data = request.get_json(force=True)
    try:
        m = Machine(
            machine_id=str(data["id"]),
            capacity=float(data["capacity"]),
            cost=float(data["cost"]),
        )
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    engine.register_machine(m)

    # Auto-connect to Scheduler with a random weight if not specified
    weight = float(data.get("link_weight", random.randint(1, 20)))
    engine.add_network_link("Scheduler", m.machine_id, weight)

    return jsonify({"ok": True, "machine": _machine_to_dict(m)}), 201


@app.route("/api/machines/<machine_id>", methods=["DELETE"])
def delete_machine(machine_id: str):
    removed = engine.remove_machine(machine_id)
    if not removed:
        return jsonify({"error": f"Machine {machine_id!r} not found"}), 404
    return jsonify({"ok": True, "removed": machine_id})


@app.route("/api/machines/<machine_id>/release", methods=["POST"])
def release_machine(machine_id: str):
    ok = engine.release_machine(machine_id)
    if not ok:
        return jsonify({"error": f"Machine {machine_id!r} not found"}), 404
    return jsonify({"ok": True, "machine_id": machine_id, "status": "available"})


@app.route("/api/allocate", methods=["POST"])
def allocate():
    global _job_counter
    data = request.get_json(force=True)

    _job_counter += 1
    job_id = data.get("job_id") or f"Job-{_job_counter:04d}"

    try:
        required_capacity = float(data["required_capacity"])
        priority = int(data.get("priority", 1))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    job = Job(job_id=job_id, required_capacity=required_capacity, priority=priority)

    start = time.perf_counter()
    machine_id = engine.allocate(job, dispatch_point="Scheduler")
    elapsed_ms = (time.perf_counter() - start) * 1000

    if machine_id:
        path, cost = network.get_full_path("Scheduler", machine_id)
        machine_info = engine.get_machine_info(machine_id)
        entry = {
            "job_id": job_id,
            "required_capacity": required_capacity,
            "priority": priority,
            "machine_id": machine_id,
            "machine_capacity": machine_info.capacity if machine_info else None,
            "machine_cost": machine_info.cost if machine_info else None,
            "network_path": path,
            "network_cost": cost if cost != math.inf else None,
            "elapsed_ms": round(elapsed_ms, 3),
            "timestamp": time.time(),
        }
        _allocation_log.append(entry)
        return jsonify({"ok": True, **entry})
    else:
        return jsonify({"ok": False, "job_id": job_id, "error": "No suitable machine found"}), 200


@app.route("/api/network/topology")
def topology():
    nodes = []
    edges = []

    # Nodes
    for mid in network.nodes:
        m = engine.get_machine_info(mid)
        nodes.append({
            "id": mid,
            "capacity": m.capacity if m else None,
            "cost": m.cost if m else None,
            "status": m.status if m else "scheduler",
        })

    # Edges — reconstruct from adjacency list
    seen = set()
    for node in network.nodes:
        for neighbour, weight in network._graph.get(node, []):
            key = tuple(sorted([node, neighbour]))
            if key not in seen:
                edges.append({"from": node, "to": neighbour, "weight": weight})
                seen.add(key)

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/network/link", methods=["POST"])
def add_link():
    data = request.get_json(force=True)
    try:
        a = str(data["from"])
        b = str(data["to"])
        weight = float(data["weight"])
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    engine.add_network_link(a, b, weight)
    return jsonify({"ok": True, "edge": {"from": a, "to": b, "weight": weight}})


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """Run a batch of random jobs and return results for chart rendering."""
    from job_simulator import generate_mixed_workload

    data = request.get_json(force=True) or {}
    count = min(int(data.get("count", 10)), 50)
    seed = data.get("seed")

    jobs = generate_mixed_workload(total=count, seed=seed)
    results = []

    for job in jobs:
        start = time.perf_counter()
        mid = engine.allocate(job, dispatch_point="Scheduler")
        elapsed_ms = (time.perf_counter() - start) * 1000

        if mid:
            _, cost = network.get_full_path("Scheduler", mid)
            results.append({
                "job_id": job.job_id,
                "capacity": job.required_capacity,
                "priority": job.priority,
                "machine": mid,
                "network_cost": cost if cost != math.inf else None,
                "elapsed_ms": round(elapsed_ms, 4),
                "status": "allocated",
            })
            engine.release_machine(mid)
        else:
            results.append({
                "job_id": job.job_id,
                "capacity": job.required_capacity,
                "priority": job.priority,
                "machine": None,
                "network_cost": None,
                "elapsed_ms": round(elapsed_ms, 4),
                "status": "failed",
            })

    return jsonify({
        "ok": True,
        "count": len(results),
        "allocated": sum(1 for r in results if r["status"] == "allocated"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    })


@app.route("/api/log")
def allocation_log():
    limit = int(request.args.get("limit", 50))
    return jsonify(list(reversed(_allocation_log[-limit:])))


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the engine to its initial seeded state."""
    global engine, network, _job_counter, _allocation_log
    engine, network = _bootstrap()
    _job_counter = 0
    _allocation_log = []
    return jsonify({"ok": True, "message": "Engine reset to initial state."})


# Entry point

if __name__ == "__main__":
    print("🚀  CORAE API server starting on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
