import heapq

class NetworkRouting:
    def __init__(self):
        """
        Գրաֆի կառուցվածքը պահում ենք Adjacency List-ի միջոցով:
        self.graph = { 'NodeA': [('NodeB', 10), ('NodeC', 5)] }
        """
        self.graph = {}

    def add_machine(self, machine_id):
        """Ավելացնում է նոր մեքենա (հանգույց) գրաֆում:"""
        if machine_id not in self.graph:
            self.graph[machine_id] = []

    def add_connection(self, node1, node2, weight):
        """Ավելացնում է կապ երկու մեքենաների միջև (weight-ը latency-ն է կամ cost-ը):"""
        if node1 in self.graph and node2 in self.graph:
            self.graph[node1].append((node2, weight))
            self.graph[node2].append((node1, weight))
        else:
            print(f"Error: One or both nodes ({node1}, {node2}) not found.")

    def find_optimal_machine(self, start_point, candidates):
        """
        Իրականացնում է Dijkstra ալգորիթմը:
        start_point: որտեղից է գալիս Job-ը (օրինակ՝ 'Scheduler')
        candidates: AVL ծառի կողմից տրված հարմար մեքենաների ցանկը
        """
        if not candidates:
            return None, float('inf')

        # Հեռավորությունների բառարան, սկզբում բոլորը անվերջություն են
        distances = {node: float('inf') for node in self.graph}
        distances[start_point] = 0
        
        # Priority Queue (min-heap) պահում է (distance, node)
        priority_queue = [(0, start_point)]

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            # Եթե գտած ճանապարհն ավելի երկար է, քան արդեն ունեցածը, բաց թողնել
            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in self.graph[current_node]:
                distance = current_distance + weight

                # Եթե գտել ենք ավելի կարճ ճանապարհ
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    heapq.heappush(priority_queue, (distance, neighbor))

        # Թեկնածուներից ընտրում ենք այն մեկը, որի հեռավորությունը ամենափոքրն է
        best_machine = None
        min_dist = float('inf')

        for machine in candidates:
            if machine in distances and distances[machine] < min_dist:
                min_dist = distances[machine]
                best_machine = machine

        return best_machine, min_dist

# --- Թեստավորման հատված ---
if __name__ == "__main__":
    routing = NetworkRouting()
    
    # Ավելացնում ենք մեքենաներ
    nodes = ['Scheduler', 'M1', 'M2', 'M3', 'M4']
    for n in nodes:
        routing.add_machine(n)
        
    # Ստեղծում ենք ցանցային կապեր (կամայական weight-երով)
    routing.add_connection('Scheduler', 'M1', 10)
    routing.add_connection('Scheduler', 'M2', 20)
    routing.add_connection('M1', 'M3', 5)
    routing.add_connection('M2', 'M3', 2)
    routing.add_connection('M3', 'M4', 1)

    # Ենթադրենք AVL ծառը մեզ տվել է M2 և M4 մեքենաները որպես հարմար տարբերակներ
    potential_candidates = ['M2', 'M4']
    
    target, cost = routing.find_optimal_machine('Scheduler', potential_candidates)
    print(f"Ամենաօպտիմալ մեքենան: {target}, Ճանապարհի արժեքը: {cost}") 
