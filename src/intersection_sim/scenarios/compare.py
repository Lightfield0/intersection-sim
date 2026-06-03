"""CLI: 4 kontrolcuyu karsilastir, CSV ve PNG'leri yaz.

Kullanim:
    python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4
    python -m intersection_sim.scenarios.compare --seeds 5 --output results/

Adimlar:
    1. seeds 0..N-1 listesi olustur
    2. compare_controllers(seeds, hours) cagir
    3. results_to_dataframe ile DataFrame yap
    4. comparison.csv olarak yaz
    5. plots.compare.save_all_plots ile 4 PNG çıkar
    6. Konsola tabloyu bas
"""

import argparse
from pathlib import Path

from intersection_sim.plots.compare import save_all_plots
from intersection_sim.scenarios.runner import compare_controllers, results_to_dataframe


def parse_args(argv: "list[str] | None" = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="intersection_sim.scenarios.compare",
        description="4 kontrolcuyu coklu seed ile kosturup karsilastirir.",
    )
    parser.add_argument(
        "--seeds", type=int, default=5,
        help="Kac seed kullanilsin (0..N-1; default: 5)",
    )
    parser.add_argument(
        "--duration-hours", type=float, default=4.0,
        help="Her koşumun suresi (saat; default: 4)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("results"),
        help="CSV ve PNG ciktilarinin yazilacagi klasor",
    )
    parser.add_argument(
        "--skip-distribution", action="store_true",
        help="Bonus histogram grafigini atla (daha hızlı)",
    )
    return parser.parse_args(argv)


def main(argv: "list[str] | None" = None) -> None:
    args = parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    seeds = list(range(args.seeds))
    print(f"Karşılaştırma basliyor: {args.seeds} seed x 4 kontrolcü x "
          f"{args.duration_hours}h ...")

    results = compare_controllers(seeds, args.duration_hours)

    # CSV çıktı
    df = results_to_dataframe(results)
    csv_path = args.output / "comparison.csv"
    df.to_csv(csv_path, index=False)

    # PNG'ler
    print("Grafikler uretiliyor ...")
    plot_paths = save_all_plots(
        results, args.output,
        include_distribution=not args.skip_distribution,
    )

    # Konsol özet
    print()
    print("=" * 70)
    print(" Karşılaştırma Tablosu")
    print("=" * 70)
    # Sade sutunlar — sunum için önemli olanlar
    print(df[[
        "controller", "mean_wait_s_mean", "normal_wait_s_mean",
        "emergency_wait_s_mean", "throughput_per_hour_mean",
        "preemption_count_mean",
    ]].to_string(index=False))
    print()
    print(f" yazildi: {csv_path}")
    for _label, path in plot_paths.items():
        print(f" yazildi: {path}")


if __name__ == "__main__":
    main()
