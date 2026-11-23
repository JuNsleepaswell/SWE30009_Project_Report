"""Data-driven Selenium tests for the LLM AI Gateway Dashboard.

Reads every case from test_cases.csv, drives the page in Chrome and compares
the displayed total with expected_total.
"""
import csv
import datetime
import html
import math
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000/index.html")
CSV_FILE = "test_cases.csv"
SCREENSHOT_DIR = "screenshots"
TOLERANCE = 0.005
WAIT_SECONDS = 10
NUM_MODELS = 8
REPORT_FILE = "report.html"

REPORT_CSS = """
body{font-family:system-ui,Segoe UI,Arial,sans-serif;background:#f1f4f9;color:#1c2433;margin:0;padding:24px}
.wrap{max-width:1000px;margin:0 auto;background:#fff;border:1px solid #e2e7f0;border-radius:12px;padding:28px}
h1{margin:0 0 4px}.meta{color:#667085;margin:0 0 20px;font-size:.9rem}
.top{display:flex;flex-wrap:wrap;gap:24px;align-items:center;margin-bottom:24px}
.cards{display:flex;flex-wrap:wrap;gap:12px;flex:1}
.card{flex:1;min-width:120px;padding:14px 16px;border:1px solid #e2e7f0;border-radius:10px;background:#f8f9fc}
.card .v{font-size:1.6rem;font-weight:700}.card .l{color:#667085;font-size:.8rem;text-transform:uppercase}
.card.pass .v{color:#1a7f37}.card.fail .v{color:#c62828}
table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #e2e7f0;vertical-align:top}
th{background:#f8f9fc;font-size:.75rem;text-transform:uppercase;color:#667085}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr.pass{background:#eaf7ee}tr.fail{background:#fdecec}
.badge{font-weight:700;padding:2px 8px;border-radius:6px;color:#fff}
.badge.pass{background:#1a7f37}.badge.fail{background:#c62828}
.bar{height:6px;background:#3b5bdb;border-radius:3px;margin-top:4px}
.legend span{display:inline-block;margin-right:14px;font-size:.85rem}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
"""


def donut_svg(passed, failed):
    """Inline SVG pass/fail donut. Red base circle with a green arc on top."""
    total = passed + failed
    r = 60
    circ = 2 * math.pi * r
    green = circ * (passed / total) if total else 0
    pct = (100.0 * passed / total) if total else 0.0
    return (
        '<svg width="160" height="160" viewBox="0 0 160 160" role="img" '
        'aria-label="Pass/fail chart: %d passed, %d failed">'
        '<circle cx="80" cy="80" r="%d" fill="none" stroke="%s" stroke-width="22"/>'
        '<circle cx="80" cy="80" r="%d" fill="none" stroke="#1a7f37" stroke-width="22" '
        'stroke-dasharray="%.2f %.2f" transform="rotate(-90 80 80)"/>'
        '<text x="80" y="86" text-anchor="middle" font-size="22" font-weight="700" '
        'fill="#1c2433">%.0f%%</text></svg>'
    ) % (passed, failed, r, "#c62828" if failed else "#e2e7f0", r, green, circ, pct)


def write_report(results, total_time, path=REPORT_FILE):
    """Write a self-contained report.html (inline CSS + inline SVG, no CDN)."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    rate = (100.0 * passed / total) if total else 0.0
    max_t = max([r["seconds"] for r in results] + [0.001])
    mode = "headless (CI)" if os.environ.get("CI") else "headed (local)"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for r in results:
        cls = "pass" if r["passed"] else "fail"
        actual = "%.2f" % r["actual"] if r["actual"] is not None else "N/A"
        rows.append(
            '<tr class="%s"><td>%s</td><td>%s</td><td class="n">%.2f</td>'
            '<td class="n">%s</td><td><span class="badge %s">%s</span></td>'
            '<td class="n">%.2f<div class="bar" style="width:%.0f%%"></div></td>'
            '<td>%s</td></tr>' % (
                cls, html.escape(r["tc_id"]), html.escape(r["description"]),
                r["expected"], actual, cls, "PASS" if r["passed"] else "FAIL",
                r["seconds"], 100.0 * r["seconds"] / max_t,
                html.escape(r["reason"]) if r["reason"] else "-"))

    doc = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test Report - LLM AI Gateway Dashboard</title>
<style>%s</style></head>
<body><div class="wrap">
<h1>Test Report</h1>
<p class="meta">LLM AI Gateway Dashboard &middot; %s &middot; %s mode &middot; runner: %s</p>
<div class="top">
%s
<div class="cards">
<div class="card"><div class="v">%d</div><div class="l">Total</div></div>
<div class="card pass"><div class="v">%d</div><div class="l">Passed</div></div>
<div class="card fail"><div class="v">%d</div><div class="l">Failed</div></div>
<div class="card"><div class="v">%.1f%%</div><div class="l">Pass rate</div></div>
<div class="card"><div class="v">%.2fs</div><div class="l">Total time</div></div>
</div></div>
<p class="legend"><span><i class="dot" style="background:#1a7f37"></i>Passed</span>
<span><i class="dot" style="background:#c62828"></i>Failed</span></p>
<table><thead><tr><th>TC</th><th>Description</th><th class="n">Expected (RM)</th>
<th class="n">Actual (RM)</th><th>Result</th><th class="n">Time (s)</th>
<th>Failure reason</th></tr></thead>
<tbody>
%s
</tbody></table>
</div></body></html>
""" % (REPORT_CSS, now, mode, os.environ.get("RUNNER_OS", "local"),
       donut_svg(passed, failed), total, passed, failed, rate, total_time,
       "\n".join(rows))

    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


def load_cases(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_driver():
    options = Options()
    # Headless only on CI (GitHub Actions sets CI=true).
    if os.environ.get("CI"):
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    # Tall window so the full summary (up to 8 rows) and Total fit in screenshots.
    options.add_argument("--window-size=1280,1800")
    return webdriver.Chrome(options=options)


def parse_rm(text):
    """'RM 132.50' -> 132.5"""
    return float(text.replace("RM", "").replace(",", "").strip())


def run_case(driver, case):
    """Fill the form for one CSV row and return the displayed total as a float."""
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, WAIT_SECONDS)

    for i in range(1, NUM_MODELS + 1):
        usage = driver.find_element(By.ID, f"usage-{i}")
        usage.clear()
        usage.send_keys(case[f"u{i}"])

        checkbox = driver.find_element(By.ID, f"batch-{i}")
        want_on = case[f"b{i}"].strip() == "1"
        if checkbox.is_selected() != want_on:
            checkbox.click()

    driver.find_element(By.ID, "calculate-btn").click()

    # The total shows "--" until a calculation succeeds, then "RM x.xx".
    wait.until(
        lambda d: d.find_element(By.ID, "total-amount").text.strip().startswith("RM")
    )
    return parse_rm(driver.find_element(By.ID, "total-amount").text)


def main():
    cases = load_cases(CSV_FILE)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    results = []  # one dict per case (reused later for the report)
    start_all = time.time()
    driver = None

    try:
        driver = make_driver()
        for case in cases:
            tc_id = case["tc_id"]
            expected = float(case["expected_total"])
            actual = None
            reason = ""
            start = time.time()

            try:
                actual = run_case(driver, case)
                passed = abs(actual - expected) <= TOLERANCE
                if not passed:
                    reason = "expected %.2f but got %.2f" % (expected, actual)
            except Exception as exc:
                passed = False
                reason = "%s: %s" % (type(exc).__name__, str(exc).splitlines()[0] if str(exc) else "")

            # Screenshot for every case, pass or fail. Scroll the total into
            # view first so it is never cut off.
            try:
                driver.execute_script(
                    "var e = document.getElementById('total-amount');"
                    "if (e) e.scrollIntoView({block: 'center'});")
                driver.save_screenshot(os.path.join(SCREENSHOT_DIR, tc_id + ".png"))
            except Exception:
                pass

            elapsed = time.time() - start
            results.append({
                "tc_id": tc_id,
                "description": case.get("description", ""),
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "reason": reason,
                "seconds": elapsed,
            })

            actual_txt = "%.2f" % actual if actual is not None else "N/A"
            print("%s  expected=%.2f  actual=%s  %s" % (
                tc_id, expected, actual_txt, "PASS" if passed else "FAIL"))
            if reason:
                print("      reason: " + reason)
    finally:
        if driver is not None:
            driver.quit()

    total_time = time.time() - start_all
    passed_n = sum(1 for r in results if r["passed"])
    failed_n = len(results) - passed_n

    print("-" * 50)
    print("Total: %d  Passed: %d  Failed: %d  Time: %.2fs" % (
        len(results), passed_n, failed_n, total_time))

    write_report(results, total_time)
    print("Report written to " + REPORT_FILE)

    return 1 if failed_n > 0 or not results else 0


if __name__ == "__main__":
    sys.exit(main())
