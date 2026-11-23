"""Standalone calculation of expected totals. Does NOT touch the web app.

Uses Decimal so arithmetic is exact, then rounds half-up once at the end.
Writes test_cases.csv and prints the working for every case.
"""
import csv
from decimal import Decimal as D, ROUND_HALF_UP

PRICES = [D("12.50"), D("14.00"), D("6.00"), D("11.00"),
          D("9.50"), D("3.00"), D("2.00"), D("8.00")]
NAMES = ["Grok-5", "Claude Sonnet 5.5", "Qwen-4-Max", "GPT-5",
         "Gemini 3 Pro", "Llama 4 Maverick", "DeepSeek-V4", "Mistral Large 3"]
BATCH = D("0.5")
SST = D("0.06")

Z = "0"
# (tc_id, short label, usages u1..u8, batch flags b1..b8)
CASES = [
    ("TC01", "all zero usage",
     [Z] * 8, [0] * 8),
    ("TC02", "only first model",
     ["10", Z, Z, Z, Z, Z, Z, Z], [0] * 8),
    ("TC03", "only last model",
     [Z, Z, Z, Z, Z, Z, Z, "25"], [0] * 8),
    ("TC04", "one typical model",
     [Z, "40", Z, Z, Z, Z, Z, Z], [0] * 8),
    ("TC05", "all 8 models no batch",
     ["1", "2", "3", "4", "5", "6", "7", "8"], [0] * 8),
    ("TC06", "all 8 models all batch",
     ["1", "2", "3", "4", "5", "6", "7", "8"], [1] * 8),
    ("TC07", "mixed batch",
     ["1", "2", "3", "4", "5", "6", "7", "8"], [1, 0, 1, 0, 1, 0, 1, 0]),
    ("TC08", "decimal usage rounding",
     [Z, Z, Z, Z, Z, Z, "0.125", Z], [0] * 8),
    ("TC09", "very large usage",
     ["100000", "100000", Z, Z, Z, Z, Z, Z], [0, 1, 0, 0, 0, 0, 0, 0]),
    ("TC10", "very small usage",
     ["0.001", Z, Z, Z, Z, Z, Z, Z], [0] * 8),
]


def r2(x):
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def calc(usages, batches, verbose=True):
    subtotal = D(0)
    for i, (u, b) in enumerate(zip(usages, batches)):
        u = D(u)
        if u == 0:
            continue
        raw = u * PRICES[i]
        cost = raw * BATCH if b else raw
        subtotal += cost
        if verbose:
            note = f"{u} x {PRICES[i]} = {raw}"
            if b:
                note += f"; batch x 0.5 = {cost}"
            print(f"    {NAMES[i]:<18} {note}")
    sst = subtotal * SST
    total = subtotal + sst
    if verbose:
        print(f"    subtotal = {subtotal}")
        print(f"    SST      = {subtotal} x 0.06 = {sst}")
        print(f"    total    = {subtotal} + {sst} = {total}")
    return total


rows = []
for tc_id, label, usages, batches in CASES:
    print(f"{tc_id}  ({label})")
    print("    usages:", usages, " batch:", batches)
    total = calc(usages, batches)
    expected = r2(total)
    print(f"    expected_total (2dp, half-up) = {expected}\n")
    rows.append([tc_id, label] + usages + batches + [str(expected)])

header = (["tc_id", "description"] + [f"u{i}" for i in range(1, 9)]
          + [f"b{i}" for i in range(1, 9)] + ["expected_total"])
with open("test_cases.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
print("Wrote test_cases.csv with", len(rows), "cases")
