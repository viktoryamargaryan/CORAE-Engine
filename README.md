## Project Title: Cost-Optimized Resource Allocation Engine (CORAE)

### Project Overview
Designed and implemented a resource management system capable of matching incoming jobs to the most suitable available machine based on capacity, cost, and network proximity. The system acts as the dispatch layer of a larger job execution pipeline — receiving a scheduled job from an upstream scheduler (HPJS) and determining the optimal machine to execute it on. By combining a self-balancing tree for capacity-ordered resource lookup with a graph-based network model, CORAE guarantees efficient, cost-aware placement decisions even as the resource pool scales.

---

### Core Technical Components

Capacity-Ordered Resource Lookup (AVL Tree)
Implements a self-balancing AVL Tree where each node represents a machine, keyed by its *available capacity* (CPU, memory, or a weighted composite score). This guarantees O(log n) insertion, deletion, and lookup when finding the best-fit machine for a job's resource requirements. When a machine's load changes after job assignment, the node is updated and the tree rebalances automatically — ensuring the structure never degrades to linear search.

Network-Aware Routing (Weighted Graph + Dijkstra's Algorithm)
Models the resource infrastructure as a weighted undirected graph where nodes are machines and edge weights represent network cost or latency between them. When multiple machines satisfy a job's capacity requirements, Dijkstra's algorithm finds the lowest-cost path from the scheduler's dispatch point to the candidate machine. This ensures the system does not just find *a* valid machine, but the *cheapest to reach* one.

Constant-Time Resource State Tracking (Hash Map)
Maintains a Hash Map keyed by machine ID for O(1) access to live resource metadata: current load, status (available / busy / offline), hourly cost rate, and job history. This allows the allocation engine to instantly validate or invalidate a candidate machine returned by the AVL Tree without re-traversing the structure.

---

### Key Features

Best-Fit Allocation Strategy
Rather than assigning jobs to the first available machine (first-fit), CORAE queries the AVL Tree for the machine whose available capacity most closely matches the job's requirements — minimizing wasted resources across the pool.

Dynamic Resource Registration
Machines can join or leave the resource pool at runtime. Additions trigger an AVL insertion with automatic rebalancing; removals trigger deletion with rebalancing and a Hash Map entry update — keeping both structures consistent at all times.

Cost vs. Capacity Trade-off Scoring
Each allocation decision computes a weighted score combining available capacity and network cost. This prevents the system from always selecting the most powerful machine when a cheaper, closer one is sufficient — directly minimizing operational cost.

Benchmarking Module
Includes a comparison mode that runs the same allocation workload using a linear scan baseline alongside the AVL + Graph approach, measuring and plotting the difference in decision time as the resource pool grows from 10 to 500 machines.

---

### Integration with HPJS

CORAE is designed as the downstream dispatch layer of the High-Performance Job Scheduler. The interface between the two systems is a single function call:

allocate(job_id, required_capacity, priority) → machine_id
HPJS extracts the next job from its heap and calls CORAE's allocate function. CORAE queries the AVL Tree for candidate machines, validates them via the Hash Map, runs Dijkstra on the resource graph to select the cheapest reachable option, and returns a machine ID. Neither system needs to know the internals of the other.

---

### Complexity Summary

| Operation | Structure | Complexity |
|---|---|---|
| Find best-fit machine | AVL Tree | O(log n) |
| Validate machine state | Hash Map | O(1) |
| Find cheapest route | Dijkstra on graph | O((V + E) log V) |
| Register / remove machine | AVL Tree + Hash Map | O(log n) |

