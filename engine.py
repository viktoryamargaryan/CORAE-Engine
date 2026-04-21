feature/avl-resource-manager
from structures import AVLTree, Machine

class AllocationEngine:
    def __init__(self):
        self.resource_tree = AVLTree()
        self.root = None
        self.machines_map = {}  # Սա մեր Hash Map-ն է O(1) հասանելիության համար

    def register_machine(self, machine):
        """Ավելացնում է նոր մեքենա համակարգում"""
        self.root = self.resource_tree.insert(self.root, machine)
        self.machines_map[machine.machine_id] = machine

    def allocate(self, job):
        """Գտնում է լավագույն մեքենան տվյալ գործի համար"""
        # 1. Օգտագործում ենք AVL-ը՝ Best-fit գտնելու համար
        best_machine = self.resource_tree.find_best_fit(self.root, job.required_capacity)
        
        if best_machine and best_machine.status == "available":
            # Հետագայում այստեղ Լիլիթը կավելացնի Dijkstra-ն՝ 
            # մի քանի թեկնածուներից ամենաէժանը ընտրելու համար։
            
            best_machine.status = "busy" # Նշում ենք, որ մեքենան զբաղված է
            return best_machine.machine_id
            
    def get_machine_info(self, machine_id):
        """Վերադարձնում է տեղեկություն մեքենայի մասին ըստ ID-ի O(1) ժամանակում"""
        return self.machines_map.get(machine_id, "Մեքենան չի գտնվել")
        
    return None  # Եթե համապատասխան մեքենա չգտնվեց

main
