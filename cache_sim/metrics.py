from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class LevelMetrics:
    """All performance metrics for one cache level."""
    name: str
    hits: int = 0
    misses: int = 0
    writebacks: int = 0
    prefetch_hits: int = 0
    prefetch_loads: int = 0
    access_time: int = 1
    energy_per_hit: int = 1
    energy_per_miss: int = 10

    @property
    def total_accesses(self) -> int:
        return self.hits + self.misses

    @property
    def hit_ratio(self) -> float:
        return self.hits / self.total_accesses if self.total_accesses else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_ratio

    @property
    def total_energy(self) -> int:
        return self.hits * self.energy_per_hit + self.misses * self.energy_per_miss


@dataclass
class SimulationReport:
    """Complete analysis report for a simulation run."""
    workload_name: str
    addresses: List[int]
    levels: List[LevelMetrics] = field(default_factory=list)
    miss_classifications: Dict[str, int] = field(default_factory=dict)
    memory_reads: int = 0
    memory_writes: int = 0
    
    # Computed later
    amat: float = 0.0
    total_cycles: int = 0
    total_energy: int = 0

    def compute(self, memory_access_time: int):
        """Calculate AMAT and total energy from in-place metrics."""
        # AMAT = HitTime_L1 + MissRate_L1 * (HitTime_L2 + MissRate_L2 * MemoryTime)
        if not self.levels:
            return
        
        amat = memory_access_time
        for lm in reversed(self.levels):
            amat = lm.access_time + lm.miss_rate * amat
        self.amat = round(amat, 4)

        self.total_cycles = sum(
            lm.hits * lm.access_time + lm.misses * (lm.access_time + memory_access_time)
            for lm in self.levels
        )
        self.total_energy = sum(lm.total_energy for lm in self.levels)
        # Memory energy (much more expensive)
        self.total_energy += (self.memory_reads + self.memory_writes) * 50

    def to_dict(self) -> dict:
        return {
            "Workload": self.workload_name,
            "Total Addresses": len(self.addresses),
            "AMAT (cycles)": self.amat,
            "Total Cycles": self.total_cycles,
            "Total Energy (units)": self.total_energy,
            **{f"{lm.name} Hits": lm.hits for lm in self.levels},
            **{f"{lm.name} Misses": lm.misses for lm in self.levels},
            **{f"{lm.name} Hit Ratio": f"{lm.hit_ratio * 100:.2f}%" for lm in self.levels},
            **{f"{lm.name} Writebacks": lm.writebacks for lm in self.levels},
            "Compulsory Misses": self.miss_classifications.get("Compulsory", 0),
            "Capacity Misses": self.miss_classifications.get("Capacity", 0),
            "Conflict Misses": self.miss_classifications.get("Conflict", 0),
            "RAM Reads": self.memory_reads,
            "RAM Writes": self.memory_writes,
        }
