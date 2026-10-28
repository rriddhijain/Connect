# Network Bandwidth Allocation Simulator
## Project Plan and Implementation Specification

## 1. Project Overview

Build a software-only **Network Bandwidth Allocation Simulator** that models multiple fake users sharing a limited-bandwidth network. The application will compare three network resource-management policies:

1. **Equal bandwidth allocation** — divide capacity evenly among active users.
2. **Priority-based packet scheduling** — serve higher-priority traffic before lower-priority traffic, while respecting the total link capacity.
3. **Round-robin packet scheduling** — serve packet queues in turns so that one continuously active user cannot monopolize transmission opportunities.

The project must run entirely on simulated data. **Do not connect to real users, capture real network traffic, access a router, or require physical hardware.** All users, packets, traffic patterns, and network conditions are generated locally by the simulator.

The goal is to demonstrate networking concepts such as Quality of Service (QoS), bandwidth limits, packet queues, congestion, scheduling, latency, throughput, packet loss, utilization, and fairness.

## 2. Core Goals

- Generate realistic-enough synthetic users and traffic without collecting real user data.
- Let the user configure network capacity, number of simulated users, simulation duration, and traffic mix.
- Run the same traffic scenario through each scheduling/allocation policy so results are comparable.
- Measure performance using explicit formulas rather than invented or hard-coded results.
- Visualize how each policy behaves under light load and congestion.
- Keep the project understandable for a student to explain in a networking viva.
- Include reproducible runs: a random seed should make a scenario repeatable.

## 3. Recommended Technology Stack

- **Python 3.11+**
- **Streamlit** for the interactive web dashboard
- **NumPy** for calculations and synthetic data generation
- **Pandas** for result tables
- **Plotly** (preferred) or Matplotlib for interactive charts
- **pytest** for core logic tests
- Optional: **SimPy** for discrete-event simulation. Prefer a small custom discrete-time simulator for the first version if that is simpler to reason about and debug.

Keep the simulation engine independent from the Streamlit UI so it can be tested and run from Python directly.

## 4. What the Simulator Represents

The simulated network is a single shared bottleneck link with a configurable capacity, such as 10, 20, 50, or 100 Mbps.

Each synthetic user generates packets over time. Every packet has:
- A unique packet ID
- User ID
- Traffic class
- Packet size in bytes
- Generation/arrival time
- Queue-entry time
- Delivery time, if delivered
- Status: delivered or dropped

Each synthetic user has:
- Unique ID and display name
- Traffic type
- Priority level
- Packet generation pattern
- Requested traffic rate or packet-arrival intensity
- Packet size distribution
- Counters for generated, delivered, and dropped packets

### Traffic classes

Use these default traffic profiles, configurable in the dashboard:

| Traffic class | Priority | Example packet size | Traffic pattern | Purpose |
|---|---:|---:|---|---|
| Voice/video call | High | 200 bytes | Small, frequent packets | Latency-sensitive |
| Online lecture/video | High | 1,000 bytes | Periodic packets | Real-time-ish media |
| Web browsing | Medium | 1,200 bytes | Bursty requests | Interactive traffic |
| File download | Low | 1,400 bytes | Continuous/bulk traffic | Throughput-oriented |

These are simplified synthetic profiles, not claims about every real application. State in the UI or README that they are illustrative.

## 5. Simulation Model

### 5.1 Time model

Use a discrete-time simulation with a configurable time step, for example **10 milliseconds (0.01 seconds)**. The user chooses a simulation duration such as 30–120 seconds.

At every time step:
1. Generate new packets according to each user's configured traffic pattern.
2. Add new packets to that user's queue.
3. If a queue or global buffer limit is exceeded, drop packets and record the reason.
4. Use the selected policy to choose packets for transmission.
5. Transmit only as much data as the link capacity permits during the time step.
6. Mark completed packets as delivered and record delay.
7. Update counters and time-series measurements.

Important: Do not allow the simulator to transmit more bits in a time step than the configured link capacity permits. For capacity `C` Mbps and step `dt` seconds, the maximum transmission budget is:

`budget_bits = C * 1_000_000 * dt`

Only packets that fit within the remaining budget may be fully transmitted. If implementing packet fragmentation is desired, make it an explicit optional feature; otherwise, carry unused budget forward within the time step or document the packet-fit rule. A simpler and consistent alternative is a byte-credit/token accumulator that preserves unused transmission capacity across steps. Pick one method and use it consistently across all policies.

### 5.2 Synthetic traffic generation

Create synthetic traffic locally using a seeded pseudo-random generator.

Provide two modes:
- **Preset scenario mode**: use predefined traffic profiles for quick demos.
- **Custom mode**: let the user adjust the number of users, class mix, offered load, and packet arrival intensity.

Suggested traffic behavior:
- Voice/video: generate small packets at a regular interval with small jitter.
- Online lecture/video: generate medium-sized packets periodically.
- Browsing: generate short bursts separated by idle periods.
- Downloads: generate packets continuously until the configured offered load is reached.

Do not make arrival generation depend on which policy is currently being tested. Generate a scenario once and replay the **same packet-arrival trace** for every policy, so comparisons are fair. Use the same seed and same generated arrivals for all policies.

### 5.3 Queue model

Start with one FIFO queue per user. Track queue length over time and allow a configurable maximum queue size in packets or bytes.

If the queue is full, drop newly arriving packets and count them as buffer-overflow drops. This gives packet loss a meaningful definition. Avoid silently discarding packets.

A user can have an empty queue at some time steps. Scheduling policies should skip empty queues.

### 5.4 Policies to implement

#### Policy A: Equal allocation baseline

Implement a clear baseline that divides the available transmission service equally among users with queued data. For each time step, identify active queues and assign each an equal share of the available service budget, subject to packet sizes and queue contents.

Document that this is an **equal-share service policy**. It may be implemented at packet level using per-user byte credits or a fair-share service budget. Do not claim it is identical to every real-world router's bandwidth allocator.

#### Policy B: Priority-based scheduling

Assign a priority rank to each traffic class. Serve high-priority packets before medium- and low-priority packets, while respecting the link capacity. Within the same priority, use FIFO order. Define whether priority is strict or weighted; for the first version, use **strict priority** and clearly state that continuous high-priority traffic can starve low-priority traffic.

The dashboard should show the trade-off: high-priority traffic may get lower delay, while lower-priority traffic may wait longer or experience more drops under congestion.

#### Policy C: Round-robin scheduling

Maintain one FIFO queue per user. Visit non-empty queues in a rotating order and transmit one packet (or a configurable quantum of bytes) per turn, then move to the next active queue. Continue cycling while transmission budget remains.

Use a byte quantum or packet quantum consistently. Since packet sizes vary, **byte-based deficit round robin** is a good extension, but a simple packet-based round robin is acceptable for the first version if its limitations are explained.

### Important modeling decision

Equal allocation and round-robin are related but not the same:
- Equal allocation aims to share service capacity evenly among active users.
- Round-robin gives users turns to send queued packets.
- Priority scheduling deliberately favors certain traffic classes.

Explain this distinction in the README and dashboard. Use the same generated arrival trace and capacity for every policy.

## 6. Dashboard Requirements

Build a clean Streamlit app with the following sections.

### A. Sidebar: Simulation Controls
- Total bandwidth (Mbps), default 20 Mbps
- Number of synthetic users, default 10
- Simulation duration in seconds, default 60
- Time step, default 0.01 seconds (advanced setting; optionally fixed initially)
- Maximum queue size
- Random seed
- Scenario preset: Light Load, Moderate Load, Heavy Congestion, Mixed Traffic
- Optional custom traffic-class distribution
- Run Simulation button

### B. Overview / Summary
Display:
- Total generated packets
- Total delivered packets
- Total dropped packets
- Aggregate throughput (Mbps)
- Packet delivery ratio
- Packet loss ratio
- Average latency (ms)
- 95th percentile latency (ms)
- Bandwidth utilization (%)
- Jain's fairness index

Always label values with units. If a metric is undefined (for example, latency when no packets were delivered), display N/A rather than inventing a value.

### C. Policy Comparison
Provide a table with one row per policy:
- Policy name
- Throughput (Mbps)
- Mean latency (ms)
- 95th percentile latency (ms)
- Packet loss (%)
- Utilization (%)
- Jain's fairness index
- Delivered packets

Add charts:
- Throughput by policy
- Mean and p95 latency by policy
- Packet loss by policy
- Fairness by policy
- Bandwidth utilization by policy
- Optional time-series graph of queue length and throughput

Do not pre-fill charts with made-up sample results. Generate them from the actual simulation output. If a policy performs better on one metric but worse on another, show that trade-off rather than declaring one universal winner.

### D. User / Traffic Details
Allow selecting a synthetic user to inspect:
- Traffic class
- Packets generated/delivered/dropped
- Throughput
- Mean and p95 latency
- Average queue length or waiting time

### E. Packet/Queue Animation (optional)
A simple visual that shows packets moving from generated traffic into queues and then through the bottleneck link is useful but secondary. Do not sacrifice simulation correctness for animation.

### F. Export
Allow exporting policy comparison and per-user metrics as CSV. Include the random seed and simulation configuration in the export or a metadata file.

## 7. Metrics and Formulas

Implement metrics from recorded events.

Let:
- `generated` = number of packets created
- `delivered` = number of packets successfully transmitted
- `dropped` = number of packets dropped by the queue/buffer model
- `simulation_duration` = simulation duration in seconds
- `delivered_bits` = total bits in delivered packets
- `total_capacity_bits` = link capacity in bits per second multiplied by measurement duration

Formulas:

**Aggregate throughput**
`throughput_mbps = delivered_bits / measurement_duration_seconds / 1_000_000`

**Packet delivery ratio**
`PDR = delivered / generated * 100`

**Packet loss ratio**
`PLR = dropped / generated * 100`

If packets remain queued at the end, report them as `remaining_in_queue`; do not count them as delivered. Either report them separately or, if the project defines end-of-simulation packets as lost, state that convention explicitly. Prefer reporting them separately for transparency.

**Average latency**
`mean_latency_ms = mean(delivery_time - arrival_time) * 1000` for delivered packets.

**95th percentile latency**
The 95th percentile of delivery latency among delivered packets.

**Bandwidth utilization**
`utilization_pct = delivered_bits / (capacity_mbps * 1_000_000 * measurement_duration_seconds) * 100`

Use the same measurement window for all policies. Decide whether the first and last partial time steps count; document it and apply consistently.

**Per-user throughput**
Delivered bits for a user divided by the same measurement duration.

**Jain's fairness index**
For per-user throughput values `x_i` across the same set of users:

`J = (sum(x_i) ** 2) / (n * sum(x_i ** 2))`

If all throughput values are zero, report N/A or define a documented convention. Use all configured users, including users with zero throughput, to avoid hiding starvation.

**Queue waiting time (optional but recommended)**
`queue_wait = transmission_start_time - arrival_time`

**End-to-end simulated latency**
For this single-link simulator, define latency as arrival-to-delivery time, which includes queue waiting and serialization/transmission delay. State that propagation delay and real Internet behavior are not modeled unless explicitly added.

### Metric integrity rules
- Throughput must not exceed the link capacity, aside from a clearly explained boundary/measurement convention.
- Packet accounting must be consistent: generated packets should equal delivered + dropped + remaining in queues (plus any packet currently in service, if modeled separately).
- Never show hard-coded or random metric values unrelated to simulation events.
- Guard against division by zero and empty results.
- Use one shared metric calculation module for all policies.

## 8. Scenario Presets

Implement at least four scenarios, using the same user count and random seed when comparing policies.

1. **Light Load**: offered traffic is well below link capacity. Expect most policies to perform similarly.
2. **Moderate Load**: offered traffic approaches link capacity. Differences may start to appear.
3. **Heavy Congestion**: offered traffic exceeds link capacity. Queues build, delays rise, and queue overflow may cause drops.
4. **Mixed Traffic**: a combination of latency-sensitive, interactive, and bulk traffic.

Do not force the outcomes to match a predetermined expectation. The model should generate the results; presets only define the input traffic conditions.

## 9. Suggested Project Structure

Use a structure similar to:

```text
network-bandwidth-simulator/
├── app.py                    # Streamlit UI and navigation
├── README.md                 # Setup, usage, assumptions, limitations
├── requirements.txt
├── src/
│   ├── models.py             # Packet, User, SimulationConfig data models
│   ├── traffic.py            # Synthetic traffic and trace generation
│   ├── queues.py             # FIFO queues and overflow behavior
│   ├── policies/
│   │   ├── base.py           # Common policy interface
│   │   ├── equal_share.py    # Equal-share service
│   │   ├── priority.py       # Strict priority scheduler
│   │   └── round_robin.py    # Round-robin scheduler
│   ├── simulator.py          # Simulation engine
│   ├── metrics.py            # Shared metric calculations
│   └── export.py             # CSV export helpers
└── tests/
    ├── test_traffic.py
    ├── test_policies.py
    ├── test_metrics.py
    └── test_accounting.py
```

Claude Code may adjust the structure if it has a clear reason, but it must keep the simulation engine separate from UI code.

## 10. Implementation Plan

Build in small, testable stages.

### Stage 1 — Repository and runnable skeleton
- Create the project structure.
- Add `requirements.txt`.
- Create a basic Streamlit app that launches.
- Add README setup instructions.

### Stage 2 — Synthetic traffic generation
- Implement seeded generation of synthetic users and packet arrival traces.
- Create the four preset scenarios.
- Ensure all policies can replay exactly the same arrival trace.

### Stage 3 — Simulation engine
- Implement packet, user, queue and configuration models.
- Implement the bottleneck link and transmission budget.
- Add buffer limits and packet accounting.
- Write tests for capacity and accounting constraints.

### Stage 4 — Scheduling policies
- Implement equal-share service.
- Implement strict priority scheduling.
- Implement round-robin scheduling.
- Test that each policy respects capacity and handles empty queues.

### Stage 5 — Metrics
- Implement throughput, delivery ratio, loss ratio, mean/p95 latency, utilization and Jain's fairness.
- Add per-user metrics and remaining queue counts.
- Test formulas and zero/empty cases.

### Stage 6 — Dashboard
- Add sidebar controls and Run Simulation action.
- Show summary metrics, policy comparison table and charts.
- Add per-user inspection.
- Make all charts use real simulation output.

### Stage 7 — Export and polish
- Add CSV export for aggregate and per-user results.
- Add configuration/seed metadata.
- Improve labels, tooltips and layout.
- Add a clear explanation of each policy and metric.

### Stage 8 — Verification
- Run the test suite.
- Run a short end-to-end simulation.
- Check that results are deterministic with a fixed seed.
- Check that all policies receive the same traffic trace.
- Check that no metric is fabricated or hard-coded.
- Check that total delivered data never exceeds link capacity.
- Check packet accounting and ensure remaining packets are reported.
- Fix bugs before adding optional animations or extra features.

## 11. Acceptance Criteria

The project is considered complete when:

- It launches locally with `streamlit run app.py`.
- No external accounts, physical devices, real users, or real network traffic are needed.
- The user can select a scenario and change the bandwidth, user count, duration, queue limit and seed.
- All three policies run on the same generated traffic trace.
- The dashboard displays computed metrics and comparison charts.
- Results are reproducible with the same settings and seed.
- Unit tests cover policy behavior, metric calculations, capacity limits and packet accounting.
- CSV exports work.
- README explains setup, algorithms, assumptions and limitations.
- The application clearly labels all traffic and users as simulated.

## 12. Assumptions and Limitations

The initial version is a **simulator, not a real network emulator**:
- It does not send packets over Wi-Fi or Ethernet.
- It does not control an operating-system router or perform real QoS configuration.
- It does not model radio interference, Wi-Fi contention, retransmissions at the wireless MAC layer, TCP congestion control, routing, propagation delay, or the full Internet stack.
- It models one shared bottleneck link with synthetic packet arrivals.
- The selected packet sizes and traffic patterns are simplified and should be documented as assumptions.

Possible future extensions, only after the core project is correct:
- Weighted fair queuing or deficit round robin.
- Token-bucket rate limiting.
- Different queue-management strategies.
- Separate uplink/downlink bottlenecks.
- Wireless-specific effects such as interference and retransmission probabilities.
- Scenario comparison across different traffic mixes.
- A downloadable PDF report.

## 13. Instructions for Claude Code

Implement this project in the current repository.

Before coding:
1. Inspect the existing files and preserve useful work.
2. Briefly summarize the implementation approach.
3. Identify any assumptions that need a decision; use the defaults in this plan rather than blocking on minor choices.

Then implement the project end to end. Do not stop after generating a plan or skeleton.

Important requirements:
- Use only synthetic users and synthetic packet traces.
- Keep the core simulator deterministic when given a seed.
- Run the same arrival trace through every policy.
- Do not hard-code sample results.
- Enforce the configured link capacity.
- Track every generated packet as delivered, dropped, or still queued/in service.
- Write and run automated tests.
- Run the application or at least perform an end-to-end smoke test if the environment allows it.
- Fix errors found during testing.
- Provide concise final instructions for installing dependencies, launching the dashboard, running tests, and understanding the metrics.
- If any feature cannot be completed, explain exactly what is missing rather than pretending it works.

Prioritize correctness, clarity, and a working MVP over decorative complexity.
