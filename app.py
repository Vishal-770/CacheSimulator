"""
app.py — Multi-Level Cache Simulator · Streamlit Dashboard
Run: .\venv\Scripts\streamlit.exe run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from cache_sim import WorkloadGenerator, run_simulation

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cache Simulator",
    page_icon="[SIM]",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color palette (amber / slate / emerald — no purple/blue) ──────────────────
C = {
    "bg":      "#0d1117",
    "surface": "#161b22",
    "border":  "#30363d",
    "text":    "#e6edf3",
    "muted":   "#8b949e",
    "amber":   "#f0a500",
    "amber2":  "#e8720c",
    "emerald": "#3fb950",
    "red":     "#f85149",
    "cyan":    "#39c5cf",
}

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {{ font-family:'Inter',sans-serif; }}

.stApp {{ background:{C["bg"]}; color:{C["text"]}; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background:{C["surface"]};
    border-right:1px solid {C["border"]};
}}
[data-testid="stSidebar"] * {{ color:{C["text"]} !important; }}
[data-testid="stSidebar"] label {{ color:{C["muted"]} !important; }}

/* Metric cards */
[data-testid="metric-container"] {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:10px;
    padding:14px 18px;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color:{C["amber"]} !important;
    font-weight:700;
    font-size:1.4rem;
}}

/* Tabs */
[data-baseweb="tab-list"] {{
    background:{C["surface"]};
    border-radius:8px;
    gap:4px;
}}
[data-baseweb="tab"] {{ color:{C["muted"]} !important; border-radius:6px; }}
[aria-selected="true"] {{
    color:{C["amber"]} !important;
    background:rgba(240,165,0,0.12) !important;
    border-bottom:2px solid {C["amber"]} !important;
}}

/* Buttons */
.stButton > button {{
    background:linear-gradient(135deg, {C["amber"]}, {C["amber2"]});
    color:#0d1117;
    border:none;
    border-radius:8px;
    padding:10px 24px;
    font-weight:700;
    font-size:0.95rem;
    transition:all 0.2s;
}}
.stButton > button:hover {{
    transform:translateY(-1px);
    box-shadow:0 4px 18px rgba(240,165,0,0.35);
}}

/* Headings */
h1 {{ color:{C["amber"]} !important; font-weight:700; letter-spacing:-0.5px; }}
h2, h3, h4 {{ color:{C["text"]} !important; }}

.card {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:10px;
    padding:16px 20px;
    margin-bottom:12px;
}}

.hit-badge  {{ background:#0d2e1a; color:{C["emerald"]}; padding:2px 8px;
               border-radius:4px; font-size:11px; font-weight:700; font-family:monospace; }}
.miss-badge {{ background:#2e0d0d; color:{C["red"]};     padding:2px 8px;
               border-radius:4px; font-size:11px; font-weight:700; font-family:monospace; }}

hr {{ border-color:{C["border"]}; }}
</style>
""", unsafe_allow_html=True)

# ── Matplotlib theme ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  C["surface"],
    "axes.facecolor":    C["bg"],
    "axes.edgecolor":    C["border"],
    "axes.labelcolor":   C["muted"],
    "text.color":        C["text"],
    "xtick.color":       C["muted"],
    "ytick.color":       C["muted"],
    "grid.color":        C["border"],
    "grid.linestyle":    "--",
    "grid.alpha":        0.6,
    "legend.facecolor":  C["surface"],
    "legend.edgecolor":  C["border"],
    "font.family":       "DejaVu Sans",   # safe font — no emojis
})

HIT_C  = C["emerald"]
MISS_C = C["red"]
AMB    = C["amber"]
ALGO_COLORS = {"LRU": C["amber"], "FIFO": C["cyan"], "LFU": C["emerald"]}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"## Cache Configuration")
    st.markdown("---")

    st.markdown(f"**L1 Cache**")
    l1_size   = st.select_slider("L1 Size (bytes)",       [256,512,1024,2048,4096],          value=1024)
    l1_block  = st.select_slider("L1 Block Size (bytes)", [8,16,32,64],                       value=16)
    l1_assoc  = st.selectbox("L1 Associativity", [1,2,4,8], index=1,
                              help="1 = Direct Mapped, N = N-Way Set Associative")
    l1_algo   = st.selectbox("L1 Replacement Policy", ["LRU","FIFO","LFU"])
    l1_policy = st.selectbox("L1 Write Policy",       ["Write-Back","Write-Through"])

    st.markdown("---")
    st.markdown(f"**L2 Cache**")
    use_l2 = st.checkbox("Enable L2 Cache", value=True)
    if use_l2:
        l2_size   = st.select_slider("L2 Size (bytes)",       [1024,2048,4096,8192,16384], value=4096)
        l2_block  = st.select_slider("L2 Block Size (bytes)", [16,32,64],                   value=16)
        l2_assoc  = st.selectbox("L2 Associativity", [1,2,4,8], index=2)
        l2_algo   = st.selectbox("L2 Replacement Policy", ["LRU","FIFO","LFU"])
        l2_policy = st.selectbox("L2 Write Policy",       ["Write-Back","Write-Through"])
    else:
        l2_size = l2_block = l2_assoc = 0
        l2_algo = l2_policy = "LRU"

    st.markdown("---")
    st.markdown(f"**Main Memory**")
    mem_banks = st.selectbox("Memory Banks (Interleaving)", [1,2,4,8], index=2)
    mem_time  = st.slider("Memory Access Time (cycles)", 50, 300, 100, step=10)

    st.markdown("---")
    st.markdown(f"**Prefetching**")
    prefetch_enabled = st.checkbox("Hardware Prefetching (L1)", value=False)
    prefetch_degree  = st.slider("Prefetch Degree", 1, 4, 1, disabled=not prefetch_enabled)

    st.markdown("---")
    st.markdown(f"**Workload**")
    pattern     = st.selectbox("Access Pattern", ["Sequential","Loop","Random","Strided"])
    num_accesses = st.slider("Total Memory Accesses", 16, 512, 128, step=16)
    array_size = iterations = stride = address_space = None
    if pattern == "Loop":
        array_size  = st.slider("Array Size (blocks)", 4, 32, 8)
        iterations  = st.slider("Loop Iterations",      2, 16, 8)
    elif pattern == "Strided":
        stride       = st.slider("Stride (blocks)", 2, 16, 4)
    elif pattern == "Random":
        address_space = st.slider("Address Space (blocks)", 16, 512, 128)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:24px 0 8px 0;">
  <h1 style="font-size:2.2rem; margin-bottom:4px;">
    Multi-Level Cache Simulator
  </h1>
  <p style="color:{C['muted']}; margin:0; font-size:1rem;">
    Simulate L1 / L2 caches &nbsp;·&nbsp; LRU / FIFO / LFU &nbsp;·&nbsp;
    Write-Back / Write-Through &nbsp;·&nbsp; Prefetching &nbsp;·&nbsp;
    Memory Interleaving &nbsp;·&nbsp; AMAT &amp; Energy Analysis
  </p>
</div>
<hr>
""", unsafe_allow_html=True)

# ── Run button ────────────────────────────────────────────────────────────────
col_btn, _ = st.columns([1, 5])
with col_btn:
    run = st.button("Run Simulation", use_container_width=True)

if run:
    config = dict(
        l1_size=l1_size, l1_block=l1_block, l1_assoc=l1_assoc,
        l1_algo=l1_algo, l1_write_policy=l1_policy, l1_access_time=1,
        use_l2=use_l2,
        l2_size=l2_size, l2_block=l2_block, l2_assoc=l2_assoc,
        l2_algo=l2_algo, l2_write_policy=l2_policy, l2_access_time=10,
        mem_size=1024*1024, mem_banks=mem_banks, mem_access_time=mem_time,
        prefetch_enabled=prefetch_enabled, prefetch_degree=prefetch_degree,
    )
    gen = WorkloadGenerator(base_address=0, block_size=l1_block)
    if pattern == "Sequential":
        addresses = gen.sequential(num_accesses)
    elif pattern == "Loop":
        addresses = gen.loop(array_size, iterations)
    elif pattern == "Random":
        addresses = gen.random_access(num_accesses, address_space)
    else:
        addresses = gen.strided(num_accesses, stride)

    with st.spinner("Running simulation..."):
        report = run_simulation(config, addresses, pattern)

    st.session_state["report"]    = report
    st.session_state["config"]    = config
    st.session_state["addresses"] = addresses

# ── Results ───────────────────────────────────────────────────────────────────
if "report" in st.session_state:
    report  = st.session_state["report"]
    config  = st.session_state["config"]

    # KPI row
    st.markdown("### Key Performance Indicators")
    kpi_cols = st.columns(len(report.levels) * 2 + 3)
    idx = 0
    for lm in report.levels:
        kpi_cols[idx].metric(f"{lm.name} Hit Ratio",
                             f"{lm.hit_ratio*100:.1f}%",
                             delta=f"{lm.hits} hits")
        kpi_cols[idx+1].metric(f"{lm.name} Misses", str(lm.misses),
                               delta=f"{lm.miss_rate*100:.1f}% miss rate",
                               delta_color="inverse")
        idx += 2
    kpi_cols[idx  ].metric("AMAT",         f"{report.amat:.2f} cycles")
    kpi_cols[idx+1].metric("RAM Reads",    str(report.memory_reads))
    kpi_cols[idx+2].metric("Total Energy", f"{report.total_energy} units")

    st.markdown("<hr>", unsafe_allow_html=True)

    tabs = st.tabs([
        "Hit / Miss Charts",
        "Miss Classification",
        "Energy & AMAT",
        "Access Trace",
        "Architecture Diagram",
        "Compare Algorithms",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 – Hit / Miss Charts
    # ════════════════════════════════════════════════════════════════════
    with tabs[0]:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        ax = axes[0]
        names  = [lm.name for lm in report.levels]
        hits   = [lm.hits   for lm in report.levels]
        misses = [lm.misses for lm in report.levels]
        x, w   = np.arange(len(names)), 0.35
        b1 = ax.bar(x - w/2, hits,   w, label="Hits",   color=HIT_C,  alpha=0.9)
        b2 = ax.bar(x + w/2, misses, w, label="Misses", color=MISS_C, alpha=0.9)
        ax.bar_label(b1, padding=3, color=HIT_C,  fontsize=10, fontweight="bold")
        ax.bar_label(b2, padding=3, color=MISS_C, fontsize=10, fontweight="bold")
        ax.set_xticks(x); ax.set_xticklabels(names)
        ax.set_ylabel("Count"); ax.set_title("Hits vs Misses per Cache Level")
        ax.legend(); ax.grid(axis="y")

        ax2 = axes[1]
        total_hits   = sum(lm.hits   for lm in report.levels)
        total_misses = sum(lm.misses for lm in report.levels)
        ax2.pie(
            [total_hits, total_misses],
            labels=[f"Hits ({total_hits})", f"Misses ({total_misses})"],
            colors=[HIT_C, MISS_C],
            autopct="%1.1f%%", startangle=90,
            wedgeprops={"edgecolor": C["bg"], "linewidth":2},
            textprops={"color": C["text"]},
        )
        ax2.set_title("Overall Hit Distribution")
        fig.tight_layout(); st.pyplot(fig); plt.close()

        fig2, ax3 = plt.subplots(figsize=(12, 3))
        x_ax  = list(range(1, len(report.levels)+1))
        ratios = [lm.hit_ratio*100 for lm in report.levels]
        ax3.plot(x_ax, ratios, marker="o", color=AMB, linewidth=2.5, markersize=8)
        for xi, yr in zip(x_ax, ratios):
            ax3.annotate(f"{yr:.1f}%", (xi, yr), textcoords="offset points",
                         xytext=(0,10), ha="center", color=AMB)
        ax3.set_xticks(x_ax); ax3.set_xticklabels([lm.name for lm in report.levels])
        ax3.set_ylabel("Hit Ratio (%)"); ax3.set_title("Hit Ratio per Cache Level")
        ax3.set_ylim(0, 115); ax3.grid(True)
        fig2.tight_layout(); st.pyplot(fig2); plt.close()

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 – Miss Classification
    # ════════════════════════════════════════════════════════════════════
    with tabs[1]:
        mc = report.miss_classifications
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        values     = [mc.get("Compulsory",0), mc.get("Capacity",0), mc.get("Conflict",0)]
        labels     = ["Compulsory", "Capacity", "Conflict"]
        colors_mc  = [AMB, C["cyan"], MISS_C]
        non_zero   = [(v,l,c) for v,l,c in zip(values,labels,colors_mc) if v>0]
        if non_zero:
            nv,nl,nc = zip(*non_zero)
            ax1.pie(nv, labels=nl, colors=nc, autopct="%1.0f%%", startangle=90,
                    pctdistance=0.75,
                    wedgeprops={"edgecolor":C["bg"],"linewidth":2,"width":0.55},
                    textprops={"color":C["text"]})
        ax1.set_title("Miss Classification (L1)")

        level_names = [lm.name for lm in report.levels]
        comp = [mc.get("Compulsory",0)] + [0]*(len(level_names)-1)
        cap  = [mc.get("Capacity",  0)] + [0]*(len(level_names)-1)
        conf = [mc.get("Conflict",  0)] + [0]*(len(level_names)-1)
        x    = np.arange(len(level_names))
        ax2.bar(x, comp, label="Compulsory", color=AMB,       alpha=0.9)
        bottom1 = np.array(comp)
        ax2.bar(x, cap,  label="Capacity",   color=C["cyan"], alpha=0.9, bottom=bottom1)
        ax2.bar(x, conf, label="Conflict",   color=MISS_C,    alpha=0.9, bottom=bottom1+np.array(cap))
        ax2.set_xticks(x); ax2.set_xticklabels(level_names)
        ax2.set_ylabel("Miss Count"); ax2.set_title("Miss Types per Level")
        ax2.legend(); ax2.grid(axis="y")
        fig.tight_layout(); st.pyplot(fig); plt.close()

        st.markdown("---")
        co1, co2, co3 = st.columns(3)
        co1.markdown(f"""<div class="card">
            <b style="color:{AMB}">Compulsory Miss</b><br>
            First-ever access to a block. Unavoidable (cold miss).
            Prefetching can reduce them.
        </div>""", unsafe_allow_html=True)
        co2.markdown(f"""<div class="card">
            <b style="color:{C['cyan']}">Capacity Miss</b><br>
            Cache too small to hold the working set. Increase cache size to fix.
        </div>""", unsafe_allow_html=True)
        co3.markdown(f"""<div class="card">
            <b style="color:{MISS_C}">Conflict Miss</b><br>
            Two blocks compete for the same set (direct-mapped). Fix: raise associativity.
        </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 – Energy & AMAT
    # ════════════════════════════════════════════════════════════════════
    with tabs[2]:
        col1, col2 = st.columns(2)
        with col1:
            # AMAT bar per level
            running = config.get("mem_access_time", 100)
            level_amats = []
            for lm in reversed(report.levels):
                running = lm.access_time + lm.miss_rate * running
                level_amats.insert(0, round(running, 2))
            fig, ax = plt.subplots(figsize=(6, 4))
            bar_colors = [AMB, C["cyan"]][:len(level_amats)]
            bars = ax.bar([lm.name for lm in report.levels], level_amats,
                          color=bar_colors, alpha=0.9, width=0.5)
            ax.bar_label(bars, labels=[f"{v:.2f}" for v in level_amats], padding=3)
            ax.set_ylabel("AMAT (cycles)"); ax.set_title("Average Memory Access Time")
            ax.grid(axis="y")
            fig.tight_layout(); st.pyplot(fig); plt.close()

            st.markdown(f"""<div class="card">
                <b>AMAT Formula</b><br>
                <code>AMAT = HitTime + MissRate x NextLevelTime</code><br><br>
                <span style="color:{AMB}; font-size:1.5rem; font-weight:700">{report.amat:.2f} cycles</span>
            </div>""", unsafe_allow_html=True)

        with col2:
            energy_data  = {lm.name: lm.total_energy for lm in report.levels}
            energy_data["Main Memory"] = (report.memory_reads + report.memory_writes) * 50
            fig2, ax2 = plt.subplots(figsize=(6, 4))
            e_colors = [AMB, C["cyan"], MISS_C][:len(energy_data)]
            bars2 = ax2.barh(list(energy_data.keys()), list(energy_data.values()),
                             color=e_colors, alpha=0.9)
            for i,(k,v) in enumerate(energy_data.items()):
                ax2.text(v+0.5, i, str(v), va="center", color=C["text"])
            ax2.set_xlabel("Energy (units)"); ax2.set_title("Energy Consumption by Level")
            ax2.grid(axis="x")
            fig2.tight_layout(); st.pyplot(fig2); plt.close()

            st.markdown(f"""<div class="card">
                <b>Energy Model</b><br>
                Cache Hit: 1 unit &nbsp; Cache Miss: 10 units<br>
                RAM Access: 50 units (expensive!)<br><br>
                <span style="color:{AMB}; font-size:1.5rem; font-weight:700">
                {report.total_energy} total units</span>
            </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # TAB 4 – Access Trace
    # ════════════════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown("**Memory Access Trace — L1 view (first 100 accesses)**")
        log = getattr(report, "_access_log", [])[:100]
        if log:
            rows = []
            for i, entry in enumerate(log):
                result = entry["result"]
                badge  = (f'<span class="hit-badge">HIT</span>'
                          if "HIT" in result else
                          f'<span class="miss-badge">MISS</span>')
                rows.append(
                    f"<tr>"
                    f"<td style='padding:5px 12px;color:{C['muted']}'>{i+1}</td>"
                    f"<td style='padding:5px 12px;font-family:monospace'>"
                    f"0x{entry['address']:04X}  ({entry['address']})</td>"
                    f"<td style='padding:5px 12px'>{badge}</td>"
                    f"</tr>"
                )
            html = (
                f"<div style='max-height:380px;overflow-y:auto;'>"
                f"<table style='width:100%;border-collapse:collapse;'>"
                f"<thead><tr>"
                f"<th style='text-align:left;padding:8px 12px;color:{C['amber']};"
                f"border-bottom:1px solid {C['border']}'>#</th>"
                f"<th style='text-align:left;padding:8px 12px;color:{C['amber']};"
                f"border-bottom:1px solid {C['border']}'>Address</th>"
                f"<th style='text-align:left;padding:8px 12px;color:{C['amber']};"
                f"border-bottom:1px solid {C['border']}'>Result</th>"
                f"</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
            )
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("No trace available. Run the simulation.")

        st.markdown("---")
        st.markdown("**Address Stream Visualization**")
        addr_series = st.session_state.get("addresses", [])[:128]
        if addr_series:
            fig, ax = plt.subplots(figsize=(12, 2.5))
            ax.scatter(range(len(addr_series)), addr_series, s=16, c=AMB, alpha=0.75, zorder=2)
            ax.plot(range(len(addr_series)), addr_series, color=AMB, alpha=0.25, linewidth=1)
            ax.set_xlabel("Access #"); ax.set_ylabel("Address")
            ax.set_title(f"Access Pattern — {st.session_state['report'].workload_name}")
            ax.grid(True)
            fig.tight_layout(); st.pyplot(fig); plt.close()

    # ════════════════════════════════════════════════════════════════════
    # TAB 5 – Architecture Diagram  (NO EMOJI IN MATPLOTLIB)
    # ════════════════════════════════════════════════════════════════════
    with tabs[4]:
        def draw_box(ax, x, y, w, h, title, subtitle, color):
            rect = mpatches.FancyBboxPatch(
                (x,y), w, h, boxstyle="round,pad=0.04",
                linewidth=2, edgecolor=color, facecolor=color+"22",
            )
            ax.add_patch(rect)
            ax.text(x+w/2, y+h*0.63, title,
                    ha="center", va="center", fontsize=12,
                    fontweight="bold", color=color)
            ax.text(x+w/2, y+h*0.27, subtitle,
                    ha="center", va="center", fontsize=8.5, color=C["muted"])

        def draw_arrow(ax, x, y1, y2, label=""):
            ax.annotate("", xy=(x,y2), xytext=(x,y1),
                        arrowprops=dict(arrowstyle="<->", color=C["border"], lw=2))
            if label:
                ax.text(x+0.12, (y1+y2)/2, label,
                        color=C["muted"], fontsize=8.5, va="center")

        fig, ax = plt.subplots(figsize=(6.5, 9))
        ax.set_xlim(0,3); ax.set_ylim(0,10); ax.axis("off")
        ax.set_facecolor(C["bg"]); fig.patch.set_facecolor(C["surface"])

        l1m = report.levels[0]
        draw_box(ax, 0.4, 8.1, 2.2, 0.8, "CPU", "Processor Core", C["text"])
        draw_arrow(ax, 1.5, 7.95, 7.1)
        draw_box(ax, 0.4, 6.2, 2.2, 0.8, "L1 Cache",
                 f"{l1_size}B  {l1_assoc}-Way  {l1_algo}  |  {l1m.hit_ratio*100:.0f}% HR",
                 AMB)

        if config.get("use_l2") and len(report.levels) > 1:
            l2m = report.levels[1]
            draw_arrow(ax, 1.5, 6.0, 5.0, "Miss ->")
            draw_box(ax, 0.4, 4.1, 2.2, 0.8, "L2 Cache",
                     f"{l2_size}B  {l2_assoc}-Way  {l2_algo}  |  {l2m.hit_ratio*100:.0f}% HR",
                     C["cyan"])
            draw_arrow(ax, 1.5, 3.95, 3.0, "Miss ->")
            draw_box(ax, 0.4, 2.1, 2.2, 0.8, "Main Memory",
                     f"{mem_banks} banks  |  {mem_time} cycles", C["emerald"])
        else:
            draw_arrow(ax, 1.5, 6.0, 3.0, "Miss ->")
            draw_box(ax, 0.4, 2.1, 2.2, 0.8, "Main Memory",
                     f"{mem_banks} banks  |  {mem_time} cycles", C["emerald"])

        ax.set_title("Memory Hierarchy", fontsize=13, pad=10, color=C["text"])
        st.pyplot(fig); plt.close()

        st.markdown("---")
        st.markdown("**Cache Block Structure**")
        ca, cb = st.columns(2)
        ca.markdown(f"""<div class="card">
        <b>Standard Block</b>
        <table style="width:100%;margin-top:10px;border-collapse:collapse">
        <tr style="background:{C['border']}">
          <th style="padding:8px;text-align:center">Valid Bit</th>
          <th style="padding:8px;text-align:center">Tag</th>
          <th style="padding:8px;text-align:center">Data Block</th>
        </tr>
        <tr>
          <td style="padding:8px;text-align:center;color:{HIT_C}">1 bit</td>
          <td style="padding:8px;text-align:center;color:{AMB}">t bits</td>
          <td style="padding:8px;text-align:center;color:{C['cyan']}">B bytes</td>
        </tr></table></div>""", unsafe_allow_html=True)
        cb.markdown(f"""<div class="card">
        <b>Write-Back Block (Dirty Bit)</b>
        <table style="width:100%;margin-top:10px;border-collapse:collapse">
        <tr style="background:{C['border']}">
          <th style="padding:8px;text-align:center">Valid</th>
          <th style="padding:8px;text-align:center">Tag</th>
          <th style="padding:8px;text-align:center">Dirty</th>
          <th style="padding:8px;text-align:center">Data</th>
        </tr>
        <tr>
          <td style="padding:8px;text-align:center;color:{HIT_C}">1 bit</td>
          <td style="padding:8px;text-align:center;color:{AMB}">t bits</td>
          <td style="padding:8px;text-align:center;color:{MISS_C}">1 bit</td>
          <td style="padding:8px;text-align:center;color:{C['cyan']}">data</td>
        </tr></table></div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # TAB 6 – Compare Algorithms
    # ════════════════════════════════════════════════════════════════════
    with tabs[5]:
        st.markdown("**Run the same workload with LRU, FIFO, and LFU and compare results**")
        with st.spinner("Comparing algorithms..."):
            algos = ["LRU","FIFO","LFU"]
            compare_rows = []
            for algo in algos:
                cmp_cfg = dict(config); cmp_cfg["l1_algo"] = algo
                cr  = run_simulation(cmp_cfg, st.session_state["addresses"], pattern)
                l1m = cr.levels[0]
                compare_rows.append({
                    "Algorithm":     algo,
                    "L1 Hits":       l1m.hits,
                    "L1 Misses":     l1m.misses,
                    "Hit Ratio (%)": round(l1m.hit_ratio*100, 2),
                    "AMAT (cycles)": cr.amat,
                    "Total Energy":  cr.total_energy,
                    "Writebacks":    l1m.writebacks,
                })

        df_cmp = pd.DataFrame(compare_rows).set_index("Algorithm")
        # Convert all to string so Arrow serialization never chokes
        st.dataframe(df_cmp.astype(str), width="stretch")

        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        metrics_plt = ["Hit Ratio (%)","AMAT (cycles)","Total Energy"]
        for i, metric in enumerate(metrics_plt):
            ax = axes[i]
            vals   = df_cmp[metric].astype(float)
            colors = [ALGO_COLORS[a] for a in df_cmp.index]
            bars   = ax.bar(df_cmp.index, vals, color=colors, alpha=0.9, width=0.45)
            ax.bar_label(bars, labels=[f"{v:.1f}" for v in vals], padding=3)
            ax.set_title(metric); ax.set_ylabel(metric); ax.grid(axis="y")
            # Highlight the winning bar
            winner = vals.idxmax() if metric == "Hit Ratio (%)" else vals.idxmin()
            for bar, algo in zip(bars, df_cmp.index):
                if algo == winner:
                    bar.set_edgecolor(C["text"]); bar.set_linewidth(2.5)
        fig.suptitle("Replacement Algorithm Comparison", fontsize=13)
        fig.tight_layout(); st.pyplot(fig); plt.close()

        best_hr   = df_cmp["Hit Ratio (%)"].astype(float).idxmax()
        best_amat = df_cmp["AMAT (cycles)"].astype(float).idxmin()
        st.success(f"Best Hit Ratio: **{best_hr}** &nbsp;&nbsp;|&nbsp;&nbsp; Lowest AMAT: **{best_amat}**")

    # ── Full report expandable ────────────────────────────────────────
    with st.expander("Full Simulation Report"):
        rpt_dict = report.to_dict()
        # Ensure all values are strings for Arrow compatibility
        rpt_df = pd.DataFrame(
            {"Metric": list(rpt_dict.keys()), "Value": [str(v) for v in rpt_dict.values()]}
        ).set_index("Metric")
        st.dataframe(rpt_df, width="stretch")

else:
    # Landing page (no simulation yet)
    st.markdown(f"""
    <div style="text-align:center; padding:70px 0;">
      <div style="font-size:4rem; margin-bottom:16px;">&#9776;</div>
      <h2 style="color:{C['amber']}; margin-bottom:10px;">Configure a Simulation</h2>
      <p style="color:{C['muted']}; max-width:520px; margin:0 auto; font-size:1rem; line-height:1.7">
        Use the sidebar to set L1 / L2 cache parameters, choose a replacement policy,
        write policy, enable prefetching, and pick a memory workload pattern.
        Then click <b style="color:{C['amber']}">Run Simulation</b>.
      </p>
      <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:32px;">
        {"".join(f'<div class="card" style="width:160px;text-align:center">{t}</div>'
                 for t in ["LRU / FIFO / LFU","AMAT Analysis","Miss Classification",
                            "Algorithm Compare","Memory Interleaving","Prefetching"])}
      </div>
    </div>
    """, unsafe_allow_html=True)
