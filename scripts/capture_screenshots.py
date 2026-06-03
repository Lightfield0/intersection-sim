"""Playwright ile Streamlit dashboard ekran goruntulerini al.

Streamlit'in onceden ayri bir terminalde calistirilmasi gerekiyor:
    streamlit run dashboard.py --server.headless true --server.port 8501

Bu script:
  1. Tarayicida dashboard'i acar
  2. 'Adaptif' senaryosunu secip Calistir'a basar
  3. Sirayla 3 sekmeyi gezer, her birinde screenshot alir
  4. Sekme 2'deki acil arac grafigi (PNG dosyasi) icin de ayri kopya cikar
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, Playwright, sync_playwright

URL = "http://127.0.0.1:8501"
OUT = Path("results/screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def _wait_settled(page: Page, settle_ms: int = 1500) -> None:
    """Streamlit "Running..." spinner'inin gecmesini bekle."""
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(settle_ms)


def run(pw: Playwright) -> None:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1600, "height": 1000},
        device_scale_factor=2,
    )
    page = context.new_page()
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Sidebar'dan Adaptif sec
    selector = page.locator("[data-baseweb='select']").first
    selector.click()
    page.wait_for_timeout(400)
    page.get_by_role("option", name="Adaptif", exact=True).click()
    page.wait_for_timeout(300)

    # Calistir'a bas
    page.get_by_role("button", name="Çalıştır").click()
    # KPI kartlari belirinceye kadar bekle
    page.wait_for_selector("text=Senaryo:", timeout=60_000)
    _wait_settled(page, settle_ms=2500)

    # ---- Sekme 1: Senaryo Calistir (default tab) ----
    page.screenshot(path=str(OUT / "01_kpi_summary.png"), full_page=True)
    print(f"captured {OUT / '01_kpi_summary.png'}")

    # ---- Sekme 2: 3 Kontrolcu Karsilastirma ----
    page.get_by_role("tab", name="4 Kontrolcü Karşılaştırma").click()
    _wait_settled(page, settle_ms=2000)
    page.screenshot(path=str(OUT / "02_comparison.png"), full_page=True)
    print(f"captured {OUT / '02_comparison.png'}")

    # ---- Sekme 3: Kavsak Gorseli ----
    page.get_by_role("tab", name="Kavşak Görseli").click()
    _wait_settled(page, settle_ms=2000)
    page.screenshot(path=str(OUT / "03_intersection_view.png"), full_page=True)
    print(f"captured {OUT / '03_intersection_view.png'}")

    # ---- Acil arac grafigi (PNG dosyasini kopyala) ----
    em_src = Path("results/comparison_emergency_wait.png")
    em_dst = OUT / "04_emergency_grafik.png"
    if em_src.exists():
        em_dst.write_bytes(em_src.read_bytes())
        print(f"copied {em_dst}")

    browser.close()


if __name__ == "__main__":
    try:
        with sync_playwright() as pw:
            run(pw)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    print("done")
