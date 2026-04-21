import random

class Job:
    def __init__(self, job_id, required_capacity, priority):
        self.job_id = job_id
        self.required_capacity = required_capacity
        self.priority = priority

    def __repr__(self):
        return f"[Job {self.job_id}: Capacity={self.required_capacity}, Priority={self.priority}]"

def generate_jobs(count=10):
    """Գեներացնում է պատահական աշխատանքների ցուցակ:"""
    jobs = []
    for i in range(1, count + 1):
        # Պատահական հզորություն 10-ից 100-ի միջակայքում
        cap = random.randint(10, 100)
        # Պատահական պրիորիտետ 1-ից 5-ի միջակայքում
        priority = random.randint(1, 5)
        jobs.append(Job(i, cap, priority))
    return jobs

if __name__ == "__main__":
    # Թեստավորենք սիմուլյատորը
    test_jobs = generate_jobs(5)
    print("Գեներացված աշխատանքների ցուցակը:")
    for j in test_jobs:
        print(j) 
