class Machine:
    def __init__(self, machine_id, capacity, cost):
        self.machine_id = machine_id
        self.capacity = capacity
        self.cost = cost
        self.status = "available"

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
    def get_height(self, node):
        if not node:
            return 0
        return node.height

    def get_balance(self, node):
        if not node:
            return 0
        return self.get_height(node.left) - self.get_height(node.right)

    def right_rotate(self, y):
        x = y.left
        T2 = x.right
        x.right = y
        y.left = T2
        y.height = 1 + max(self.get_height(y.left), self.get_height(y.right))
        x.height = 1 + max(self.get_height(x.left), self.get_height(x.right))
        return x

    def left_rotate(self, x):
        y = x.right
        T2 = y.left
        y.left = x
        x.right = T2
        x.height = 1 + max(self.get_height(x.left), self.get_height(x.right))
        y.height = 1 + max(self.get_height(y.left), self.get_height(y.right))
        return y

    def insert(self, root, machine):
        if not root:
            return AVLNode(machine)

        if machine.capacity < root.machine.capacity:
            root.left = self.insert(root.left, machine)
        else:
            root.right = self.insert(root.right, machine)

        root.height = 1 + max(self.get_height(root.left), self.get_height(root.right))
        balance = self.get_balance(root)

        # Rotations
        if balance > 1 and machine.capacity < root.left.machine.capacity:
            return self.right_rotate(root)
        if balance < -1 and machine.capacity > root.right.machine.capacity:
            return self.left_rotate(root)
        if balance > 1 and machine.capacity > root.left.machine.capacity:
            root.left = self.left_rotate(root.left)
            return self.right_rotate(root)
        if balance < -1 and machine.capacity < root.right.machine.capacity:
            root.right = self.right_rotate(root.right)
            return self.left_rotate(root)

        return root

    def find_best_fit(self, root, required_capacity):
        best_candidate = None
        current = root
        while current:
            if current.machine.capacity >= required_capacity:
                best_candidate = current.machine
                current = current.left
            else:
                current = current.right
        return best_candidate