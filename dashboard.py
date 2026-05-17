"""Etkilesimli Streamlit dashboard — 3 sekme, sade matplotlib.

Calistirma:
    streamlit run dashboard.py

3 sekme:
    1. Senaryo Calistir   — bir kontrolcu icin kosum + KPI + grafik
    2. 3 Kontrolcu        — Faz 4 karsilastirma PNG/CSV/findings
    3. Kavsak Gorseli     — statik 4-yollu kavsak diyagrami
"""

from __future__ import annotations

import sys
from pathlib import Path

# src/ dizinini sys.path'e ekle ki "streamlit run dashboard.py" calissin
_SRC = Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from intersection_sim.controllers.adaptive import adaptive_controller  # noqa: E402
from intersection_sim.controllers.fixed import fixed_controller  # noqa: E402
from intersection_sim.controllers.preemptive import preemptive_controller  # noqa: E402
from intersection_sim.dashboard_helpers import (  # noqa: E402
    build_intersection_diagram,
    prepare_direction_wait_df,
    prepare_queue_timeseries,
    prepare_vehicle_type_counts,
)
from intersection_sim.domain.config import SimConfig  # noqa: E402
from intersection_sim.simulation.runner import run_with_controller  # noqa: E402

# Matplotlib tema
plt.rcParams["font.family"] = "DejaVu Sans"

# ---------- Page setup -------------------------------------------------------

st.set_page_config(
    page_title="Kavsak Trafik Isigi Simulasyonu",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🚦 Kavsak Trafik Isigi Simulasyonu")
st.caption(
    "SimPy + 4 yon + 3 kontrolcu (Sabit / Adaptif / Acil Oncelikli) — "
    "Faz 5 etkilesimli dashboard"
)


# ---------- Kontrolcu secici ------------------------------------------------

_CONTROLLERS = {
    "Sabit Zamanli": ("fixed", fixed_controller),
    "Adaptif": ("adaptive", adaptive_controller),
    "Acil Oncelikli": ("preemptive", preemptive_controller),
}


# ---------- Sidebar ---------------------------------------------------------

with st.sidebar:
    st.header("Senaryo")
    controller_label = st.selectbox(
        "Kontrolcu",
        list(_CONTROLLERS.keys()),
        help="3 kontrolcuden hangisi: Sabit / Adaptif / Acil Oncelikli",
    )
    duration_hours = st.slider("Sure (saat)", 1, 8, 4)
    seed = st.number_input("Seed", min_value=0, max_value=10_000, value=42, step=1)

    st.divider()
    run_btn = st.button("▶ Calistir", type="primary", use_container_width=True)

# Calistir butonuna basildiginda kosumu yap ve session'a koy.
if run_btn:
    name, controller = _CONTROLLERS[controller_label]
    config = SimConfig(
        seed=int(seed),
        horizon_seconds=float(duration_hours) * 3600.0,
    )
    with st.spinner(f"Kosturuluyor: {controller_label} ({duration_hours} saat, seed={seed}) ..."):
        intersection = run_with_controller(config, controller)
        report = intersection.metrics.build_report(config.horizon_seconds)
        st.session_state["current_run"] = {
            "intersection": intersection,
            "report": report,
            "controller_label": controller_label,
            "controller_name": name,
            "duration_hours": duration_hours,
            "seed": int(seed),
        }


# ---------- Tabs ------------------------------------------------------------

tab_run, tab_compare, tab_diagram = st.tabs(
    ["📊 Senaryo Calistir", "📈 3 Kontrolcu Karsilastirma", "🚦 Kavsak Gorseli"],
)


# ===== Tab 1 — Senaryo Calistir ===========================================

with tab_run:
    if "current_run" not in st.session_state:
        st.info(
            "⬅ Sol panelden kontrolcu sec, sure ve seed ayarla, **Calistir**'a bas."
        )
    else:
        run = st.session_state["current_run"]
        intersection = run["intersection"]
        report = run["report"]

        st.subheader(f"Senaryo: `{run['controller_label']}` · seed={run['seed']} · "
                     f"{run['duration_hours']} saat")

        # 4 KPI metric kart
        cols = st.columns(4)
        with cols[0]:
            mean_w = report.mean_wait_time_s
            st.metric("Ortalama bekleme", f"{mean_w:.2f} sn" if mean_w else "n/a")
        with cols[1]:
            em_w = report.mean_wait_by_type_s.get("emergency")
            st.metric("Acil arac beklemesi", f"{em_w:.2f} sn" if em_w else "n/a")
        with cols[2]:
            st.metric("Throughput", f"{report.throughput_per_hour:.1f} arac/sa")
        with cols[3]:
            st.metric("Preemption sayisi", str(report.preemption_count))

        st.divider()

        # 2 grafik yan yana: zaman serisi + yon bazli bekleme
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Kuyruk uzunlugu — zaman serisi (4 yon)**")
            snap_df = intersection.metrics.snapshots_dataframe()
            ts_df = prepare_queue_timeseries(snap_df)
            if not ts_df.empty:
                fig, ax = plt.subplots(figsize=(7, 4))
                for d_value, group in ts_df.groupby("direction"):
                    ax.plot(group["sim_time_s"] / 60.0, group["queue_length"],
                            label=d_value, linewidth=1.4)
                ax.set_xlabel("Sim-zaman (dk)")
                ax.set_ylabel("Kuyruktaki arac")
                ax.legend(title="Yon", fontsize=9)
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        with col_right:
            st.markdown("**Yon bazli ortalama bekleme**")
            dir_df = prepare_direction_wait_df(report)
            if not dir_df.empty:
                fig, ax = plt.subplots(figsize=(7, 4))
                # NaN olabilir; 0 ile doldur ve uyar
                dir_df_plot = dir_df.fillna({"mean_wait_s": 0.0})
                bars = ax.bar(
                    dir_df_plot["direction_tr"],
                    dir_df_plot["mean_wait_s"],
                    color=["#3B82F6", "#F59E0B", "#10B981", "#EF4444"],
                    edgecolor="#1F2937", linewidth=0.8,
                )
                for bar, v in zip(bars, dir_df_plot["mean_wait_s"]):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                        f"{v:.1f}",
                        ha="center", va="bottom", fontsize=10, fontweight="bold",
                    )
                ax.set_ylabel("Ortalama bekleme (sn)")
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        st.divider()

        # Arac tipi pie chart
        st.markdown("**Arac tipi dagilimi**")
        counts = prepare_vehicle_type_counts(intersection.metrics)
        if counts["normal"] + counts["emergency"] > 0:
            fig, ax = plt.subplots(figsize=(5, 5))
            wedges, texts, autotexts = ax.pie(
                [counts["normal"], counts["emergency"]],
                labels=["Normal", "Acil"],
                colors=["#60A5FA", "#DC2626"],
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops={"edgecolor": "white", "linewidth": 2},
            )
            for t in autotexts:
                t.set_color("white")
                t.set_fontweight("bold")
            ax.set_aspect("equal")
            fig.tight_layout()
            # Pie chart icin daha dar bir sutun kullan
            pie_col, _ = st.columns([1, 2])
            with pie_col:
                st.pyplot(fig)
            plt.close(fig)


# ===== Tab 2 — 3 Kontrolcu Karsilastirma ==================================

with tab_compare:
    st.subheader("Faz 4 — 3 Kontrolcu Karsilastirma")
    st.caption("5 seed × 4 saat ortalamasi. Sayilar `results/comparison.csv`'den.")

    csv_path = Path("results/comparison.csv")
    if not csv_path.exists():
        st.warning(
            "`results/comparison.csv` bulunamadi. Once su komutu kosturun:  \n"
            "`python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4`"
        )
    else:
        df = pd.read_csv(csv_path)
        # Sunum icin onemli sutunlar
        display_cols = [
            "display_name_tr", "mean_wait_s_mean", "normal_wait_s_mean",
            "emergency_wait_s_mean", "throughput_per_hour_mean", "preemption_count_mean",
        ]
        st.dataframe(
            df[display_cols].rename(columns={
                "display_name_tr": "Kontrolcu",
                "mean_wait_s_mean": "Ort. bekleme (sn)",
                "normal_wait_s_mean": "Normal arac (sn)",
                "emergency_wait_s_mean": "Acil arac (sn)",
                "throughput_per_hour_mean": "Throughput (arac/sa)",
                "preemption_count_mean": "Preemption",
            }),
            use_container_width=True, hide_index=True,
        )

        # 3 PNG — tek sutunda alt alta (genis ekran kapasitesini kullan)
        for fname, caption in [
            ("comparison_avg_wait.png", "Ortalama Bekleme Suresi — 3 Kontrolcu"),
            ("comparison_emergency_wait.png", "★ Acil Arac Bekleme Suresi (Ana Sunum Kozu)"),
            ("comparison_throughput.png", "Throughput — Kontrolculer Arasinda Yakin"),
        ]:
            p = Path("results") / fname
            if p.exists():
                st.image(str(p), caption=caption, use_container_width=True)

    st.divider()
    findings = Path("docs/scenario-findings.md")
    if findings.exists():
        st.subheader("📋 Bulgular ozeti")
        st.markdown(findings.read_text())
    else:
        st.info("`docs/scenario-findings.md` bulunamadi.")


# ===== Tab 3 — Kavsak Gorseli =============================================

with tab_diagram:
    st.subheader("Kavsak Gorseli")

    if "current_run" not in st.session_state:
        st.info(
            "⬅ Once Sekme 1'den bir senaryo calistirin. Bu diyagram kosumun"
            " **son snapshot**'indaki kavsak durumunu gosterir."
        )
    else:
        run = st.session_state["current_run"]
        intersection = run["intersection"]
        snap_df = intersection.metrics.snapshots_dataframe()

        if snap_df.empty:
            st.warning("Snapshot verisi yok.")
        else:
            # Snapshot zaman secici
            n_snaps = len(snap_df)
            # Default: son snapshot
            idx = st.slider(
                "Snapshot zamani",
                0, n_snaps - 1, n_snaps - 1,
                help="Sim-zamani uzerinde gez. 0 = baslangic, son = bitis.",
            )
            row = snap_df.iloc[idx]

            # Kuyruk ve sinyal durumu o snapshot icin
            from intersection_sim.domain.direction import Direction as _Dir
            from intersection_sim.domain.signal import (  # noqa: N814
                LightState as _LS,
            )

            queue_lengths = {
                d: int(row[f"queue_{d.value}"]) for d in _Dir
            }

            # Snapshot'ta active_green kayitli — diger 3 yon kirmizi
            ag_value = row["active_green"]
            signals = {d: _LS.RED for d in _Dir}
            if pd.notna(ag_value):
                signals[_Dir(ag_value)] = _LS.GREEN

            sim_time_min = row["sim_time_s"] / 60.0
            title = f"Sim-zaman: {sim_time_min:.1f} dk · " \
                    f"{run['controller_label']}"
            fig = build_intersection_diagram(
                signals, queue_lengths, title=title,
            )

            diagram_col, info_col = st.columns([2, 1])
            with diagram_col:
                st.pyplot(fig)
                plt.close(fig)
            with info_col:
                st.markdown("**Yon durumlari**")
                green_dir = None
                for d in _Dir:
                    if signals[d] is _LS.GREEN:
                        green_dir = d
                        break

                if green_dir is not None:
                    st.markdown(f"🟢 **Yesil:** {green_dir.display_name_tr}")
                else:
                    st.markdown("⚪ Su an hicbir yon yesil degil "
                                "(sari veya tum-kirmizi buffer)")

                st.markdown("**Kuyruk uzunluklari**")
                for d in _Dir:
                    st.markdown(f"- {d.display_name_tr}: {queue_lengths[d]} arac")

                st.divider()
                st.caption(
                    "Bu diyagram bir 'fotograf' — slider'i kaydirarak"
                    " baska bir sim-zamanindaki kavsak durumunu gorebilirsin."
                )
