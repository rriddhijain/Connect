"""Streamlit Dashboard for Network Bandwidth Allocation Simulator."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.models import SimulationConfig, TrafficClass
from src.traffic import build_users_for_scenario, generate_packet_trace, SCENARIO_OFFERED_RATIOS
from src.simulator import NetworkSimulator
from src.policies.equal_share import EqualSharePolicy
from src.policies.priority import PrioritySchedulingPolicy
from src.policies.round_robin import RoundRobinPolicy
from src.metrics import compute_metrics
from src.export import export_comparison_dataframe, export_user_dataframe, export_config_json

# Set page configuration
st.set_page_config(
    page_title="Network Bandwidth Allocation Simulator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #38bdf8;
        margin-top: 4px;
    }
    .badge-sim {
        background-color: #0369a1;
        color: #f0f9ff;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Sidebar: Configuration & Simulation Controls
# ==========================================
with st.sidebar:
    st.title("🌐 Simulator Controls")
    st.caption("Shared Bottleneck Link QoS Lab")

    preset = st.selectbox(
        "Scenario Preset",
        options=["Moderate Load", "Light Load", "Heavy Congestion", "Mixed Traffic", "Custom"],
        index=0,
        help="Select a predefined network load condition or customize your own.",
    )

    col_bw, col_users = st.columns(2)
    with col_bw:
        bandwidth_mbps = st.slider("Link Capacity (Mbps)", min_value=5.0, max_value=100.0, value=20.0, step=5.0)
    with col_users:
        num_users = st.slider("Synthetic Users", min_value=2, max_value=30, value=10, step=1)

    col_dur, col_buf = st.columns(2)
    with col_dur:
        duration_s = st.slider("Duration (seconds)", min_value=5, max_value=120, value=60, step=5)
    with col_buf:
        max_queue = st.slider("Queue Limit (pkts)", min_value=10, max_value=200, value=50, step=10)

    with st.expander("⚙️ Advanced Parameters"):
        seed = st.number_input("Random Seed (Reproducibility)", min_value=0, max_value=999999, value=42, step=1)
        time_step = st.select_slider("Time Step (dt in s)", options=[0.005, 0.01, 0.02, 0.05], value=0.01)
        rr_quantum = st.slider("Round-Robin Byte Quantum", min_value=500, max_value=3000, value=1500, step=100)

        traffic_mix = {
            TrafficClass.VOICE.value: 0.25,
            TrafficClass.VIDEO_STREAM.value: 0.25,
            TrafficClass.WEB.value: 0.25,
            TrafficClass.DOWNLOAD.value: 0.25,
        }

        if preset == "Custom":
            st.markdown("**Custom Traffic Distribution**")
            w_voice = st.slider("Voice / Video Call (%)", 0, 100, 25)
            w_video = st.slider("Online Video (%)", 0, 100, 25)
            w_web = st.slider("Web Browsing (%)", 0, 100, 25)
            w_down = st.slider("File Download (%)", 0, 100, 25)
            total_w = max(1, w_voice + w_video + w_web + w_down)
            traffic_mix = {
                TrafficClass.VOICE.value: w_voice / total_w,
                TrafficClass.VIDEO_STREAM.value: w_video / total_w,
                TrafficClass.WEB.value: w_web / total_w,
                TrafficClass.DOWNLOAD.value: w_down / total_w,
            }

    run_clicked = st.button("🚀 Run Simulation", type="primary", use_container_width=True)

# Helper function to run the complete simulation workflow
@st.cache_data(show_spinner="Simulating discrete-time traffic across policies...")
def run_all_simulations(config: SimulationConfig):
    users = build_users_for_scenario(config)
    all_packets, packets_by_step = generate_packet_trace(config, users)

    simulator = NetworkSimulator(config)

    policies = [
        EqualSharePolicy(),
        PrioritySchedulingPolicy(),
        RoundRobinPolicy(quantum_bytes=config.rr_quantum_bytes),
    ]

    results = []
    metrics = []

    for pol in policies:
        res = simulator.run_policy(pol, users, packets_by_step)
        met = compute_metrics(res)
        results.append(res)
        metrics.append(met)

    return config, users, all_packets, results, metrics


# Store in session state
config = SimulationConfig(
    bandwidth_mbps=float(bandwidth_mbps),
    num_users=int(num_users),
    duration_seconds=float(duration_s),
    time_step_seconds=float(time_step),
    max_queue_packets=int(max_queue),
    seed=int(seed),
    scenario_name=preset,
    traffic_mix=traffic_mix,
    rr_quantum_bytes=int(rr_quantum),
)

if "sim_data" not in st.session_state or run_clicked:
    st.session_state.sim_data = run_all_simulations(config)

sim_config, sim_users, sim_packets, sim_results, sim_metrics = st.session_state.sim_data

# ==========================================
# Main Header
# ==========================================
st.markdown("## 📊 Network Bandwidth Allocation Simulator")
st.markdown(
    '<span class="badge-sim">100% Synthetic Data</span>'
    '<span class="badge-sim">Single Shared Bottleneck Link</span>'
    f'<span class="badge-sim">Scenario: {sim_config.scenario_name}</span>'
    f'<span class="badge-sim">Capacity: {sim_config.bandwidth_mbps:.1f} Mbps</span>'
    f'<span class="badge-sim">Seed: {sim_config.seed}</span>',
    unsafe_allow_html=True,
)

st.info(
    "💡 **Educational Simulator Note**: This application runs entirely in software on synthetic packet arrival traces. "
    "All three resource-allocation policies evaluate the **exact same packet trace** with the same random seed, "
    "allowing rigorous, fair comparisons without physical router hardware or real network packet captures.",
    icon="ℹ️",
)

# Tabs for structured navigation
tab_comp, tab_qos, tab_users, tab_queues, tab_export = st.tabs([
    "📈 Policy Comparison",
    "🎯 QoS & Traffic Classes",
    "👥 Per-User Inspection",
    "📦 Queue & Conservation",
    "📥 Export & Viva Guide",
])

# ------------------------------------------
# TAB 1: Policy Comparison
# ------------------------------------------
with tab_comp:
    st.subheader("Key Performance Indicators (KPIs)")

    kpi_cols = st.columns(3)
    policy_colors = {
        "Equal Allocation": "#38bdf8",     # Cyan
        "Priority Scheduling": "#f43f5e", # Rose
        "Round-Robin": "#10b981",        # Emerald
    }

    for col, m in zip(kpi_cols, sim_metrics):
        with col:
            color = policy_colors.get(m.policy_name, "#38bdf8")
            st.markdown(f"""
            <div class="metric-card" style="border-top: 4px solid {color};">
                <div class="metric-title">{m.policy_name}</div>
                <div class="metric-value">{m.throughput_mbps:.2f} <span style="font-size: 1rem; color: #94a3b8;">Mbps</span></div>
                <div style="margin-top: 8px; font-size: 0.9rem;">
                    <div>• <b>Delivery Ratio:</b> {m.delivery_ratio_pct:.1f}%</div>
                    <div>• <b>Packet Loss:</b> {m.loss_ratio_pct:.1f}%</div>
                    <div>• <b>Mean Latency:</b> {f'{m.mean_latency_ms:.1f} ms' if m.mean_latency_ms is not None else 'N/A'}</div>
                    <div>• <b>P95 Latency:</b> {f'{m.p95_latency_ms:.1f} ms' if m.p95_latency_ms is not None else 'N/A'}</div>
                    <div>• <b>Utilization:</b> {m.utilization_pct:.1f}%</div>
                    <div>• <b>Jain's Fairness:</b> {m.jains_fairness_index:.4f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Detailed Comparison Table
    st.markdown("### Summary Comparison Table")
    df_comp = export_comparison_dataframe(sim_metrics)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    # Comparison Charts
    st.markdown("### Visual Comparison")
    c1, c2 = st.columns(2)

    with c1:
        # Throughput vs Link Capacity
        fig_thru = go.Figure()
        for m in sim_metrics:
            fig_thru.add_trace(go.Bar(
                x=[m.policy_name],
                y=[m.throughput_mbps],
                name=m.policy_name,
                marker_color=policy_colors.get(m.policy_name),
                text=[f"{m.throughput_mbps:.2f} Mbps"],
                textposition="auto",
            ))
        fig_thru.add_hline(
            y=sim_config.bandwidth_mbps,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Link Capacity ({sim_config.bandwidth_mbps} Mbps)",
        )
        fig_thru.update_layout(
            title="Delivered Throughput vs Link Capacity",
            yaxis_title="Throughput (Mbps)",
            showlegend=False,
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_thru, use_container_width=True)

    with c2:
        # Delivery vs Loss Ratio
        p_names = [m.policy_name for m in sim_metrics]
        p_dels = [m.delivery_ratio_pct for m in sim_metrics]
        p_loss = [m.loss_ratio_pct for m in sim_metrics]

        fig_dl = go.Figure(data=[
            go.Bar(name="Delivered (%)", x=p_names, y=p_dels, marker_color="#10b981"),
            go.Bar(name="Dropped (%)", x=p_names, y=p_loss, marker_color="#ef4444"),
        ])
        fig_dl.update_layout(
            barmode="stack",
            title="Packet Delivery vs Drop Ratios",
            yaxis_title="Percentage (%)",
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_dl, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        # Mean & P95 Latency
        fig_lat = go.Figure(data=[
            go.Bar(
                name="Mean Latency",
                x=p_names,
                y=[m.mean_latency_ms or 0 for m in sim_metrics],
                marker_color="#6366f1",
            ),
            go.Bar(
                name="95th Percentile Latency",
                x=p_names,
                y=[m.p95_latency_ms or 0 for m in sim_metrics],
                marker_color="#ec4899",
            ),
        ])
        fig_lat.update_layout(
            barmode="group",
            title="Latency Comparison (Lower is Better)",
            yaxis_title="Latency (ms)",
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_lat, use_container_width=True)

    with c4:
        # Jain's Fairness Index
        fig_fair = go.Figure()
        for m in sim_metrics:
            fig_fair.add_trace(go.Bar(
                x=[m.policy_name],
                y=[m.jains_fairness_index],
                marker_color=policy_colors.get(m.policy_name),
                text=[f"{m.jains_fairness_index:.4f}"],
                textposition="auto",
            ))
        fig_fair.update_layout(
            title="Jain's Fairness Index (1.0 = Perfectly Fair)",
            yaxis=dict(range=[0, 1.05], title="Fairness Index"),
            showlegend=False,
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_fair, use_container_width=True)

    # Time-series graphs
    st.markdown("### Dynamic Time-Series Behavior")
    ts_tabs = st.tabs(["Throughput Dynamics", "Queue Occupancy Dynamics"])

    with ts_tabs[0]:
        fig_ts_thru = go.Figure()
        for res in sim_results:
            df_snap = pd.DataFrame([
                {"time": s.time_seconds, "mbps": s.instant_throughput_mbps}
                for s in res.snapshots
            ])
            # Rolling window average for smooth visualization
            df_snap["smoothed"] = df_snap["mbps"].rolling(window=10, min_periods=1).mean()
            fig_ts_thru.add_trace(go.Scatter(
                x=df_snap["time"],
                y=df_snap["smoothed"],
                mode="lines",
                name=res.policy_name,
                line=dict(color=policy_colors.get(res.policy_name), width=2),
            ))
        fig_ts_thru.add_hline(
            y=sim_config.bandwidth_mbps,
            line_dash="dot",
            line_color="orange",
            annotation_text="Link Capacity",
        )
        fig_ts_thru.update_layout(
            title="Instantaneous Throughput Over Time (Smoothed)",
            xaxis_title="Simulation Time (s)",
            yaxis_title="Throughput (Mbps)",
            height=380,
        )
        st.plotly_chart(fig_ts_thru, use_container_width=True)

    with ts_tabs[1]:
        fig_ts_q = go.Figure()
        for res in sim_results:
            df_snap = pd.DataFrame([
                {"time": s.time_seconds, "q_pkts": s.total_queued_packets}
                for s in res.snapshots
            ])
            fig_ts_q.add_trace(go.Scatter(
                x=df_snap["time"],
                y=df_snap["q_pkts"],
                mode="lines",
                name=res.policy_name,
                line=dict(color=policy_colors.get(res.policy_name), width=2),
            ))
        fig_ts_q.update_layout(
            title="Aggregate Queue Depth Over Time",
            xaxis_title="Simulation Time (s)",
            yaxis_title="Queued Packets",
            height=380,
        )
        st.plotly_chart(fig_ts_q, use_container_width=True)

# ------------------------------------------
# TAB 2: QoS & Traffic Classes
# ------------------------------------------
with tab_qos:
    st.subheader("Traffic Class Differentiation & Quality of Service (QoS)")
    st.markdown("""
    This section exposes how each policy treats different application traffic classes:
    - **Voice / Video Call (Priority 1 / High)**: Latency-sensitive small packets.
    - **Online Lecture / Video (Priority 1 / High)**: Real-time media streaming.
    - **Web Browsing (Priority 2 / Medium)**: Interactive bursty web traffic.
    - **File Download (Priority 3 / Low)**: Bulk background data transfer.
    """)

    selected_pol_qos = st.selectbox(
        "Select Policy to Inspect Traffic Classes",
        options=[m.policy_name for m in sim_metrics],
        key="qos_policy_sel",
    )
    chosen_metrics = next(m for m in sim_metrics if m.policy_name == selected_pol_qos)

    # Class breakdown table
    df_classes = pd.DataFrame.from_dict(chosen_metrics.class_metrics, orient="index").reset_index()
    df_classes.rename(columns={"index": "Traffic Class"}, inplace=True)
    st.dataframe(df_classes, use_container_width=True, hide_index=True)

    # Comparison across all 3 policies for each class
    st.markdown("#### Delivery Ratio Across Classes for Each Policy")
    class_rows = []
    for m in sim_metrics:
        for c_name, c_data in m.class_metrics.items():
            class_rows.append({
                "Policy": m.policy_name,
                "Traffic Class": c_name,
                "Delivery Ratio (%)": c_data["Delivery Ratio (%)"],
                "Loss Ratio (%)": c_data["Loss Ratio (%)"],
                "Mean Latency (ms)": c_data["Mean Latency (ms)"] or 0,
            })
    df_all_classes = pd.DataFrame(class_rows)

    fig_qos_del = px.bar(
        df_all_classes,
        x="Traffic Class",
        y="Delivery Ratio (%)",
        color="Policy",
        barmode="group",
        color_discrete_map=policy_colors,
        title="Delivery Ratio (%) by Traffic Class",
    )
    st.plotly_chart(fig_qos_del, use_container_width=True)

    fig_qos_lat = px.bar(
        df_all_classes,
        x="Traffic Class",
        y="Mean Latency (ms)",
        color="Policy",
        barmode="group",
        color_discrete_map=policy_colors,
        title="Mean Latency (ms) by Traffic Class (Lower is Better)",
    )
    st.plotly_chart(fig_qos_lat, use_container_width=True)

# ------------------------------------------
# TAB 3: Per-User Inspection
# ------------------------------------------
with tab_users:
    st.subheader("Synthetic User Inspection")
    u_names = [f"User {u.user_id}: {u.name} [{u.traffic_class.value}]" for u in sim_users]
    sel_u_idx = st.selectbox("Select User to Inspect", range(len(u_names)), format_func=lambda i: u_names[i])
    selected_u = sim_users[sel_u_idx]

    user_comp_rows = []
    for m in sim_metrics:
        u_m = next((u for u in m.user_metrics if u["User ID"] == selected_u.user_id), None)
        if u_m:
            user_comp_rows.append({
                "Policy": m.policy_name,
                "Traffic Class": u_m["Traffic Class"],
                "Throughput (Mbps)": u_m["Throughput (Mbps)"],
                "Delivery Ratio (%)": u_m["Delivery Ratio (%)"],
                "Loss Ratio (%)": u_m["Loss Ratio (%)"],
                "Mean Latency (ms)": u_m["Mean Latency (ms)"] if u_m["Mean Latency (ms)"] is not None else "N/A",
                "P95 Latency (ms)": u_m["P95 Latency (ms)"] if u_m["P95 Latency (ms)"] is not None else "N/A",
                "Generated": u_m["Generated Packets"],
                "Delivered": u_m["Delivered Packets"],
                "Dropped": u_m["Dropped Packets"],
                "Remaining": u_m["Remaining Packets"],
            })

    df_selected_u = pd.DataFrame(user_comp_rows)
    st.dataframe(df_selected_u, use_container_width=True, hide_index=True)

    st.markdown("#### Complete User Roster (Current Run)")
    all_user_df = export_user_dataframe(sim_metrics)
    st.dataframe(all_user_df, use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 4: Queue & Conservation
# ------------------------------------------
with tab_queues:
    st.subheader("Packet Accounting & Conservation Invariant")
    st.markdown("""
    A fundamental network simulation integrity requirement is that:
    $$\\text{Generated Packets} = \\text{Delivered Packets} + \\text{Dropped Packets} + \\text{Remaining in Queue}$$
    No packets may appear or disappear unrecorded.
    """)

    accounting_rows = []
    for m in sim_metrics:
        is_exact = (m.total_generated == (m.total_delivered + m.total_dropped + m.total_remaining))
        accounting_rows.append({
            "Policy": m.policy_name,
            "Total Generated": m.total_generated,
            "Delivered": m.total_delivered,
            "Dropped (Overflow)": m.total_dropped,
            "Remaining in Queue": m.total_remaining,
            "Sum (Del + Drop + Rem)": m.total_delivered + m.total_dropped + m.total_remaining,
            "Invariant Satisfied?": "✅ YES" if is_exact else "❌ MISMATCH",
        })
    st.dataframe(pd.DataFrame(accounting_rows), use_container_width=True, hide_index=True)

    # Queue Overflow Analysis
    st.markdown("#### Drop Analysis & Buffer Overflow")
    st.write(
        f"Each user was allocated a FIFO buffer limit of **{sim_config.max_queue_packets} packets**. "
        "When arriving traffic exceeds transmission capacity, buffers fill up and tail-drops occur."
    )

# ------------------------------------------
# TAB 5: Export & Viva Guide
# ------------------------------------------
with tab_export:
    st.subheader("Data Export")
    col_exp1, col_exp2, col_exp3 = st.columns(3)

    csv_comp = export_comparison_dataframe(sim_metrics).to_csv(index=False).encode("utf-8")
    with col_exp1:
        st.download_button(
            "📥 Download Policy Summary (CSV)",
            data=csv_comp,
            file_name=f"network_policy_summary_seed{sim_config.seed}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    csv_users = export_user_dataframe(sim_metrics).to_csv(index=False).encode("utf-8")
    with col_exp2:
        st.download_button(
            "📥 Download Per-User Data (CSV)",
            data=csv_users,
            file_name=f"network_user_metrics_seed{sim_config.seed}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    json_cfg = export_config_json(sim_config).encode("utf-8")
    with col_exp3:
        st.download_button(
            "📥 Download Config Metadata (JSON)",
            data=json_cfg,
            file_name=f"sim_config_seed{sim_config.seed}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    st.subheader("🎓 Student Viva / Oral Exam Quick Reference")

    with st.expander("❓ 1. What is the fundamental difference between Equal Share and Round-Robin?"):
        st.markdown("""
        - **Equal Share (Fair-Share Service)** allocates an equal **bandwidth budget** (bytes/bits per second) among all active users in each scheduling interval.
        - **Round-Robin** allocates **transmission opportunities** (turns to dequeue 1 packet or a quantum) by rotating cyclically through active user queues.
        - *Key difference*: If packet sizes vary greatly (e.g. 200B voice vs 1400B download), simple packet round-robin gives equal turns, which favors users with large packets in terms of throughput. Equal allocation equalizes byte transmission capacity directly.
        """)

    with st.expander("❓ 2. Why does Strict Priority cause starvation under heavy congestion?"):
        st.markdown("""
        - **Strict Priority** always serves High-priority queues first whenever packets are present.
        - Under heavy congestion (offered load > 100%), if high-priority voice/video streams generate enough traffic to fill the link capacity, Low-priority download queues never get served. Their buffers overflow and they suffer high loss and starvation.
        - In real-world networks, this is mitigated by combining priority with rate limiters (e.g. Token Bucket / Weighted Fair Queuing).
        """)

    with st.expander("❓ 3. How is Jain's Fairness Index calculated and interpreted?"):
        st.markdown("""
        - Formula:
          $$J(x_1, x_2, \\dots, x_n) = \\frac{\\left(\\sum_{i=1}^n x_i\\right)^2}{n \\cdot \\sum_{i=1}^n x_i^2}$$
        - **Range**: From $1/n$ (worst case: one user monopolizes all bandwidth while all other $n-1$ users receive zero) to $1.0$ (perfect fairness: all users receive identical throughput).
        - It is bounded, continuous, scale-independent, and penalizes starvation severely.
        """)

    with st.expander("❓ 4. Why is discrete-time simulation appropriate here?"):
        st.markdown("""
        - In discrete-time simulation, time advances in fixed increments ($dt = 10\\text{ ms}$).
        - In each interval, the bottleneck link's physical transmission limit is strictly enforced:
          $$\\text{Budget (bits)} = \\text{Capacity (bps)} \\times dt$$
        - This guarantees that the simulator never transmits more bits than the physical line speed allows.
        """)
