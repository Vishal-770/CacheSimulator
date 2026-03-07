"""
simulator.py — Orchestrates a full cache simulation run.
Builds the hierarchy, runs the workload, collects metrics.
"""
from typing import List, Optional
from .hardware import CacheLevel, InterleavedMemory
from .workload import WorkloadGenerator
from .metrics import SimulationReport, LevelMetrics
from .constants import WritePolicy, ReplacementAlgorithm


def build_hierarchy(config: dict) -> tuple:
    """
    Build a cache hierarchy from a flat config dict (used by the Streamlit app).
    
    Config keys:
        l1_size, l1_assoc, l1_block, l1_algo, l1_write_policy,
        l2_size, l2_assoc, l2_block, l2_algo, l2_write_policy,
        use_l2  (bool),
        mem_size, mem_banks, mem_access_time,
        prefetch_enabled, prefetch_degree
    """
    algo_map = {
        "LRU": ReplacementAlgorithm.LRU,
        "FIFO": ReplacementAlgorithm.FIFO,
        "LFU": ReplacementAlgorithm.LFU,
    }
    policy_map = {
        "Write-Back": WritePolicy.WRITE_BACK,
        "Write-Through": WritePolicy.WRITE_THROUGH,
    }

    memory = InterleavedMemory(
        size_bytes=config.get("mem_size", 1024 * 1024),
        num_banks=config.get("mem_banks", 4),
        access_time=config.get("mem_access_time", 100),
    )

    next_level = memory
    levels = []

    if config.get("use_l2", True):
        l2 = CacheLevel(
            name="L2 Cache",
            size_bytes=config.get("l2_size", 4096),
            block_size_bytes=config.get("l2_block", 16),
            associativity=config.get("l2_assoc", 4),
            access_time=config.get("l2_access_time", 10),
            write_policy=policy_map[config.get("l2_write_policy", "Write-Back")],
            replacement_algo=algo_map[config.get("l2_algo", "LRU")],
            next_level=memory,
            prefetch_enabled=False,
        )
        levels.append(l2)
        next_level = l2

    l1 = CacheLevel(
        name="L1 Cache",
        size_bytes=config.get("l1_size", 1024),
        block_size_bytes=config.get("l1_block", 16),
        associativity=config.get("l1_assoc", 2),
        access_time=config.get("l1_access_time", 1),
        write_policy=policy_map[config.get("l1_write_policy", "Write-Back")],
        replacement_algo=algo_map[config.get("l1_algo", "LRU")],
        next_level=next_level,
        prefetch_enabled=config.get("prefetch_enabled", False),
        prefetch_degree=config.get("prefetch_degree", 1),
    )
    levels.insert(0, l1)

    return l1, levels, memory


def run_simulation(config: dict, addresses: List[int], workload_name: str) -> SimulationReport:
    """Run the full simulation and return a SimulationReport."""
    l1, levels, memory = build_hierarchy(config)

    for addr in addresses:
        l1.read(addr)

    report = SimulationReport(
        workload_name=workload_name,
        addresses=addresses,
    )

    for lv in levels:
        report.levels.append(LevelMetrics(
            name=lv.name,
            hits=lv.hits,
            misses=lv.misses,
            writebacks=lv.writebacks,
            prefetch_hits=lv.prefetch_hits,
            prefetch_loads=lv.prefetch_loads,
            access_time=lv.access_time,
            energy_per_hit=lv.energy_per_hit,
            energy_per_miss=lv.energy_per_miss,
        ))

    # Aggregate miss classifications from L1
    report.miss_classifications = levels[0].miss_classifications() if levels else {}
    report.memory_reads = memory.reads
    report.memory_writes = memory.writes
    report.compute(memory_access_time=memory.access_time)
    
    # Pass access log from L1 for trace display
    report._access_log = levels[0].access_log[:200]   # cap to 200 for display

    return report
