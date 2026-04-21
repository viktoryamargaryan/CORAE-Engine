class Machine:
    def __init__(self, machine_id, capacity, cost):
        self.machine_id = machine_id
        self.capacity = capacity  # CPU կամ RAM
        self.cost = cost          # Գինը մեկ ժամվա համար
        self.status = "available" # available, busy, offline

class Job:
    def __init__(self, job_id, required_capacity):
        self.job_id = job_id
        self.required_capacity = required_capacity

class AVLNode:
    def __init__(self, machine):
        self.machine = machine
        self.left = None
        self.right = None
        self.height = 1

class AVLTree:
    def insert(self, root, machine):
        # Այստեղ կգրես AVL-ի ստանդարտ ինսերտը
        pass

    def find_best_fit(self, root, required_capacity):
        # Սա քո ամենակարևոր ֆունկցիան է լինելու
        pass
