"""CLI ana giris noktasi: ``python -m intersection_sim.run``.

Verilen kontrolcu ile bir simulasyon kosturup:
  - per-vehicle CSV ciktisi yazar (her arac bir satir)
  - snapshot CSV ciktisi yazar (zaman serisi, her 10 sn)
  - JSON ozet raporu yazar (KPI'lar)
  - Konsola ozet tablo basar

Kullanim:
    python -m intersection_sim.run --controller fixed     --seed 42
    python -m intersection_sim.run --controller adaptive  --seed 42
"""

import argparse
from pathlib import Path
from typing import Callable

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.simulation.runner import ControllerFn, run_with_controller

CONTROLLERS: dict[str, Callable[..., object]] = {
    "fixed": fixed_controller,
    "adaptive": adaptive_controller,
    "preemptive": preemptive_controller,
}


def parse_args(argv: "list[str] | None" = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="intersection_sim.run",
        description="Akilli kavsak trafik isigi simulasyonu.",
    )
    parser.add_argument(
        "--controller", choices=sorted(CONTROLLERS.keys()), default="fixed",
        help="Hangi kontrolcuyu kullanalim (default: fixed)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="RNG seed (default: 42)",
    )
    parser.add_argument(
        "--duration-hours", type=float, default=4.0,
        help="Simulasyon suresi saat olarak (default: 4)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results"),
        help="CSV ve JSON ciktilarinin yazilacagi klasor",
    )
    return parser.parse_args(argv)


def main(argv: "list[str] | None" = None) -> None:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    config = SimConfig(
        seed=args.seed,
        horizon_seconds=args.duration_hours * 3600.0,
    )
    controller: ControllerFn = CONTROLLERS[args.controller]  # type: ignore[assignment]
    intersection = run_with_controller(config, controller)
    report = intersection.metrics.build_report(config.horizon_seconds)

    # ---- CSV + JSON yaz --------------------------------------------------
    prefix = args.controller
    vehicles_csv = args.output_dir / f"{prefix}_vehicles.csv"
    snapshots_csv = args.output_dir / f"{prefix}_snapshots.csv"
    kpi_json = args.output_dir / f"{prefix}_kpi.json"

    intersection.metrics.vehicles_dataframe().to_csv(vehicles_csv, index=False)
    intersection.metrics.snapshots_dataframe().to_csv(snapshots_csv, index=False)
    report.write_json(kpi_json)

    # ---- Konsol ozet -----------------------------------------------------
    print()
    print("=" * 60)
    print(f" {args.controller.upper()} kontrolcu - seed={args.seed}, sure={args.duration_hours}h")
    print("=" * 60)
    print(report.pretty_print())
    print()
    print(f" yazildi: {vehicles_csv}")
    print(f" yazildi: {snapshots_csv}")
    print(f" yazildi: {kpi_json}")


if __name__ == "__main__":
    main()
