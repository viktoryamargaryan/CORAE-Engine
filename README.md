# CORAE — Cost-Optimized Resource Allocation Engine

> A university Data Structures project built with Python, implementing AVL Trees, Hash Maps, Dijkstra's Algorithm, and a live web dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

---

## What is CORAE?

CORAE is a **resource allocation engine** — the kind of system that sits inside a data center and decides which server should run each incoming job.

Every time a job arrives (a video render, a database query, a computation task), CORAE answers the question: *"which machine should handle this, and how do we get the job there as cheaply as possible?"*

It combines three data structures into a single dispatch pipeline:

- An **AVL Tree** to find the right server by capacity in O(log n)
- A **Hash Map** to check server status instantly in O(1)
- A **weighted graph + Dijkstra's algorithm** to pick the cheapest server to reach

The result is displayed through a live web dashboard where you can register servers, dispatch jobs, watch allocations happen in real time, and visualise the network routing graph.

This is a university project built for a Data Structures course. We are open to suggestions, feedback, and contributions.

---

## Authors

| Name | GitHub |
|------|--------|
| Viktorya Margaryan | [@viktoryamargaryan](https://github.com/viktoryamargaryan) |
| Lilit Zalinyan | [@Lilit862](https://github.com/Lilit862) |

---

## Project Structure

```
CORAE-Engine/
├── structures.py         # AVL Tree, Machine & Job dataclasses
├── engine.py             # Core allocation engine (AVL + HashMap + Dijkstra)
├── network_routing.py    # Weighted graph + Dijkstra's algorithm
├── job_simulator.py      # Random job generator for testing
├── main_engine.py        # CLI demo + benchmark runner
├── app.py                # Flask REST API (backend)
├── corae_webapp.html     # Web dashboard (frontend, single file)
├── test_corae.py         # Pytest test suite (93 tests)
└── requirements.txt      # Python dependencies
```

---

## Data Structures — The Core of the Project

This section explains every data structure used, why it was chosen, and what problem it solves.

---

### 1. AVL Tree — `structures.py`

**What it is:** A self-balancing binary search tree where every node stores a `Machine` object, sorted by the machine's capacity.

**The problem it solves:** When a job arrives needing, say, 40 capacity units, we need to find the server with the smallest capacity that is still ≥ 40 (this is called *best-fit allocation*). A naive approach would check every server one by one — O(n). With 1,000 servers, that's 1,000 checks per job.

**How it works:** A binary search tree keeps values sorted so that at each node, everything to the left is smaller and everything to the right is larger. To find a best fit, we walk the tree: if a node's capacity is sufficient, we record it as a candidate and go left to look for a tighter fit. If it's too small, we go right to look for something larger. Because the tree is balanced, the depth is always ≈ log₂(n).

The "AVL" part means the tree **rebalances itself after every insert or delete** using rotations. Without this, inserting machines in sorted capacity order would create a long chain (essentially a linked list), destroying the O(log n) property. AVL rotations ensure the tree height stays ≤ 1.44 × log₂(n) at all times.

**Why best-fit matters:** If a job needs 40 units and you have servers at 42, 60, and 120, picking the 42-unit server leaves the 60 and 120 servers free for larger jobs. Picking 120 wastes 80 units. Best-fit minimises fragmentation across the pool.

| Operation | Complexity |
|-----------|-----------|
| Insert machine | O(log n) |
| Delete machine | O(log n) |
| Find best-fit | O(log n) |
| Inorder traversal | O(n) |

---

### 2. Hash Map — `engine.py`

**What it is:** Python's built-in `dict`, used as a hash map keyed by `machine_id` (a string like `"Server-Alpha"`).

**The problem it solves:** After the AVL tree returns a candidate machine, we need to immediately check its current status — is it available, busy, or offline? We also need to update its load, record which job it received, and know its cost. Re-traversing the tree for this would be wasteful.

**How it works:** A hash map converts the machine ID string into a numeric index via a hash function. That index points directly to a memory slot containing the full `Machine` object. No loops, no comparisons — one mathematical operation.

**Why O(1) matters here:** Every single job allocation involves at least one hash map lookup. At 10,000 allocations per second (plausible in a real data centre), even a tiny per-lookup overhead compounds quickly. O(1) means the lookup cost is the same whether the pool has 5 machines or 50,000.

| Operation | Complexity |
|-----------|-----------|
| Lookup by machine ID | O(1) |
| Insert machine | O(1) |
| Delete machine | O(1) |
| Update status/load | O(1) |

---

### 3. Weighted Graph + Dijkstra's Algorithm — `network_routing.py`

**What it is:** An undirected graph where nodes are machines (and the scheduler), and edges carry a numeric weight representing network cost or latency between them. Dijkstra's algorithm finds the shortest (cheapest) path from the scheduler to any machine.

**The problem it solves:** When multiple machines all have enough capacity for a job, which one do you pick? The cheapest to reach. Sending every job to the most powerful server wastes money if a cheaper, nearby server would do just as well.

**How Dijkstra works:**
1. Start at the Scheduler node with cost 0.
2. Look at all direct neighbours and record their costs.
3. Pick the cheapest unvisited node (using a **min-heap** priority queue).
4. From that node, update neighbour costs if going through it is cheaper than previously known.
5. Repeat until every node has been visited.

The min-heap ensures we always expand the currently cheapest known path first, which mathematically guarantees the algorithm finds the **globally optimal** route — not just a locally good one.

**Why a min-heap matters:** Without it, finding the cheapest unvisited node at each step would be O(V), making the total complexity O(V²). With a binary min-heap, each step is O(log V), giving a total of **O((V + E) log V)** — far better for dense networks.

**Provably optimal:** For graphs with non-negative edge weights (which all real network costs are), Dijkstra's algorithm is proven to always find the shortest path. There is no case where it returns a suboptimal result.

| Operation | Complexity |
|-----------|-----------|
| Add node / edge | O(1) / O(1) |
| Dijkstra (full graph) | O((V + E) log V) |
| Find cheapest candidate | O((V + E) log V) |
| Reconstruct full path | O(V) |

---

### Why This Combination?

Each structure solves a different bottleneck:

```
Job arrives
     │
     ▼
AVL Tree ──────────────── "Which servers have enough capacity?"   O(log n)
     │
     ▼
Hash Map ──────────────── "Are those servers actually available?" O(1)
     │
     ▼
Dijkstra on Graph ──────── "Which one is cheapest to reach?"     O((V+E) log V)
     │
     ▼
Winner marked busy, job dispatched
```

A system using only linear scans would be O(n) at every step. CORAE's combined approach means the decision time barely changes as the pool grows from 10 servers to 10,000.

---

## Web Dashboard

The project includes a single-page web dashboard served by the Flask backend.

**Sidebar** — Live pool monitor that refreshes every 3 seconds. Shows total, available, and busy machine counts. Each machine card has a colour-coded status stripe (green = available, orange = busy) and a capacity bar showing current load.

**Allocate Job tab** — Enter required capacity and priority, click Allocate. The result box shows which machine was chosen, the full Dijkstra routing path, network cost, and how long the decision took in milliseconds.

**Add Machine tab** — Register a new server into the live pool or remove an existing one without restarting.

**Network tab** — A canvas that draws the Dijkstra graph. Nodes are colour-coded by status. You can add custom network links between any two machines.

**Simulate tab** — Dispatch up to 50 random jobs at once. Results are shown as a bar chart — each bar is a job, its length is the capacity it needed, and the label shows which machine it landed on.

**Allocation Log tab** — Full history table of every dispatched job with machine, path, network cost, and decision latency.

---

## Quick Start

### Prerequisites
- Python 3.10 or newer
- pip

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/viktoryamargaryan/CORAE-Engine.git
cd CORAE-Engine

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the backend
python app.py
```

### Open the dashboard

Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

> ⚠️ Do **not** open `corae_webapp.html` by double-clicking it. Always use the URL above so the page and API share the same origin.

### Run tests

```bash
pytest test_corae.py -v
```

### Run CLI demo

```bash
python main_engine.py
```

### `requirements.txt`

```
flask>=3.0
flask-cors>=4.0
pytest>=8.0
```

---

## API Endpoints

The Flask backend exposes a REST API at `http://127.0.0.1:5000/api`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/status` | Engine health + pool summary |
| GET | `/api/machines` | List all machines |
| POST | `/api/machines` | Register a new machine |
| DELETE | `/api/machines/:id` | Remove a machine |
| POST | `/api/machines/:id/release` | Mark a machine available |
| POST | `/api/allocate` | Dispatch a job |
| GET | `/api/network/topology` | Graph nodes + edges |
| POST | `/api/network/link` | Add a network edge |
| POST | `/api/simulate` | Batch simulation |
| GET | `/api/log` | Recent allocation history |
| POST | `/api/reset` | Reset to initial state |

---

## Notes

This is a **university project** submitted as part of a Data Structures course. The focus is on demonstrating correct implementation and practical application of AVL Trees, Hash Maps, and Dijkstra's Algorithm — not production-scale engineering.

We are **open to suggestions, questions, and pull requests**. If you spot something that could be improved or explained better, feel free to open an issue.

---

## License

[MIT](LICENSE)
