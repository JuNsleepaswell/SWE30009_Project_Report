"""Data-driven Selenium tests for the LLM AI Gateway Dashboard.

Reads every case from test_cases.csv, drives the page in Chrome and compares
the displayed total with expected_total.
"""
import csv
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

    return 1 if failed_n > 0 or not results else 0


if __name__ == "__main__":
    sys.exit(main())
