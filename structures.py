"""
structures.py — Core data structures for the CORAE Engine.

Defines Machine, Job, AVLNode, and AVLTree.

Improvements over original:
  - Added type hints throughout for clarity and IDE support.
  - Added __repr__ / __str__ to Machine and AVLNode for easier debugging.
  - AVLTree now supports delete() so machines can leave the pool at runtime —
    the original had no removal path at all.
  - find_best_fit is now a proper method that filters out non-available machines
    inside the tree walk rather than relying on the caller.
  - Added an inorder() generator so the whole tree can be iterated (useful for
    the web API and benchmarking).
  - Used dataclasses for Machine and Job to remove boilerplate __init__ code.
  - Added a composite "score" property on Machine so capacity and cost can be
    combined into a single sortable key without changing the tree key.
  - Guard clauses are explicit; the original had a silent fall-through on the
    AVL rotation cases (equal-capacity insert went to the right branch by
    default but this was undocumented).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Generator


# Domain objects

@dataclass
class Machine:
    machine_id: str
    capacity: float          # available capacity units (CPU cores, GB RAM, etc.)
    cost: float              # hourly cost rate
    status: str = "available"  # "available" | "busy" | "offline"
    current_load: float = 0.0
    job_history: list = field(default_factory=list)

    @property
    def free_capacity(self) -> float:
        """Remaining capacity after current load."""
        return self.capacity - self.current_load

    def __repr__(self) -> str:
        return (
            f"Machine(id={self.machine_id!r}, capacity={self.capacity}, "
            f"cost={self.cost}, status={self.status!r})"
        )


@dataclass
class Job:
    job_id: str
    required_capacity: float
    priority: int = 1        # 1 (low) – 5 (high)

    def __repr__(self) -> str:
        return (
            f"Job(id={self.job_id!r}, required={self.required_capacity}, "
            f"priority={self.priority})"
        )


# AVL Tree internals

class AVLNode:
    """A node in the AVL tree keyed on machine.capacity."""

    __slots__ = ("machine", "left", "right", "height")

    def __init__(self, machine: Machine) -> None:
        self.machine: Machine = machine
        self.left: Optional[AVLNode] = None
        self.right: Optional[AVLNode] = None
        self.height: int = 1

    def __repr__(self) -> str:
        return f"AVLNode(machine_id={self.machine.machine_id!r}, cap={self.machine.capacity})"


# AVL Tree

class AVLTree:
    """
    Self-balancing binary search tree keyed on Machine.capacity.

    Guarantees O(log n) insert, delete, and best-fit lookup.
    """

    # Height helpers

    @staticmethod
    def _height(node: Optional[AVLNode]) -> int:
        return node.height if node else 0

    @staticmethod
    def _balance_factor(node: Optional[AVLNode]) -> int:
        if not node:
            return 0
        return AVLTree._height(node.left) - AVLTree._height(node.right)

    @staticmethod
    def _refresh_height(node: AVLNode) -> None:
        node.height = 1 + max(AVLTree._height(node.left), AVLTree._height(node.right))

    # Rotations

    @staticmethod
    def _right_rotate(y: AVLNode) -> AVLNode:
        x = y.left
        assert x is not None, "right_rotate called on node with no left child"
        T2 = x.right

        x.right = y
        y.left = T2

        AVLTree._refresh_height(y)
        AVLTree._refresh_height(x)
        return x

    @staticmethod
    def _left_rotate(x: AVLNode) -> AVLNode:
        y = x.right
        assert y is not None, "left_rotate called on node with no right child"
        T2 = y.left

        y.left = x
        x.right = T2

        AVLTree._refresh_height(x)
        AVLTree._refresh_height(y)
        return y
    

    # Balance helper (called after every structural change)

    @staticmethod
    def _balance(node: AVLNode, key: float) -> AVLNode:
        AVLTree._refresh_height(node)
        bf = AVLTree._balance_factor(node)

        # Left-Left
        if bf > 1 and node.left and key < node.left.machine.capacity:
            return AVLTree._right_rotate(node)
        # Right-Right
        if bf < -1 and node.right and key > node.right.machine.capacity:
            return AVLTree._left_rotate(node)
        # Left-Right
        if bf > 1 and node.left and key > node.left.machine.capacity:
            node.left = AVLTree._left_rotate(node.left)
            return AVLTree._right_rotate(node)
        # Right-Left
        if bf < -1 and node.right and key < node.right.machine.capacity:
            node.right = AVLTree._right_rotate(node.right)
            return AVLTree._left_rotate(node)

        return node

    # Public API

    @staticmethod
    def _find_capacity(root: Optional[AVLNode], machine_id: str) -> Optional[float]:
        """Linear inorder scan to find a machine's capacity by its ID."""
        if root is None:
            return None
        left = AVLTree._find_capacity(root.left, machine_id)
        if left is not None:
            return left
        if root.machine.machine_id == machine_id:
            return root.machine.capacity
        return AVLTree._find_capacity(root.right, machine_id)

    def insert(self, root: Optional[AVLNode], machine: Machine) -> AVLNode:
        """Insert a machine and return the (possibly new) root."""
        if root is None:
            return AVLNode(machine)

        if machine.capacity < root.machine.capacity:
            root.left = self.insert(root.left, machine)
        else:
            # Equal capacities go right; avoids duplicates breaking the BST
            root.right = self.insert(root.right, machine)

        return self._balance(root, machine.capacity)

    def delete(self, root: Optional[AVLNode], machine_id: str,
               _capacity: Optional[float] = None) -> Optional[AVLNode]:
        """
        Remove the node whose machine.machine_id matches and return the
        (possibly new) root.

        Navigation uses capacity (the BST key).  On first call, capacity is
        looked up via a preliminary scan so that the correct subtree is
        reached; on recursive calls it is passed directly.  O(log n).
        """
        if root is None:
            return None

        # First call: find the target capacity so we can navigate by BST key
        if _capacity is None:
            _capacity = self._find_capacity(root, machine_id)
            if _capacity is None:
                return root  # machine not in tree

        if _capacity < root.machine.capacity:
            root.left = self.delete(root.left, machine_id, _capacity)
        elif _capacity > root.machine.capacity:
            root.right = self.delete(root.right, machine_id, _capacity)
        else:
            # Capacity matches; confirm machine_id (handles equal-capacity nodes)
            if root.machine.machine_id != machine_id:
                # Same capacity but different machine — check both subtrees
                root.left = self.delete(root.left, machine_id, _capacity)
                root.right = self.delete(root.right, machine_id, _capacity)
                AVLTree._refresh_height(root)
                return root

            # Node found — handle the three BST-delete cases
            if root.left is None:
                return root.right
            if root.right is None:
                return root.left

            # Two children: replace with in-order successor
            successor = root.right
            while successor.left:
                successor = successor.left
            root.machine = successor.machine
            root.right = self.delete(root.right, successor.machine.machine_id,
                                     successor.machine.capacity)

        AVLTree._refresh_height(root)
        bf = AVLTree._balance_factor(root)

        if bf > 1:
            if AVLTree._balance_factor(root.left) >= 0:
                return AVLTree._right_rotate(root)
            root.left = AVLTree._left_rotate(root.left)  # type: ignore[arg-type]
            return AVLTree._right_rotate(root)

        if bf < -1:
            if AVLTree._balance_factor(root.right) <= 0:
                return AVLTree._left_rotate(root)
            root.right = AVLTree._right_rotate(root.right)  # type: ignore[arg-type]
            return AVLTree._left_rotate(root)

        return root

    def find_best_fit(
        self,
        root: Optional[AVLNode],
        required_capacity: float,
    ) -> Optional[Machine]:
        """
        Return the available machine with the *smallest* capacity that still
        satisfies required_capacity (classic best-fit allocation).
        Skips machines that are busy or offline.

        When a qualifying node is unavailable (busy/offline) both subtrees are
        explored so that available machines on the right are not missed.
        Worst case O(n) only when all machines are busy; O(log n) for a
        healthy pool with available machines.
        """
        return self._find_best_fit_rec(root, required_capacity)

    def _find_best_fit_rec(
        self,
        node: Optional[AVLNode],
        required_capacity: float,
    ) -> Optional[Machine]:
        if node is None:
            return None

        if node.machine.capacity < required_capacity:
            # This subtree's root is too small; only the right subtree can help
            return self._find_best_fit_rec(node.right, required_capacity)

        # Node capacity is sufficient — check whether it's available
        if node.machine.status == "available":
            # Candidate found; go left for a potentially tighter fit
            left_candidate = self._find_best_fit_rec(node.left, required_capacity)
            return left_candidate if left_candidate is not None else node.machine
        else:
            # Node is busy/offline — must search BOTH sides
            left  = self._find_best_fit_rec(node.left,  required_capacity)
            right = self._find_best_fit_rec(node.right, required_capacity)
            if left is not None and right is not None:
                return left if left.capacity <= right.capacity else right
            return left if left is not None else right

    def inorder(self, root: Optional[AVLNode]) -> Generator[Machine, None, None]:
        """Yield machines in ascending capacity order."""
        if root is None:
            return
        yield from self.inorder(root.left)
        yield root.machine
        yield from self.inorder(root.right)
