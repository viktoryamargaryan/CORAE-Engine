from structures import Machine, Job
from engine import AllocationEngine

def run_test():
    # 1. Ստեղծում ենք CORAE շարժիչը
    corae = AllocationEngine()

    # 2. Ստեղծում ենք մի քանի մեքենաներ (ID, Capacity, Cost)
    # Պատկերացրու սրանք սերվերներ են տարբեր հզորության
    m1 = Machine("Server-A", 10, 5)
    m2 = Machine("Server-B", 50, 20)
    m3 = Machine("Server-C", 25, 12)
    m4 = Machine("Server-D", 100, 45)

    # 3. Գրանցում ենք մեքենաները համակարգում
    print("--- Ռեսուրսների գրանցում ---")
    for m in [m1, m2, m3, m4]:
        corae.register_machine(m)
        print(f"Մեքենա {m.machine_id}-ն ավելացվեց (Հզորություն: {m.capacity})")

    # 4. Ստեղծում ենք գործեր (Jobs), որոնք պետք է բաշխվեն
    print("\n--- Գործերի բաշխում ---")
    jobs = [
        Job("Job-1", 20),  # Սրան ամենամոտը Server-C-ն է (25)
        Job("Job-2", 8),   # Սրան ամենամոտը Server-A-ն է (10)
        Job("Job-3", 80),  # Սրան ամենամոտը Server-D-ն է (100)
    ]

    for j in jobs:
        allocated_id = corae.allocate(j)
        if allocated_id:
            print(f"✅ {j.job_id} ({j.required_capacity}GB) -> Ուղարկվեց սերվեր: {allocated_id}")
        else:
            print(f"❌ {j.job_id} ({j.required_capacity}GB) -> Հարմար մեքենա չգտնվեց")

if __name__ == "__main__":
    run_test()
