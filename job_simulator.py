from __future__ import annotations

import random
from typing import Optional

from structures import Job



# Generators

def generate_jobs(
    count: int = 10,
    *,
    seed: Optional[int] = None,
    min_capacity: float = 10.0,
    max_capacity: float = 100.0,
    min_priority: int = 1,
    max_priority: int = 5,
) -> list[Job]:
    """
    Generate *count* jobs with random capacity and priority.

    Parameters
    ----------
    count:         Number of jobs to generate.
    seed:          Optional RNG seed for reproducibility.
    min_capacity:  Minimum required capacity (inclusive).
    max_capacity:  Maximum required capacity (inclusive).
    min_priority:  Minimum priority level (1 = low).
    max_priority:  Maximum priority level (5 = high).
    """
    rng = random.Random(seed)
    jobs: list[Job] = []

    for i in range(1, count + 1):
        cap = round(rng.uniform(min_capacity, max_capacity), 1)
        priority = rng.randint(min_priority, max_priority)
        jobs.append(Job(job_id=f"Job-{i:03d}", required_capacity=cap, priority=priority))

    return jobs


def generate_burst(
    count: int = 20,
    *,
    seed: Optional[int] = None,
) -> list[Job]:
    """
    Generate a burst of high-priority, high-capacity jobs to stress-test
    the allocation engine under peak load.
    """
    rng = random.Random(seed)
    jobs: list[Job] = []

    for i in range(1, count + 1):
        cap = round(rng.uniform(60.0, 100.0), 1)   # heavy jobs
        priority = rng.randint(4, 5)                 # high priority only
        jobs.append(Job(job_id=f"Burst-{i:03d}", required_capacity=cap, priority=priority))

    return jobs


def generate_mixed_workload(
    total: int = 30,
    *,
    seed: Optional[int] = None,
) -> list[Job]:
    """
    Generate a realistic mixed workload:
      70 % small background jobs (capacity 5–30, priority 1–2)
      20 % medium jobs          (capacity 30–70, priority 3)
      10 % large jobs           (capacity 70–100, priority 4–5)

    The returned list is shuffled so arrival order is random.
    """
    rng = random.Random(seed)
    jobs: list[Job] = []
    counter = 1

    small_count = int(total * 0.70)
    medium_count = int(total * 0.20)
    large_count = total - small_count - medium_count

    for _ in range(small_count):
        jobs.append(Job(f"BG-{counter:03d}", round(rng.uniform(5, 30), 1), rng.randint(1, 2)))
        counter += 1

    for _ in range(medium_count):
        jobs.append(Job(f"MD-{counter:03d}", round(rng.uniform(30, 70), 1), 3))
        counter += 1

    for _ in range(large_count):
        jobs.append(Job(f"LG-{counter:03d}", round(rng.uniform(70, 100), 1), rng.randint(4, 5)))
        counter += 1

    rng.shuffle(jobs)
    return jobs


# Demo

if __name__ == "__main__":
    print("=" * 55)
    print(" CORAE — Job Simulator Demo")
    print("=" * 55)

    demo_jobs = generate_jobs(count=8, seed=42)
    print(f"\n{'ID':<12} {'Capacity':>10} {'Priority':>10}")
    print("-" * 34)
    for j in demo_jobs:
        print(f"{j.job_id:<12} {j.required_capacity:>10.1f} {j.priority:>10}")

    print("\n--- Burst workload (5 jobs) ---")
    burst = generate_burst(count=5, seed=7)
    for j in burst:
        print(f"  {j}")

    print("\n--- Mixed workload (10 jobs) ---")
    mixed = generate_mixed_workload(total=10, seed=99)
    for j in mixed:
        print(f"  {j}")
