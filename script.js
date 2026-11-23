"use strict";

// ---- Configuration -------------------------------------------------------
const MODELS = [
  { name: "Grok-5",            provider: "xAI",        price: 12.50 },
  { name: "Claude Sonnet 5.5", provider: "Anthropic",  price: 14.00 },
  { name: "Qwen-4-Max",        provider: "Alibaba",    price: 6.00  },
  { name: "GPT-5",             provider: "OpenAI",     price: 11.00 },
  { name: "Gemini 3 Pro",      provider: "Google",     price: 9.50  },
  { name: "Llama 4 Maverick",  provider: "Meta",       price: 3.00  },
  { name: "DeepSeek-V4",       provider: "DeepSeek",   price: 2.00  },
  { name: "Mistral Large 3",   provider: "Mistral AI", price: 8.00  },
];

const BATCH_FACTOR = 0.5;   // Batch API halves the row cost
const SST_RATE = 0.06;      // 6% Sales and Service Tax
const MAX_USAGE = 100000;   // millions of tokens; anything above is rejected as absurd

// ---- Helpers -------------------------------------------------------------
const $ = (id) => document.getElementById(id);

// Formatting is the ONLY place rounding happens.
// Math.round rounds half up; Number.EPSILON nudges values like 1.005
// (stored as 1.00499999999999989...) over the half-way mark.
function formatRM(value) {
  const rounded = Math.round((value + Number.EPSILON) * 100) / 100;
  return "RM " + rounded.toFixed(2);
}

// Build the 8 table rows from MODELS so name/provider/price live in one place.
// IDs usage-N and batch-N (N = 1..8) are unchanged.
function buildTable() {
  const body = $("model-body");
  body.innerHTML = "";

  MODELS.forEach((model, i) => {
    const n = i + 1;
    const tr = document.createElement("tr");

    const addText = (label, text, cls) => {
      const td = document.createElement("td");
      td.dataset.label = label;
      td.textContent = text;
      if (cls) td.className = cls;
      tr.appendChild(td);
      return td;
    };

    addText("Model", model.name);
    addText("Provider", model.provider);
    addText("Price", model.price.toFixed(2), "num");

    const usageTd = addText("Usage", "");
    const usage = document.createElement("input");
    usage.type = "number";
    usage.id = "usage-" + n;
    usage.min = "0";
    usage.step = "any";
    usage.placeholder = "0";
    usage.setAttribute("aria-label", "Usage for " + model.name + " in millions of tokens");
    usageTd.appendChild(usage);

    const batchTd = addText("Batch API", "", "center");
    const batch = document.createElement("input");
    batch.type = "checkbox";
    batch.id = "batch-" + n;
    batch.setAttribute("aria-label", "Batch API for " + model.name);
    batchTd.appendChild(batch);

    body.appendChild(tr);
  });
}

// Validate every usage field. Returns { errors: [...], usages: [...] }.
// Empty field is treated as 0 (user simply did not use that model).
function readInputs() {
  const errors = [];
  const usages = [];

  MODELS.forEach((model, i) => {
    const input = $("usage-" + (i + 1));
    input.classList.remove("invalid");

    // A type="number" input reports typed garbage (e.g. "abc", "1e") as
    // value === "" with validity.badInput === true, so check that first.
    if (input.validity.badInput) {
      errors.push(model.name + ": usage must be a number.");
      input.classList.add("invalid");
      usages.push(0);
      return;
    }

    const raw = input.value.trim();
    if (raw === "") {
      usages.push(0);
      return;
    }

    const value = Number(raw);
    if (!Number.isFinite(value)) {
      errors.push(model.name + ": usage must be a number.");
      input.classList.add("invalid");
    } else if (value < 0) {
      errors.push(model.name + ": usage cannot be negative.");
      input.classList.add("invalid");
    } else if (value > MAX_USAGE) {
      errors.push(model.name + ": usage cannot exceed " + MAX_USAGE + " million tokens.");
      input.classList.add("invalid");
    }
    usages.push(value);
  });

  return { errors, usages };
}

function showError(messages) {
  const box = $("error-message");
  box.textContent = messages.join(" ");
  box.hidden = false;
}

function clearError() {
  const box = $("error-message");
  box.textContent = "";
  box.hidden = true;
}

// Reset results so a stale bill is never shown next to an error.
function clearResults() {
  $("summary-body").innerHTML = "";
  $("summary-table-wrap").hidden = true;
  $("summary-empty").hidden = false;
  $("subtotal").textContent = "--";
  $("sst").textContent = "--";
  $("total-amount").textContent = "--";
}

// ---- Main calculation ----------------------------------------------------
function calculateBill() {
  clearError();

  const { errors, usages } = readInputs();
  if (errors.length > 0) {
    clearResults();
    showError(errors);
    return;
  }

  let subtotal = 0;
  const lines = [];

  MODELS.forEach((model, i) => {
    const usage = usages[i];
    const batch = $("batch-" + (i + 1)).checked;

    let cost = usage * model.price;      // 1. usage x price
    if (batch) cost = cost * BATCH_FACTOR; // 2. batch discount

    subtotal += cost;                    // 3. subtotal
    if (usage > 0) {
      lines.push({ name: model.name, usage, batch, cost });
    }
  });

  const sst = subtotal * SST_RATE;       // 4. SST
  const total = subtotal + sst;          // 5. total

  renderSummary(lines);
  $("subtotal").textContent = formatRM(subtotal);
  $("sst").textContent = formatRM(sst);
  $("total-amount").textContent = formatRM(total);
}

function renderSummary(lines) {
  const body = $("summary-body");
  body.innerHTML = "";

  if (lines.length === 0) {
    $("summary-table-wrap").hidden = true;
    $("summary-empty").textContent = "No models with usage greater than zero.";
    $("summary-empty").hidden = false;
    return;
  }

  lines.forEach((line) => {
    const tr = document.createElement("tr");
    const cells = [
      [line.name, ""],
      [String(line.usage), "num"],
      [line.batch ? "Yes" : "No", "center"],
      [formatRM(line.cost), "num"],
    ];
    cells.forEach(([text, cls]) => {
      const td = document.createElement("td");
      td.textContent = text;       // textContent: no HTML injection
      if (cls) td.className = cls;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });

  $("summary-empty").hidden = true;
  $("summary-table-wrap").hidden = false;
}

buildTable();
$("calculate-btn").addEventListener("click", calculateBill);
