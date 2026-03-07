import random
from typing import List


class WorkloadGenerator:
    """
    Generates realistic memory access patterns to simulate different workloads.
    
    Three patterns:
      - Sequential: A[0], A[1], A[2], ... (high spatial locality)
      - Loop: repeated iteration over same array (high temporal locality)
      - Random: random addresses (worst cache performance)
    """

    def __init__(self, base_address: int = 0, block_size: int = 16, seed: int = 42):
        self.base_address = base_address
        self.block_size = block_size
        random.seed(seed)

    def sequential(self, num_accesses: int) -> List[int]:
        """
        Sequential scan: address increases by block_size each time.
        Models: array traversal, video decoding, file I/O buffer reads.
        """
        return [self.base_address + i * self.block_size for i in range(num_accesses)]

    def loop(self, array_size: int, iterations: int) -> List[int]:
        """
        Repeated loop over a fixed-size array.
        Models: matrix row operations, physics engine per-frame updates.
        """
        addresses = []
        for _ in range(iterations):
            for i in range(array_size):
                addresses.append(self.base_address + i * self.block_size)
        return addresses

    def random_access(self, num_accesses: int, address_space: int = 4096) -> List[int]:
        """
        Random addresses within a given address space.
        Models: hash table lookups, pointer chasing, tree traversal.
        """
        return [
            self.base_address + random.randint(0, address_space - 1) * self.block_size
            for _ in range(num_accesses)
        ]

    def strided(self, num_accesses: int, stride: int = 4) -> List[int]:
        """
        Stride access: skip `stride` blocks between accesses.
        Models: column-major matrix access, audio sample picking.
        """
        return [self.base_address + i * self.block_size * stride for i in range(num_accesses)]

    def generate(self, pattern: str, **kwargs) -> List[int]:
        """Dispatch method for the frontend."""
        if pattern == "Sequential":
            return self.sequential(kwargs.get("num_accesses", 64))
        elif pattern == "Loop":
            return self.loop(kwargs.get("array_size", 8), kwargs.get("iterations", 8))
        elif pattern == "Random":
            return self.random_access(kwargs.get("num_accesses", 64), kwargs.get("address_space", 256))
        elif pattern == "Strided":
            return self.strided(kwargs.get("num_accesses", 64), kwargs.get("stride", 4))
        else:
            raise ValueError(f"Unknown workload pattern: {pattern}")
