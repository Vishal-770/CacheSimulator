from typing import Optional, List
from math import log2
from collections import deque
from .constants import WritePolicy, ReplacementAlgorithm, MissType


class InterleavedMemory:
    """Simulates Main Memory with bank interleaving for parallel access simulation."""
    def __init__(self, size_bytes: int, num_banks: int = 4, access_time: int = 100):
        self.size_bytes = size_bytes
        self.num_banks = num_banks
        self.access_time = access_time
        # Effective access time is reduced with interleaving (parallel banks)
        self.interleaved_access_time = access_time // num_banks
        self.banks = [{} for _ in range(num_banks)]
        # Metrics
        self.reads = 0
        self.writes = 0

    def _bank_for(self, address: int) -> int:
        return address % self.num_banks

    def read(self, address: int) -> int:
        self.reads += 1
        bank = self._bank_for(address)
        return self.banks[bank].get(address, address % 256)  # Deterministic default data

    def write(self, address: int, data: int):
        self.writes += 1
        bank = self._bank_for(address)
        self.banks[bank][address] = data


# Alias for backward compatibility
MainMemory = InterleavedMemory


class CacheBlock:
    """Represents a single Cache Line / Block."""
    def __init__(self):
        self.valid_bit: bool = False
        self.tag: Optional[int] = None
        self.dirty_bit: bool = False
        self.data: Optional[int] = None
        self.access_frequency: int = 0

    def __repr__(self):
        return f"Block(V={int(self.valid_bit)} D={int(self.dirty_bit)} Tag={self.tag})"


class CacheSet:
    """Represents a set of Cache Blocks (supports N-Way associativity)."""
    def __init__(self, associativity: int, replacement_algo: ReplacementAlgorithm):
        self.associativity = associativity
        self.blocks: List[CacheBlock] = [CacheBlock() for _ in range(associativity)]
        self.replacement_algo = replacement_algo
        self.usage_queue = deque()  # Used for LRU and FIFO

    def find_block(self, tag: int) -> Optional[CacheBlock]:
        """Returns the block on a cache hit, None on miss."""
        for i, block in enumerate(self.blocks):
            if block.valid_bit and block.tag == tag:
                self._update_usage(i)
                block.access_frequency += 1
                return block
        return None

    def _update_usage(self, block_index: int):
        if self.replacement_algo == ReplacementAlgorithm.LRU:
            if block_index in self.usage_queue:
                self.usage_queue.remove(block_index)
            self.usage_queue.append(block_index)

    def evict_and_replace(self, tag: int, data: int) -> Optional[CacheBlock]:
        """Evicts a block if needed; returns the evicted block if it was dirty."""
        # First look for an invalid (empty) slot
        for i, block in enumerate(self.blocks):
            if not block.valid_bit:
                block.valid_bit = True
                block.tag = tag
                block.data = data
                block.dirty_bit = False
                block.access_frequency = 1
                self.usage_queue.append(i)
                return None

        # All blocks occupied – evict by policy
        evict_index = self._choose_block_to_evict()
        evicted_block = self.blocks[evict_index]

        # Save dirty block for writeback
        dirty_evicted = None
        if evicted_block.dirty_bit:
            dirty_evicted = CacheBlock()
            dirty_evicted.tag = evicted_block.tag
            dirty_evicted.data = evicted_block.data
            dirty_evicted.dirty_bit = True
            dirty_evicted.valid_bit = True

        evicted_block.tag = tag
        evicted_block.data = data
        evicted_block.dirty_bit = False
        evicted_block.access_frequency = 1
        self.usage_queue.append(evict_index)
        return dirty_evicted

    def _choose_block_to_evict(self) -> int:
        if self.replacement_algo in (ReplacementAlgorithm.LRU, ReplacementAlgorithm.FIFO):
            return self.usage_queue.popleft()
        elif self.replacement_algo == ReplacementAlgorithm.LFU:
            min_freq = float('inf')
            min_idx = 0
            for i, block in enumerate(self.blocks):
                if block.access_frequency < min_freq:
                    min_freq = block.access_frequency
                    min_idx = i
            return min_idx
        return 0


class CacheLevel:
    """Represents one level of cache (L1, L2, L3) with configurable parameters."""
    def __init__(
        self,
        name: str,
        size_bytes: int,
        block_size_bytes: int,
        associativity: int,
        access_time: int,
        write_policy: WritePolicy,
        replacement_algo: ReplacementAlgorithm,
        next_level=None,
        prefetch_enabled: bool = False,
        prefetch_degree: int = 1,
    ):
        self.name = name
        self.size_bytes = size_bytes
        self.block_size_bytes = block_size_bytes
        self.associativity = associativity
        self.access_time = access_time
        self.write_policy = write_policy
        self.replacement_algo = replacement_algo
        self.next_level = next_level
        self.prefetch_enabled = prefetch_enabled
        self.prefetch_degree = prefetch_degree

        # Structural calculations
        self.num_blocks = self.size_bytes // self.block_size_bytes
        self.num_sets = self.num_blocks // self.associativity
        self.offset_bits = int(log2(self.block_size_bytes))
        self.index_bits = int(log2(self.num_sets)) if self.num_sets > 1 else 0
        self.sets = [CacheSet(associativity, replacement_algo) for _ in range(self.num_sets)]

        # Stats
        self.hits = 0
        self.misses = 0
        self.writebacks = 0
        self.prefetch_hits = 0
        self.prefetch_loads = 0
        # Miss classification tracking
        self._seen_tags: set = set()
        self._compulsory_misses = 0
        self._conflict_misses = 0
        self._capacity_misses = 0
        # Log of (address, hit_or_miss) for frontend display
        self.access_log: List[dict] = []

        # Energy model (tunable weights)
        self.energy_per_hit = 1       # unit energy
        self.energy_per_miss = 10     # fetching next level

    def parse_address(self, address: int):
        offset = address & ((1 << self.offset_bits) - 1)
        index = (address >> self.offset_bits) & ((1 << self.index_bits) - 1) if self.index_bits else 0
        tag = address >> (self.offset_bits + self.index_bits)
        return tag, index, offset

    def _classify_miss(self, tag: int, index: int):
        if tag not in self._seen_tags:
            self._compulsory_misses += 1
            self._seen_tags.add(tag)
        else:
            # Simplified: if the set is full it's conflict (direct-map) or capacity
            cache_set = self.sets[index]
            full = all(b.valid_bit for b in cache_set.blocks)
            if full and self.associativity == 1:
                self._conflict_misses += 1
            else:
                self._capacity_misses += 1

    def read(self, address: int, _prefetch_call: bool = False) -> int:
        tag, index, offset = self.parse_address(address)
        cache_set = self.sets[index]
        block = cache_set.find_block(tag)

        if block is not None:
            self.hits += 1
            if _prefetch_call:
                self.prefetch_hits += 1
            data = block.data if block.data is not None else address % 256
            if not _prefetch_call:
                self.access_log.append({"address": address, "result": "HIT", "level": self.name})
            return data
        else:
            self.misses += 1
            self._classify_miss(tag, index)
            data = self.next_level.read(address)
            evicted = cache_set.evict_and_replace(tag, data)
            if evicted is not None:
                self.writebacks += 1
                ev_addr = (evicted.tag << (self.offset_bits + self.index_bits)) | (index << self.offset_bits)
                self.next_level.write(ev_addr, evicted.data)

            if not _prefetch_call:
                self.access_log.append({"address": address, "result": "MISS", "level": self.name})

            # Hardware Prefetching: load next N blocks on miss
            if self.prefetch_enabled and not _prefetch_call:
                for i in range(1, self.prefetch_degree + 1):
                    prefetch_addr = address + i * self.block_size_bytes
                    self.prefetch_loads += 1
                    self.read(prefetch_addr, _prefetch_call=True)

            return data

    def write(self, address: int, data: int):
        tag, index, offset = self.parse_address(address)
        cache_set = self.sets[index]
        block = cache_set.find_block(tag)

        if block is not None:
            self.hits += 1
            block.data = data
            if self.write_policy == WritePolicy.WRITE_THROUGH:
                self.next_level.write(address, data)
            else:
                block.dirty_bit = True
            self.access_log.append({"address": address, "result": "WRITE HIT", "level": self.name})
        else:
            self.misses += 1
            self._classify_miss(tag, index)
            # Write-allocate: fetch the block first, then update
            _ = self.next_level.read(address)
            evicted = cache_set.evict_and_replace(tag, data)
            if evicted is not None:
                self.writebacks += 1
                ev_addr = (evicted.tag << (self.offset_bits + self.index_bits)) | (index << self.offset_bits)
                self.next_level.write(ev_addr, evicted.data)
            block = cache_set.find_block(tag)
            if self.write_policy == WritePolicy.WRITE_THROUGH:
                self.next_level.write(address, data)
            elif block:
                block.dirty_bit = True
            self.access_log.append({"address": address, "result": "WRITE MISS", "level": self.name})

    # --- Metrics helpers ---
    def get_hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_miss_rate(self) -> float:
        return 1.0 - self.get_hit_ratio()

    def miss_classifications(self) -> dict:
        return {
            "Compulsory": self._compulsory_misses,
            "Capacity": self._capacity_misses,
            "Conflict": self._conflict_misses,
        }

    def total_energy(self) -> int:
        return self.hits * self.energy_per_hit + self.misses * self.energy_per_miss

    def reset_stats(self):
        self.hits = 0
        self.misses = 0
        self.writebacks = 0
        self.prefetch_hits = 0
        self.prefetch_loads = 0
        self._seen_tags.clear()
        self._compulsory_misses = 0
        self._conflict_misses = 0
        self._capacity_misses = 0
        self.access_log.clear()
        self.sets = [CacheSet(self.associativity, self.replacement_algo) for _ in range(self.num_sets)]
