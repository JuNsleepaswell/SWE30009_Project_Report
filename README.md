# LLM AI Gateway Dashboard

[![Test (Ubuntu)](https://github.com/JuNsleepaswell/SWE30009_Project_Report/actions/workflows/test-ubuntu.yml/badge.svg)](https://github.com/JuNsleepaswell/SWE30009_Project_Report/actions/workflows/test-ubuntu.yml)
[![Test (Windows)](https://github.com/JuNsleepaswell/SWE30009_Project_Report/actions/workflows/test-windows.yml/badge.svg)](https://github.com/JuNsleepaswell/SWE30009_Project_Report/actions/workflows/test-windows.yml)

A small web app for estimating LLM API bills, built for SWE30009 Software Testing and Reliability, together with an automated Selenium test suite.

The dashboard lists 8 models with a unit price (RM per 1M tokens). For each model you enter usage (millions of tokens) and optionally tick **Batch API** (50% off). **Calculate Bill** shows the subtotal, 6% SST and total. The app is plain HTML, CSS and JavaScript with no frameworks.

The test suite (`test_gateway.py`) reads cases from `test_cases.csv`, drives the page in Chrome, compares the displayed total with the expected value, saves a screenshot per case and writes `report.html`.

## Project files

| File | Purpose |
|---|---|
| `index.html`, `style.css`, `script.js` | The web app |
| `test_cases.csv` | Test data (10 cases with expected totals) |
| `compute_expected.py` | Standalone calculation that produced the expected totals |
| `test_gateway.py` | Selenium test runner and report generator |
| `requirements.txt` | Python dependencies |
| `.github/workflows/` | Ubuntu and Windows CI workflows |

## Run locally

Requirements: Python 3.9+ and Google Chrome.

```bash
pip install -r requirements.txt

# Terminal 1: serve the app
python -m http.server 8000

# Terminal 2: run the tests
python test_gateway.py
```

Open http://localhost:8000/index.html to use the app manually.

- Chrome runs visibly by default. Set the `CI` environment variable to run headless.
- Output: one line per test, `screenshots/<tc_id>.png` per case, and `report.html`.
- The script exits with code 1 if any test fails.

## Continuous integration

Both workflows are started manually from the **Actions** tab (**Run workflow**). They check out the repo, set up Python and Chrome, start the server, run the tests, and upload `report.html` and the `screenshots` folder as an artifact (even when tests fail).
