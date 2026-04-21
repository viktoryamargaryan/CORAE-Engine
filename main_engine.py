from network_routing import NetworkRouting
from job_simulator import generate_jobs

def run_allocation_system():
    # 1. Ստեղծում ենք ցանցը
    network = NetworkRouting()
    
    # Ավելացնում ենք մի քանի մեքենա թեստի համար
    for m in ['M1', 'M2', 'M3', 'M4', 'Scheduler']:
        network.add_machine(m)
    
    # Ստեղծում ենք կապեր
    network.add_connection('Scheduler', 'M1', 10)
    network.add_connection('Scheduler', 'M2', 5)
    network.add_connection('M1', 'M3', 2)
    network.add_connection('M2', 'M4', 8)

    # 2. Գեներացնում ենք աշխատանքներ
    jobs = generate_jobs(3)

    print("--- CORAE Allocation System Started ---")

    for job in jobs:
        print(f"\nProcessing {job}...")
        
        # ԺԱՄԱՆԱԿԱՎՈՐ: Ենթադրենք բոլոր մեքենաները համապատասխանում են (մինչև AVL-ի պատրաստ լինելը)
        available_candidates = ['M1', 'M2', 'M3', 'M4']
        
        # 3. Կանչում ենք քո գրած Dijkstra-ն
        best_m, cost = network.find_optimal_machine('Scheduler', available_candidates)
        
        if best_m:
            print(f"Result: Job {job.job_id} allocated to {best_m} with network cost {cost}")
        else:
            print("Result: No suitable machine found.")

if __name__ == "__main__":
    run_allocation_system() 
