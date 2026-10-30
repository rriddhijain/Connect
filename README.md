# Network Bandwidth Allocation Simulator

A software-only, discrete-time **Network Bandwidth Allocation and Quality of Service (QoS) Simulator** with an interactive **Streamlit** dashboard.

This simulator models synthetic users sharing a single bottleneck link and compares three foundational network resource-management policies on the **exact same packet-arrival trace**:

1. **Equal Bandwidth Allocation (Fair-Share Service)**: Divides transmission service evenly among active queues.
2. **Strict Priority Packet Scheduling**: Serves latency-sensitive high-priority packets (Voice, Video) before lower-priority packets (Web, File Download), showing QoS benefits and starvation trade-offs.
3. **Round-Robin Packet Scheduling**: Cycles turns through active user queues, preventing any single flow from monopolizing transmission opportunities.

> **Zero Hardware Requirement**: The simulator runs entirely in software on synthetic, reproducible traffic traces. No network captures, real router hardware, or external network access are needed.

---

## 🌟 Key Features

- **100% Deterministic & Reproducible**: Powered by seeded pseudo-random trace generation. Changing the seed alters the trace, but all 3 policies always replay the **exact same arrivals**.
- **Packet-Conservation Invariant**: Strictly enforces the fundamental accounting rule:
  $$\text{Total Generated} = \text{Delivered} + \text{Dropped (Buffer Overflow)} + \text{Remaining in Queue}$$
- **Physical Link Capacity Enforcement**: The simulation strictly enforces maximum transmission bits per discrete time step ($dt = 10\text{ ms}$):
  $$\text{Max Transmission Budget (bits)} = \text{Bandwidth (bps)} \times dt$$
- **Pre-Configured Scenario Presets**:
  - **Light Load** (~35% of capacity): Minimal queuing, ~100% PDR, low latency across all policies.
  - **Moderate Load** (~85% of capacity): Approaching link saturation; policies start exhibiting latency variance.
  - **Heavy Congestion** (~175% of capacity): Buffers overflow; strict priority preserves voice while starving downloads; round-robin and equal-share provide balanced delivery.
  - **Mixed Traffic** (~115% of capacity): Diverse mixture of real-time, interactive, and bulk flows.
- **Interactive Visualizations (Plotly)**:
  - Throughput vs. Link Capacity limit
  - Packet Delivery Ratio (PDR) vs. Loss Ratio (PLR)
  - Latency Trade-offs: Mean Latency and 95th Percentile Latency
  - Jain's Fairness Index comparison
  - Real-time dynamic traces: Instantaneous throughput and aggregate queue depth over time
- **QoS & Traffic Class Deep-Dive**: Breakdown by application type (Voice, Video, Web, File Download).
- **Per-User Inspection**: Drill down into individual synthetic user statistics.

---

## 🏗️ Project Architecture

```text
Connect/
├── app.py                      # Interactive Streamlit dashboard
├── README.md                   # Comprehensive project documentation
├── requirements.txt            # Python dependencies
├── src/
│   ├── __init__.py
│   ├── models.py               # Data models (Packet, User, Priority, TrafficClass, SimulationConfig)
│   ├── traffic.py              # Deterministic synthetic traffic trace generator
│   ├── queues.py               # FIFO queues and tail-drop buffer overflow manager
│   ├── simulator.py            # Discrete-time simulation engine & invariant verification
│   ├── metrics.py              # Metric calculations & Jain's Fairness Index
│   ├── export.py               # CSV and JSON export formatters
│   └── policies/
│       ├── __init__.py
│       ├── base.py             # SchedulingPolicy abstract interface
│       ├── equal_share.py      # Equal allocation policy
│       ├── priority.py         # Strict priority scheduler
│       └── round_robin.py      # Round-robin packet scheduler
└── tests/
    ├── __init__.py
    ├── test_traffic.py         # Seed reproducibility and traffic class tests
    ├── test_accounting.py      # Conservation invariant and capacity enforcement tests
    ├── test_policies.py        # Policy behavior and starvation tests
    └── test_metrics.py         # Jain's fairness and metric accuracy tests
```

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.11, 3.12, or 3.13
- Virtual environment tool (`venv` or `uv`)

### 2. Installation

Clone or open the repository folder:
```bash
cd /Users/riddhijain/Connect
```

Create a virtual environment and install dependencies:
```bash
# Using standard Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or using uv (recommended for ultra-fast setup)
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
```

### 3. Running the Test Suite
Run the automated pytest suite (17 tests covering accounting, policies, metrics, and traffic generation):
```bash
.venv/bin/pytest tests/ -v
```

### 4. Launching the Interactive Web Dashboard
Run the Streamlit application:
```bash
.venv/bin/streamlit run app.py
```
Then open your web browser at `http://localhost:8501`.

---

## 📐 Formulas and Network Metrics

| Metric | Formula | Description |
|---|---|---|
| **Aggregate Throughput** | $\frac{\text{Delivered Bits}}{\text{Duration (s)} \times 10^6}$ | Link throughput delivered in Mbps. Cannot exceed configured capacity. |
| **Packet Delivery Ratio (PDR)** | $\frac{\text{Delivered Packets}}{\text{Generated Packets}} \times 100\%$ | Percentage of offered packets successfully transmitted. |
| **Packet Loss Ratio (PLR)** | $\frac{\text{Dropped Packets}}{\text{Generated Packets}} \times 100\%$ | Percentage of packets dropped due to buffer overflow. |
| **Mean Latency** | $\frac{1}{N}\sum (\text{Delivery Time} - \text{Arrival Time}) \times 1000$ | Average end-to-end delay (ms) for delivered packets. |
| **95th Percentile Latency** | 95th percentile of delivered packet latency | Tail latency indicator for jitter-sensitive traffic. |
| **Bandwidth Utilization** | $\frac{\text{Delivered Bits}}{\text{Capacity (bps)} \times \text{Duration (s)}} \times 100\%$ | Percentage of total available link capacity utilized. |
| **Jain's Fairness Index** | $\frac{\left(\sum_{i=1}^n x_i\right)^2}{n \sum_{i=1}^n x_i^2}$ | Evaluates throughput fairness among all $n$ users ($1/n \le J \le 1.0$). |

---

## ⚠️ Assumptions and Limitations

- **Software Simulator**: Models a single shared bottleneck link; does not transmit real Ethernet/Wi-Fi frames.
- **Single Bottleneck**: Does not model multi-hop Internet routing or propagation delays across continents.
- **No Transport Layer Dynamics**: Synthetic traffic patterns are open-loop offered loads; TCP congestion-window back-off (AIMD) is not simulated.
