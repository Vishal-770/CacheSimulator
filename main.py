from cache_sim import MainMemory, CacheLevel, WritePolicy, ReplacementAlgorithm

def main():
    print("--- Phase 2: Multi-Level Cache Simulation Test ---")
    
    # Setup Phase 2 Hierarchy: L1 -> L2 -> Main Memory
    # Main Memory: 1MB
    memory = MainMemory(size_bytes=1024 * 1024, access_time=100)
    
    # L2 Cache: 4KB, 16-byte blocks, 4-Way Set Associative
    l2_cache = CacheLevel(
        name="L2 Cache",
        size_bytes=4096,
        block_size_bytes=16,
        associativity=4,
        access_time=10,
        write_policy=WritePolicy.WRITE_BACK,
        replacement_algo=ReplacementAlgorithm.LRU,
        next_level=memory
    )

    # L1 Cache: 1KB, 16-byte blocks, 2-Way Set Associative
    l1_cache = CacheLevel(
        name="L1 Cache",
        size_bytes=1024,
        block_size_bytes=16,
        associativity=2,
        access_time=1,
        write_policy=WritePolicy.WRITE_THROUGH, # L1 writes through to L2
        replacement_algo=ReplacementAlgorithm.LRU,
        next_level=l2_cache
    )
    
    print(f"L2 Num Sets: {l2_cache.num_sets}")
    print(f"L1 Num Sets: {l1_cache.num_sets}")

    # Simulated Addresses:
    # 0, 16, 32 map to Set 0 in L1 and L2 (with 16-byte blocks).
    # Since L1 is 2-Way associative, reading 0, 16, 32 will cause an eviction of 0 on the 3rd read!
    # But L2 is 4-Way associative, so it can hold all 3.
    addresses_to_read = [
        0,    # L1 Miss, L2 Miss
        16,   # L1 Miss, L2 Miss
        0,    # L1 Hit  (LRU updates 0 to most recently used)
        32,   # L1 Miss, Evicts 16 (since 0 was just used) -> L2 Miss
        16,   # L1 Miss (Evicted previously), L2 Hit! (L2 has 4-way assoc)
    ]
    
    print("\n--- CPU Requests ---")
    for addr in addresses_to_read:
        print(f"CPU Reading Address {addr}...")
        _ = l1_cache.read(addr)
    
    print("\n--- Results ---")
    print(f"L1 Hits: {l1_cache.hits}, L1 Misses: {l1_cache.misses} (Hit Ratio: {l1_cache.get_hit_ratio() * 100:.2f}%)")
    print(f"L2 Hits: {l2_cache.hits}, L2 Misses: {l2_cache.misses} (Hit Ratio: {l2_cache.get_hit_ratio() * 100:.2f}%)")

if __name__ == "__main__":
    main()
