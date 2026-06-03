"""Etkileşimli Streamlit dashboard — 7 sekme, sade matplotlib.

Çalıştırma:
    streamlit run dashboard.py

7 sekme:
    1. Senaryo Çalıştır       — bir kontrolcü için koşum + KPI + grafik
    2. 4 Kontrolcü Karşılaştır — comparison.csv tablosu + PNG'ler
    3. Dağılım & Çevresel     — histogram, boxplot, CO2/yakıt
    4. Saatlik Heatmap        — saat × yön bekleme matrix
    5. Burst Senaryosu        — ani talep altında 4 kontrolcü
    6. Sensitivity α Sweep    — predictive α parametre süpürmesi
    7. Kavşak Görseli         — statik 4-yollu kavşak diyagrami
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
from intersection_sim.controllers.predictive import predictive_controller  # noqa: E402
from intersection_sim.controllers.preemptive import preemptive_controller  # noqa: E402
from intersection_sim.dashboard_helpers import (  # noqa: E402
    build_intersection_diagram,
    predictive_alpha_sweep,
    prepare_direction_wait_df,
    prepare_hourly_heatmap,
    prepare_queue_timeseries,
    prepare_vehicle_type_counts,
    prepare_wait_distribution,
)
from intersection_sim.domain.config import (  # noqa: E402
    ArrivalProfile,
    BurstEvent,
    SimConfig,
)
from intersection_sim.domain.direction import Direction  # noqa: E402
from intersection_sim.simulation.runner import run_with_controller  # noqa: E402

# Matplotlib tema
plt.rcParams["font.family"] = "DejaVu Sans"

# ---------- Page setup -------------------------------------------------------

st.set_page_config(
    page_title="Kavşak Trafik Işığı Simülasyonu",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("Kavşak Trafik Işığı Simülasyonu")
st.caption(
    "SimPy + 4 yön + 4 kontrolcü (Sabit / Adaptif / Tahmine Dayalı / Acil "
    "Öncelikli) — final genişletmesi: percentile, fairness, CO2, saatlik heatmap"
)


# ---------- Kontrolcü secici ------------------------------------------------

_CONTROLLERS = {
    "Sabit Zamanlı": ("fixed", fixed_controller),
    "Adaptif": ("adaptive", adaptive_controller),
    "Tahmine Dayalı": ("predictive", predictive_controller),
    "Acil Öncelikli": ("preemptive", preemptive_controller),
}

# Trafik profili preset'leri (base/peak rate çarpanı)
_TRAFFIC_PROFILES = {
    "Sakin (-30%)": 0.7,
    "Normal (default)": 1.0,
    "Yoğun (+50%)": 1.5,
    "Çok Yoğun (+100%)": 2.0,
}

_DIR_LABELS = {
    "Kuzey": Direction.NORTH,
    "Güney": Direction.SOUTH,
    "Doğu": Direction.EAST,
    "Batı": Direction.WEST,
}


# ---------- Sidebar ---------------------------------------------------------

with st.sidebar:
    st.header("Senaryo")
    controller_label = st.selectbox(
        "Kontrolcü",
        list(_CONTROLLERS.keys()),
        help="4 kontrolcüden hangisi: Sabit / Adaptif / Tahmine Dayalı / Acil Öncelikli",
    )
    duration_hours = st.slider("Süre (saat)", 1, 8, 4)
    seed = st.number_input(
        "Seed", min_value=0, max_value=10_000, value=42, step=1,
    )

    with st.expander("Gelişmiş ayarlar", expanded=False):
        traffic_profile = st.selectbox(
            "Trafik profili",
            list(_TRAFFIC_PROFILES.keys()),
            index=1,
            help="Tüm yönlerin geliş hızını çarpan ile ölçekler.",
        )
        emergency_pct = st.slider(
            "Acil araç oranı (%)",
            min_value=0, max_value=15, value=5, step=1,
            help="Gelen araçların kaç %'si acil (ambulans/itfaiye/polis).",
        )

        st.markdown("**Burst (ani yığın) olayı**")
        burst_enabled = st.checkbox(
            "Burst senaryosunu etkinleştir",
            value=False,
            help="Belirli zamanda + yönde ek talep yığınlaması ekler.",
        )
        if burst_enabled:
            burst_dir_label = st.selectbox(
                "Burst yönü", list(_DIR_LABELS.keys()), index=0,
            )
            burst_start_min = st.slider(
                "Başlangıç (dakika)", 0, 240, 30, step=5,
            )
            burst_duration_min = st.slider(
                "Süre (dakika)", 5, 90, 30, step=5,
            )
            burst_extra_rate = st.slider(
                "Ek hız (araç/dk)", 5, 40, 20, step=1,
                help="Base/peak hızının üzerine eklenir.",
            )

    st.divider()
    run_btn = st.button("Çalıştır", type="primary", use_container_width=True)


def _build_arrival_profile() -> ArrivalProfile:
    """Sidebar değerlerinden ArrivalProfile üretir."""
    mult = _TRAFFIC_PROFILES[traffic_profile]
    base = {d: 0.4 * mult if d in (Direction.NORTH, Direction.SOUTH)
            else 0.3 * mult for d in Direction}
    peak = {Direction.NORTH: 0.8 * mult, Direction.SOUTH: 0.7 * mult,
            Direction.EAST: 0.6 * mult, Direction.WEST: 0.6 * mult}
    events: list[BurstEvent] = []
    if burst_enabled:
        events.append(BurstEvent(
            start_time_s=float(burst_start_min) * 60.0,
            duration_s=float(burst_duration_min) * 60.0,
            direction=_DIR_LABELS[burst_dir_label],
            extra_rate_per_min=float(burst_extra_rate),
        ))
    return ArrivalProfile(
        base_rate_per_min=base,
        peak_rate_per_min=peak,
        emergency_probability=emergency_pct / 100.0,
        burst_events=events,
    )


# Çalıştır butonuna basildiginda kosumu yap ve session'a koy.
if run_btn:
    name, controller = _CONTROLLERS[controller_label]
    arrivals = _build_arrival_profile()
    config = SimConfig(
        seed=int(seed),
        horizon_seconds=float(duration_hours) * 3600.0,
        arrivals=arrivals,
    )
    extras: list[str] = []
    if traffic_profile != "Normal (default)":
        extras.append(f"trafik: {traffic_profile}")
    if emergency_pct != 5:
        extras.append(f"acil: %{emergency_pct}")
    if burst_enabled:
        extras.append(
            f"burst: {burst_dir_label} {burst_start_min}-"
            f"{burst_start_min + burst_duration_min} dk +{burst_extra_rate} araç/dk",
        )
    spin = (f"Koşturuluyor: {controller_label} ({duration_hours} saat, "
            f"seed={seed})")
    if extras:
        spin += " · " + " · ".join(extras)
    with st.spinner(spin + " ..."):
        intersection = run_with_controller(config, controller)
        report = intersection.metrics.build_report(config.horizon_seconds)
        st.session_state["current_run"] = {
            "intersection": intersection,
            "report": report,
            "controller_label": controller_label,
            "controller_name": name,
            "duration_hours": duration_hours,
            "seed": int(seed),
            "scenario_extras": extras,
        }


# ---------- Tabs ------------------------------------------------------------

(tab_run, tab_compare, tab_dist, tab_heatmap, tab_burst,
 tab_sens, tab_diagram) = st.tabs(
    [
        "Senaryo Çalıştır",
        "4 Kontrolcü Karşılaştırma",
        "Dağılım & Çevresel",
        "Saatlik Heatmap",
        "Burst Senaryosu",
        "Sensitivity α Sweep",
        "Kavşak Görseli",
    ],
)


# ===== Tab 1 — Senaryo Çalıştır ===========================================

with tab_run:
    if "current_run" not in st.session_state:
        st.info(
            "Sol panelden kontrolcü seç, süre ve seed ayarla, **Çalıştır**'a bas."
        )
    else:
        run = st.session_state["current_run"]
        intersection = run["intersection"]
        report = run["report"]

        st.subheader(
            f"Senaryo: `{run['controller_label']}` · seed={run['seed']} · "
            f"{run['duration_hours']} saat",
        )
        extras = run.get("scenario_extras") or []
        if extras:
            st.caption(" · ".join(extras))

        # 4 KPI metric kart
        cols = st.columns(4)
        with cols[0]:
            mean_w = report.mean_wait_time_s
            st.metric("Ortalama bekleme", f"{mean_w:.2f} sn" if mean_w else "n/a")
        with cols[1]:
            em_w = report.mean_wait_by_type_s.get("emergency")
            st.metric("Acil araç beklemesi", f"{em_w:.2f} sn" if em_w else "n/a")
        with cols[2]:
            st.metric("Throughput", f"{report.throughput_per_hour:.1f} araç/sa")
        with cols[3]:
            st.metric("Preemption sayısı", str(report.preemption_count))

        # ---- Faz Final: 2. KPI satırı (percentile + fairness + CO2 + idle) ---
        cols2 = st.columns(4)
        with cols2[0]:
            p95 = report.wait_percentiles_s.get("p95")
            st.metric(
                "p95 bekleme",
                f"{p95:.2f} sn" if p95 is not None else "n/a",
                help="En kötü %5'lik dilimin bekleme süresi — "
                     "ortalama yanıltıcıdır, p95 'gerçek deneyim'i gösterir.",
            )
        with cols2[1]:
            fi = report.fairness_index
            st.metric(
                "Fairness (Jain)",
                f"{fi:.3f}" if fi is not None else "n/a",
                help="1.0 = yönler arasında mükemmel eşit dağılım; "
                     "0.25 = tek yön avantajlı (4 yön için min).",
            )
        with cols2[2]:
            st.metric(
                "CO2 (tahmini)",
                f"{report.co2_grams_proxy:.0f} g",
                help="Idle motorlardan tahmini CO2 emisyonu "
                     "(0.6 L/saat × 2310 g/L benzin proxy).",
            )
        with cols2[3]:
            idle_min = report.total_idle_seconds / 60.0
            st.metric(
                "Toplam idle",
                f"{idle_min:.1f} dk",
                help="Tüm araçların kumulatif bekleme süresi (motor çalışırken).",
            )

        st.divider()

        # 2 grafik yan yana: zaman serisi + yön bazli bekleme
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**Kuyruk uzunluğu — zaman serisi (4 yön)**")
            snap_df = intersection.metrics.snapshots_dataframe()
            ts_df = prepare_queue_timeseries(snap_df)
            if not ts_df.empty:
                fig, ax = plt.subplots(figsize=(7, 4))
                for d_value, group in ts_df.groupby("direction"):
                    ax.plot(group["sim_time_s"] / 60.0, group["queue_length"],
                            label=d_value, linewidth=1.4)
                ax.set_xlabel("Sim-zaman (dk)")
                ax.set_ylabel("Kuyruktaki araç")
                ax.legend(title="Yön", fontsize=9)
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        with col_right:
            st.markdown("**Yön bazlı ortalama bekleme**")
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

        # Araç tipi pie chart
        st.markdown("**Araç tipi dağılımı**")
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
            # Pie chart için daha dar bir sutun kullan
            pie_col, _ = st.columns([1, 2])
            with pie_col:
                st.pyplot(fig)
            plt.close(fig)


# ===== Tab 2 — 3 Kontrolcü Karşılaştırma ==================================

with tab_compare:
    st.subheader("4 Kontrolcü Karşılaştırma")
    st.caption("5 seed × 4 saat ortalaması. Sayılar `results/comparison.csv`'den.")

    csv_path = Path("results/comparison.csv")
    if not csv_path.exists():
        st.warning(
            "`results/comparison.csv` bulunamadı. Önce şu komutu koşturun:  \n"
            "`python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4`"
        )
    else:
        df = pd.read_csv(csv_path)
        # Sunum için önemli sutunlar (Faz Final genişletilmiş)
        display_cols = [
            "display_name_tr", "mean_wait_s_mean", "p95_wait_s_mean",
            "emergency_wait_s_mean", "throughput_per_hour_mean",
            "fairness_index_mean", "co2_grams_proxy_mean",
            "preemption_count_mean",
        ]
        # Dosyada eski versiyonlardan kalan kolon eksik olabilir; varsa al
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[display_cols].rename(columns={
                "display_name_tr": "Kontrolcü",
                "mean_wait_s_mean": "Ort. bekleme (sn)",
                "p95_wait_s_mean": "p95 (sn)",
                "emergency_wait_s_mean": "Acil araç (sn)",
                "throughput_per_hour_mean": "Throughput (araç/sa)",
                "fairness_index_mean": "Fairness",
                "co2_grams_proxy_mean": "CO2 (g)",
                "preemption_count_mean": "Preemption",
            }),
            use_container_width=True, hide_index=True,
        )

        # 3 PNG — tek sutunda alt alta (genis ekran kapasitesini kullan)
        for fname, caption in [
            ("comparison_avg_wait.png", "Ortalama Bekleme Süresi — 3 Kontrolcü"),
            ("comparison_emergency_wait.png", "Acil Araç Bekleme Süresi (Ana Sunum Kozu)"),
            ("comparison_throughput.png", "Throughput — Kontrolcüler Arasında Yakın"),
        ]:
            p = Path("results") / fname
            if p.exists():
                st.image(str(p), caption=caption, use_container_width=True)

    st.divider()
    findings = Path("docs/scenario-findings.md")
    if findings.exists():
        st.subheader("Bulgular özeti")
        st.markdown(findings.read_text())
    else:
        st.info("`docs/scenario-findings.md` bulunamadı.")


# ===== Tab 3 — Dağılım & Çevresel =========================================

with tab_dist:
    st.subheader("Bekleme Dağılımı ve Çevresel Etki")
    if "current_run" not in st.session_state:
        st.info(
            "Önce Sekme 1'den bir senaryo çalıştırın. Burada o "
            "koşumdaki bekleme dağılımı + CO2 / yakıt tahmini gösterilir."
        )
    else:
        run = st.session_state["current_run"]
        intersection = run["intersection"]
        report = run["report"]

        # ---- Percentile tablosu --------------------------------------------
        st.markdown("**Bekleme süresi percentile dilimleri**")
        pct_rows = []
        labels = [("Tümü", report.wait_percentiles_s),
                  ("Normal", report.wait_percentiles_normal_s),
                  ("Acil", report.wait_percentiles_emergency_s)]
        for label, pct_d in labels:
            row = {"Grup": label}
            for p in ("p50", "p75", "p90", "p95", "p99"):
                v = pct_d.get(p)
                row[p] = f"{v:.2f}" if v is not None else "n/a"
            pct_rows.append(row)
        st.dataframe(pd.DataFrame(pct_rows), hide_index=True,
                     use_container_width=True)

        st.divider()

        # ---- Histogram + boxplot -------------------------------------------
        dist = prepare_wait_distribution(intersection.metrics)
        if dist["overall"]:
            col_h, col_b = st.columns(2)
            with col_h:
                st.markdown("**Histogram — tüm araçlar vs acil**")
                fig, ax = plt.subplots(figsize=(7, 4))
                ax.hist(dist["normal"], bins=30, alpha=0.6,
                        color="#3B82F6", label="Normal", edgecolor="white")
                if dist["emergency"]:
                    ax.hist(dist["emergency"], bins=15, alpha=0.7,
                            color="#DC2626", label="Acil", edgecolor="white")
                ax.set_xlabel("Bekleme süresi (sn)")
                ax.set_ylabel("Araç sayısı")
                ax.legend()
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            with col_b:
                st.markdown("**Boxplot — yön bazlı dağılım**")
                fig, ax = plt.subplots(figsize=(7, 4))
                from intersection_sim.domain.direction import (
                    ALL_DIRECTIONS as _AD,
                )
                box_data = [dist["by_direction"][d.value] for d in _AD]
                labels_tr = [d.display_name_tr for d in _AD]
                ax.boxplot(box_data, labels=labels_tr, patch_artist=True,
                           boxprops=dict(facecolor="#A5B4FC", alpha=0.6))
                ax.set_ylabel("Bekleme süresi (sn)")
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

        st.divider()

        # ---- Çevresel metrik blok ------------------------------------------
        st.markdown("**Çevresel etki — idle motor tahmini**")
        env_cols = st.columns(4)
        with env_cols[0]:
            st.metric("Toplam idle",
                      f"{report.total_idle_seconds/60.0:.1f} dk")
        with env_cols[1]:
            st.metric("Tahmini yakıt",
                      f"{report.fuel_liters_proxy:.3f} L")
        with env_cols[2]:
            st.metric("Tahmini CO2",
                      f"{report.co2_grams_proxy:.0f} g")
        with env_cols[3]:
            # CO2 km karşılığı: ortalama otomobil ~120 g/km
            km_eq = report.co2_grams_proxy / 120.0
            st.metric("Karşılığı (km)",
                      f"{km_eq:.1f} km",
                      help="Otomobil 120 g CO2/km ile bu kadar km gidebilir.")
        st.caption(
            "Idle yakıt: 0.6 L/saat (literatür). CO2: 2310 g/L benzin "
            "(EPA). Bu sayılar gerçek ölçüm değil — kontrolcüler arası "
            "göreceli karşılaştırma için proxy."
        )


# ===== Tab 4 — Saatlik Heatmap ============================================

with tab_heatmap:
    st.subheader("Saatlik Bekleme Heatmap'i")
    if "current_run" not in st.session_state:
        st.info(
            "Önce Sekme 1'den bir senaryo çalıştırın. "
            "Saatlik × yön bekleme matrisini burada görürsünüz."
        )
    else:
        run = st.session_state["current_run"]
        report = run["report"]

        heat_df = prepare_hourly_heatmap(report)
        if heat_df.empty or report.horizon_seconds < 3600:
            st.warning(
                "Heatmap için en az 1 saatlik koşum lazım. "
                "Süreyi artırıp tekrar çalıştırın."
            )
        else:
            # Pivot: satir=yön, sutun=saat, deger=mean_wait_s
            pivot = heat_df.pivot(
                index="direction_tr", columns="hour", values="mean_wait_s",
            )
            # Sirayi ALL_DIRECTIONS ile uyumlu yap
            from intersection_sim.domain.direction import (
                ALL_DIRECTIONS as _AD2,
            )
            order = [d.display_name_tr for d in _AD2]
            pivot = pivot.reindex(order)

            col_heat, col_thru = st.columns([2, 1])
            with col_heat:
                st.markdown("**Yön × Saat ortalama bekleme (sn)**")
                fig, ax = plt.subplots(figsize=(8, 4))
                im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
                ax.set_yticks(range(len(pivot.index)))
                ax.set_yticklabels(pivot.index)
                ax.set_xticks(range(len(pivot.columns)))
                ax.set_xticklabels([f"Saat {h}" for h in pivot.columns])
                # Hücre içi değer
                for i in range(pivot.shape[0]):
                    for j in range(pivot.shape[1]):
                        v = pivot.values[i, j]
                        ax.text(j, i, f"{v:.1f}",
                                ha="center", va="center",
                                fontsize=9,
                                color="white" if v > pivot.values.max()/2
                                else "#1F2937")
                fig.colorbar(im, ax=ax, label="Bekleme (sn)")
                ax.set_xlabel("Simülasyon saati")
                ax.set_ylabel("Yön")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
            with col_thru:
                st.markdown("**Saatlik throughput**")
                fig, ax = plt.subplots(figsize=(5, 4))
                hours = list(range(len(report.hourly_throughput)))
                ax.bar(hours, report.hourly_throughput,
                       color="#3B82F6", edgecolor="#1F2937")
                for h, v in zip(hours, report.hourly_throughput):
                    ax.text(h, v + 1, f"{v:.0f}",
                            ha="center", va="bottom",
                            fontsize=10, fontweight="bold")
                ax.set_xticks(hours)
                ax.set_xticklabels([f"Saat {h}" for h in hours])
                ax.set_ylabel("Geçen araç sayısı")
                ax.grid(axis="y", linestyle="--", alpha=0.3)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            st.caption(
                "Sıcaklık ne kadar koyu → o saatte o yönde bekleme o "
                "kadar yüksek. Yoğun saatlerde (07-09 / 17-19) trend "
                "açıkça artar."
            )


# ===== Tab 5 — Burst Senaryosu ============================================

with tab_burst:
    st.subheader("Burst Senaryosu — Ani Talep Altında 4 Kontrolcü")
    st.caption(
        "Standart 4 saat koşumun ortasında 30 dk boyunca Kuzey'e +20 araç/dk "
        "ek yığın (okul çıkışı / maç sonu benzeri). Sabit kontrolün catastrophic "
        "fail ettiği, predictive'in trend yakalama avantajının ortaya çıktığı yer."
    )

    burst_csv = Path("results/comparison_burst.csv")
    burst_png = Path("results/comparison_burst.png")
    if not burst_csv.exists():
        st.warning(
            "`results/comparison_burst.csv` bulunamadı. Önce şu komutu koşturun:\n"
            "```\npython -m intersection_sim.scenarios.burst --seeds 5 --duration-hours 4\n```"
        )
    else:
        burst_df = pd.read_csv(burst_csv)
        display_cols = [
            "display_name_tr", "mean_wait_s_mean", "p95_wait_s_mean",
            "emergency_wait_s_mean", "throughput_per_hour_mean",
            "fairness_index_mean",
        ]
        display_cols = [c for c in display_cols if c in burst_df.columns]
        st.dataframe(
            burst_df[display_cols].rename(columns={
                "display_name_tr": "Kontrolcü",
                "mean_wait_s_mean": "Ort. bekleme (sn)",
                "p95_wait_s_mean": "p95 (sn)",
                "emergency_wait_s_mean": "Acil (sn)",
                "throughput_per_hour_mean": "Throughput (araç/sa)",
                "fairness_index_mean": "Fairness",
            }),
            use_container_width=True, hide_index=True,
        )

        if burst_png.exists():
            st.image(str(burst_png), use_container_width=True,
                     caption="Burst senaryosu — log ölçek (fixed ekseni dağıtmasın diye)")

        # Fixed vs adaptive vurgu
        fixed_row = burst_df[burst_df["controller"] == "fixed"]
        adapt_row = burst_df[burst_df["controller"] == "adaptive"]
        if not fixed_row.empty and not adapt_row.empty:
            f_mean = fixed_row["mean_wait_s_mean"].iloc[0]
            a_mean = adapt_row["mean_wait_s_mean"].iloc[0]
            ratio = f_mean / a_mean if a_mean > 0 else 0
            st.error(
                f"**Sabit kontrol burst'te catastrophic fail:** {f_mean:.0f} sn "
                f"ortalama bekleme (adaptive'in **{ratio:.0f} katı**). "
                f"Çevrim sırasıyla giden kontrol ani yığını yakalayamaz."
            )
        pred_row = burst_df[burst_df["controller"] == "predictive"]
        if not pred_row.empty and not adapt_row.empty:
            p_p95 = pred_row["p95_wait_s_mean"].iloc[0]
            a_p95 = adapt_row["p95_wait_s_mean"].iloc[0]
            p_fair = pred_row["fairness_index_mean"].iloc[0]
            a_fair = adapt_row["fairness_index_mean"].iloc[0]
            st.success(
                f"**Hibrit predictive burst'te trend avantajı:** "
                f"p95 {p_p95:.1f} sn (adaptive {a_p95:.1f} sn), "
                f"fairness {p_fair:.3f} vs {a_fair:.3f}."
            )


# ===== Tab 6 — Sensitivity α Sweep ========================================

with tab_sens:
    st.subheader("Sensitivity Analysis — Hibrit Predictive α Sweep")
    st.caption(
        "Predictive controller'ın hibrit skor formulü: "
        "`score = current + α × max(0, predicted − current)`. "
        "α=0 saf adaptive demektir; α büyüdükçe trend bonusu ağırlık kazanır. "
        "Buradaki sweep ile α'nın metriklere etkisini gözlemleyebilirsiniz."
    )

    col1, col2 = st.columns(2)
    with col1:
        sweep_seeds = st.slider("Seed sayısı", 2, 8, 3, key="sens_seeds",
                                help="Daha fazla seed = daha sağlam ortalama, daha yavaş")
    with col2:
        sweep_hours = st.slider("Süre (saat)", 1, 4, 2, key="sens_hours",
                                help="Toplam sim süresi her α için")

    alpha_default = "0.0, 0.1, 0.3, 0.5, 0.7, 1.0"
    alphas_str = st.text_input("α değerleri (virgülle ayırın)",
                               value=alpha_default,
                               help="Örn: 0.0, 0.3, 0.7")

    if st.button("Sweep'i çalıştır", type="primary", key="run_sweep"):
        try:
            alphas = [float(s.strip()) for s in alphas_str.split(",") if s.strip()]
        except ValueError as exc:
            st.error(f"α parse hatası: {exc}")
            alphas = []

        if alphas:
            n_runs = len(alphas) + 1  # +1 adaptive baseline
            spinner_msg = (
                f"Sweep çalışıyor: {n_runs} senaryo × {sweep_seeds} seed × "
                f"{sweep_hours} saat ..."
            )
            with st.spinner(spinner_msg):
                sweep_df = predictive_alpha_sweep(
                    alphas=alphas,
                    seeds=list(range(int(sweep_seeds))),
                    duration_hours=float(sweep_hours),
                )
            st.session_state["sweep_df"] = sweep_df

    if "sweep_df" in st.session_state:
        sweep_df = st.session_state["sweep_df"]
        st.markdown("**Sweep sonuçları**")
        st.dataframe(
            sweep_df.assign(
                mean_wait_s=lambda d: d["mean_wait_s"].round(2),
                p95_wait_s=lambda d: d["p95_wait_s"].round(2),
                fairness_index=lambda d: d["fairness_index"].round(4),
            ).drop(columns=["alpha"]),
            use_container_width=True, hide_index=True,
        )

        # 3 yan yana mini-grafik
        plot_cols = st.columns(3)
        non_baseline = sweep_df[sweep_df["alpha"].notna()].copy()
        if not non_baseline.empty:
            # adaptive baseline'ı yatay çizgi olarak çiz
            adapt = sweep_df[sweep_df["alpha"].isna()].iloc[0]
            metrics_plot = [
                ("mean_wait_s", "Ortalama bekleme (sn)", "lower is better"),
                ("p95_wait_s", "p95 bekleme (sn)", "lower is better"),
                ("fairness_index", "Fairness (Jain)", "higher is better"),
            ]
            for ax_col, (metric_key, title_text, direction) in zip(
                plot_cols, metrics_plot,
            ):
                with ax_col:
                    fig, ax = plt.subplots(figsize=(4.5, 3.5))
                    ax.plot(non_baseline["alpha"], non_baseline[metric_key],
                            marker="o", color="#7C3AED", linewidth=2,
                            label="predictive")
                    if pd.notna(adapt[metric_key]):
                        ax.axhline(adapt[metric_key],
                                   linestyle="--", color="#EAB308",
                                   label="adaptive baseline")
                    ax.set_xlabel("α (trend bonus ağırlığı)")
                    ax.set_ylabel(title_text)
                    ax.set_title(f"{title_text} ({direction})", fontsize=10)
                    ax.legend(fontsize=8)
                    ax.grid(alpha=0.3)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)

        st.info(
            "**Yorum:** α=0 saf adaptive; α>0 artan trend bonusu. "
            "Hibrit predictive'in default α=0.3 — bu sweep ile seçildi. "
            "Çok küçük α (≤0.1) adaptive'le aynıdır; çok büyük α (≥1.5) trend "
            "tahmini gürültüsü ağır basar."
        )


# ===== Tab 7 — Kavşak Görseli =============================================

with tab_diagram:
    st.subheader("Kavşak Görseli")

    if "current_run" not in st.session_state:
        st.info(
            "Önce Sekme 1'den bir senaryo çalıştırın. Bu diyagram koşumun"
            " **son snapshot**'ındaki kavşak durumunu gösterir."
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
                "Snapshot zamanı",
                0, n_snaps - 1, n_snaps - 1,
                help="Sim-zamanı üzerinde gez. 0 = başlangıç, son = bitiş.",
            )
            row = snap_df.iloc[idx]

            # Kuyruk ve sinyal durumu o snapshot için
            from intersection_sim.domain.direction import Direction as _Dir
            from intersection_sim.domain.signal import (  # noqa: N814
                LightState as _LS,
            )

            queue_lengths = {
                d: int(row[f"queue_{d.value}"]) for d in _Dir
            }

            # Snapshot'ta active_green kayitli — diger 3 yön kırmızı
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
                st.markdown("**Yön durumları**")
                green_dir = None
                for d in _Dir:
                    if signals[d] is _LS.GREEN:
                        green_dir = d
                        break

                if green_dir is not None:
                    st.markdown(f"**Yeşil:** {green_dir.display_name_tr}")
                else:
                    st.markdown("Şu an hiçbir yön yeşil değil "
                                "(sarı veya tüm-kırmızı buffer)")

                st.markdown("**Kuyruk uzunlukları**")
                for d in _Dir:
                    st.markdown(f"- {d.display_name_tr}: {queue_lengths[d]} araç")

                st.divider()
                st.caption(
                    "Bu diyagram bir 'fotoğraf' — slider'ı kaydırarak"
                    " başka bir sim-zamanındaki kavşak durumunu görebilirsin."
                )
