# Multi-Level Cache Simulator

A robust, configurable Multi-Level Cache Simulator built in Python with an interactive Streamlit dashboard.
Simulates L1/L2 cache hierarchies, multiple replacement algorithms, write policies, prefetching, memory interleaving, AMAT, and energy analysis.

## Features

- **Multi-Level Cache Hierarchy** — L1 and L2 caches connected to interleaved Main Memory
- **Cache Block Structure** — Valid Bit, Tag, Dirty Bit, Data
- **Write Policies** — Write-Through and Write-Back (with dirty bit eviction)
- **Replacement Algorithms** — LRU, FIFO, LFU
- **Hardware Prefetching** — loads next N blocks on a miss
- **Miss Classification** — Compulsory, Capacity, Conflict
- **Memory Interleaving** — up to 8 parallel memory banks
- **Performance Metrics** — Hit Ratio, AMAT, Miss Penalty, Energy Usage
- **Workload Simulation** — Sequential, Loop, Random, Strided access patterns
- **Interactive Dashboard** — 6-tab Streamlit UI with live charts

## Project Structure

```
CacheSimulator/
├── app.py                  ← Streamlit dashboard (main frontend)
├── main.py                 ← CLI runner (quick test / no UI)
├── README.md
└── cache_sim/
    ├── __init__.py
    ├── constants.py        ← Enums (WritePolicy, ReplacementAlgorithm, MissType)
    ├── hardware.py         ← CacheBlock, CacheSet, CacheLevel, InterleavedMemory
    ├── workload.py         ← WorkloadGenerator (Sequential / Loop / Random / Strided)
    ├── metrics.py          ← LevelMetrics, SimulationReport, AMAT calculation
    └── simulator.py        ← Orchestrator (build_hierarchy, run_simulation)
```

## Getting Started

### 1. Clone / open the project

```powershell
cd d:\WINTER-25-26\CAO\CacheSimulator
```

### 2. Create a virtual environment

```powershell
python -m venv venv
```

### 3. Activate the virtual environment

```powershell
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat
```

### 4. Install dependencies

```powershell
.\venv\Scripts\python.exe -m pip install streamlit pandas matplotlib numpy
```

### 5. Run the interactive dashboard

```powershell
.\venv\Scripts\streamlit.exe run app.py
```

Then open your browser at **http://localhost:8501**

### 6. (Optional) Run the CLI tester

```powershell
.\venv\Scripts\python.exe main.py
```

## Dashboard Tabs

| Tab | What it shows |
|-----|--------------|
| **Hit / Miss Charts** | Bar + pie charts of hits vs misses per cache level |
| **Miss Classification** | Compulsory / Capacity / Conflict breakdown |
| **Energy & AMAT** | Average Memory Access Time, energy cost per level |
| **Access Trace** | Per-address hit/miss log + address stream plot |
| **Architecture Diagram** | Visual hierarchy (CPU → L1 → L2 → RAM) |
| **Compare Algorithms** | LRU vs FIFO vs LFU side-by-side on the same workload |
