# Codex Prompt: MGEN Business Continuity Stress Test — Streamlit App (v2)

## Overview

Build a **single-file Streamlit application** (`app.py` + `engine.py`) that replicates the MGEN Scenario Planning and Business Continuity Stress Test Excel model. The app has **4 tabs** and applies **Bain & Company branding** throughout. All calculations run in Python; the app must reproduce the Excel's `60_Outputs` sheet values exactly (validation reference provided in §8).

---

## 1. Design System — Bain & Company

| Token | Hex | Usage |
|---|---|---|
| Bain Red | `#CC0000` | Active tab indicator, KPI accent bars, negative values, section dividers |
| Dark Gray | `#333333` | Table headers (white text on dark bg), body text |
| Mid Gray | `#666666` | Secondary text, axis labels, muted annotations |
| Light Gray | `#F2F2F2` | Alternating table rows, card backgrounds, disabled states |
| White | `#FFFFFF` | Page background, card fill |
| Green | `#006600` | Positive financial values |
| Font | `Arial, Helvetica, sans-serif` | All text |

**UI rules:**
- Square corners everywhere (`border-radius: 0` on all elements).
- Thin `#CC0000` horizontal rule below the app title and between major sections.
- Table headers: `#333333` background, white text.
- Negative financial values: `#CC0000`; positive: `#006600`.
- KPI cards: white fill, 1px `#CCCCCC` border, 4px `#CC0000` left accent, large metric (24px+), small label (12px).
- Chart palette: `['#CC0000', '#333333', '#999999', '#E6E6E6']`, no gridlines, axis text `#666666`.
- Use `st.markdown` with custom CSS injected once at app start for all styling.
- Format all financial values with 1 decimal place + comma separators (`{:,.1f}`).
- Format all percentages as `XX.X%`. Display days as integers.

---

## 2. Application Structure

```
app.py          # Streamlit entry: layout, tabs, UI components, charts
engine.py       # Pure-Python calculation engine (no Streamlit imports)
defaults.py     # All default input dictionaries
requirements.txt
```

`engine.py` exports one function: `run_model(inputs: dict) -> dict` that takes all inputs and returns all intermediate + final outputs as nested dicts. The function must be **pure** (no side effects, no Streamlit calls) so it can be tested independently.

`app.py` handles all UI: tab layout, input widgets, file upload parsing, output rendering, chart generation, and downloads.

---

## 3. Tab Layout

```python
tab1, tab2, tab3, tab4 = st.tabs([
    "① Scenario Definition",
    "② Model Inputs",
    "③ Results & Dashboard",
    "④ Intermediate Calculations",
])
```

---

## 4. Tab 1 — Scenario Definition

### Purpose
Define the 3 stress scenarios (S1, S2, S3) plus the Base case. This is the primary "what-if" lever — users adjust commodity prices, FX, availability, and logistics disruption parameters.

### Layout

**Top row: Input mode selector**
```
○ Manual entry    ○ Upload Excel
```

**If "Upload Excel":** Show `st.file_uploader` (accepts `.xlsx`). On upload, parse with `openpyxl` (data_only=True) → read `03_Scenarios` rows 7–20, columns C–F. Display a green banner: "✓ Loaded 14 variables × 4 scenarios from [filename]". Auto-fill the manual-entry table below so the user can review and override.

**Scenario name editor (always visible):**
Four `st.text_input` fields in a row:
```
Base name: [Base]    S1 name: [Scenario 1]    S2 name: [Scenario 2]    S3 name: [Scenario 3]
```
These names propagate into all table headers and chart legends app-wide.

**Scenario matrix — editable table:**
Render as a grid of `st.number_input` widgets (4 columns × 14 rows). Each row has:
- **Variable name** (bold, left column)
- **Unit** (gray, second column)
- **Description tooltip / help text** (via `st.number_input(help=...)`)
- **4 value columns** (Base, S1, S2, S3)

Here is the full variable table with descriptions:

| # | Variable | Unit | Base | S1 | S2 | S3 | Description (show as help text) |
|---|---|---|---|---|---|---|---|
| 1 | Duration | days | 0 | 30 | 120 | 180 | How long the disruption lasts. Base = pre-escalation; S1 = contained (1 month); S2 = sustained (4 months); S3 = full shock (6 months). Drives the liquidity horizon mapping (30d → S1, 90d → S2, 180d → S3). |
| 2 | Brent crude | USD/bbl | 72.48 | 80 | 95 | 135 | Brent oil benchmark price. Base = 27 Feb 2026 close. S1 = $75–85 range midpoint; S2 = $90–100; S3 = $120–150+. Feeds oil peaker SRMC and generation cost. |
| 3 | JKM LNG | USD/MMBtu | 10.725 | 12.334 | 15.551 | 23.059 | Japan-Korea Marker spot LNG price. Key driver of gas plant fuel cost and WESM clearing price when gas is marginal. |
| 4 | Newcastle coal | USD/t | 115.8 | 124.485 | 141.855 | 167.91 | Newcastle thermal coal FOB benchmark. Drives coal-fired plant SRMC through the fuel landing cost chain. |
| 5 | Coal freight | USD/t | 10 | 11.5 | 14.5 | 19.5 | Freight cost from Newcastle to Philippines. Increases under shipping disruption, war-risk, or Suez/Malacca rerouting. |
| 6 | Coal insurance | USD/t | 0.5 | 0.75 | 1.25 | 2.0 | Marine cargo and war-risk insurance premium per tonne. Spikes under geopolitical escalation. |
| 7 | Coal logistics adder | USD/t | 0 | 0.5 | 1.5 | 4.0 | Additional logistics disruption cost (port congestion, vessel diversion, stockpile access). |
| 8 | FX rate | PHP/USD | 57.741 | 58.896 | 60.34 | 62.36 | Philippine peso to US dollar exchange rate. Amplifies all USD-denominated fuel costs when peso weakens. |
| 9 | LNG DES basis | USD/MMBtu | 0 | 0.5 | 2.0 | 5.0 | Delivered ex-ship basis premium vs JKM for Batangas terminal. Increases under LNG shipping tightness. Does NOT include regas or demurrage (those are in Tab 2). |
| 10 | LNG availability | % (0–1) | 1.00 | 0.97 | 0.85 | 0.70 | Fraction of gas plant capacity that can actually dispatch (throughput constraint). 1.0 = full availability; 0.7 = 30% derated. Derates gas MW in the merit order and shifts dispatch to oil peakers. |
| 11 | Coal delay | days | 0 | 5 | 14 | 28 | Additional days of coal delivery delay. Adds to inventory holding period in the liquidity working-capital model. |
| 12 | Bid uplift | % (0–1) | 0.05 | 0.07 | 0.10 | 0.15 | WESM bid mark-up above marginal cost. Captures scarcity rents and strategic bidding. WESM price = weighted clearing price × (1 + bid uplift). |
| 13 | Reserve alpha | % (0–1) | 0.25 | 0.28 | 0.35 | 0.45 | Fraction of WESM average price used as reserve market price anchor. Higher = more expensive ancillary services. Multiplied by scarcity factor when peak supply is tight. |
| 14 | Bad debt multiplier | x | 1.0 | 1.05 | 1.15 | 1.30 | Multiplier on retail segment base bad-debt rates. Captures credit deterioration under stress (customer non-payment). |

**Input validation on each field:**
- Duration: integer ≥ 0
- Prices (rows 2–7): float ≥ 0
- FX: float > 0
- LNG availability: 0 to 1 inclusive
- Coal delay: integer ≥ 0
- Bid uplift, Reserve alpha: 0 to 1 inclusive
- Bad debt multiplier: float ≥ 1

**Below the table:** Display a read-only summary card:
```
Scenario framework: S1 = Contained disruption / rapid normalisation
                    S2 = Sustained regional disruption
                    S3 = Full-scale regional supply shock
Base reference: Pre-escalation market proxy (27 Feb 2026 close)
```

---

## 5. Tab 2 — Model Inputs

### Purpose
All non-scenario model parameters. These are structural/operational inputs that define the fleet, contracts, retail portfolio, and liquidity position. Organized in collapsible expanders.

### Expander 1: "Physical Constants & Coal Quality"

**Coal GAR case** — dropdown selector: `GAR 5000 | GAR 5250 (default) | GAR 5500`
Displays the derived calorific value:
- GAR 5000 → 20.934 GJ/t
- GAR 5250 → 21.981 GJ/t
- GAR 5500 → 23.027 GJ/t
Conversion factor: `GJ/t = GAR_kcal_per_kg × 0.0041868`

Other constants (display-only, not editable):
```
MWh_to_GJ = 3.6
MMBtu_to_GJ = 1.055056
MMBtu_per_bbl = 5.8
GJ_per_bbl = 6.1193  (MMBtu_to_GJ × MMBtu_per_bbl)
kWh_per_MWh = 1000
```

### Expander 2: "Season & Weather Stress"

**Season selector** — dropdown: `Hot-dry (default) | Wet | Cool-dry`
Description: "Selects seasonal multipliers for solar/wind/hydro capacity factors and demand uplift. Use Hot-dry for highest stress (peak demand, low hydro); Wet for monsoon conditions; Cool-dry for benign baseline."

Below, display the seasonal multiplier table (read-only, highlighted row = selected):

| Season | Solar mult | Wind mult | Hydro mult | Demand uplift | Character |
|---|---|---|---|---|---|
| **Hot-dry** | 1.02 | 0.95 | 0.85 | 1.05 | Higher temp load; hydro deration risk |
| Wet | 0.80 | 1.05 | 1.10 | 1.00 | Cloud suppresses solar; hydro improves |
| Cool-dry | 0.95 | 1.00 | 0.95 | 0.97 | Lower cooling demand; benign |

**Demand blocks** — editable:

| Block | Base MW | Hours/day | Description |
|---|---|---|---|
| Off-peak | 8500 | 8 | Night trough demand |
| Shoulder | 9700 | 10 | Daytime / evening shoulder |
| Peak | 11600 | 6 | System peak (calibrated so S3 can push to oil marginal) |

Note: Final MW = Base MW × demand_uplift from selected season.

**VRE block-shape calibration** — editable:

| Source | Off-peak | Shoulder | Peak | Description |
|---|---|---|---|---|
| Solar | 0 | 0.35 | 0.05 | Daylight-driven; zero at night |
| Wind | 0.34 | 0.31 | 0.29 | Relatively flat diurnal profile |

**Hydro energy-budget proxy** — editable:

| Setting | Hot-dry | Wet | Cool-dry | Unit | Description |
|---|---|---|---|---|---|
| Hydro budget | 16 | 22 | 18 | GWh/day | Daily hydro energy cap by season |
| Hydro peak MW limit | 1200 | 1500 | 1300 | MW | Max instantaneous hydro output |

**SPC / WESM mitigation** — editable:

| Setting | Default | Description |
|---|---|---|
| SPC toggle | Off (0) | When on, caps block clearing prices at SPC cap |
| SPC cap | 9,000 PHP/MWh | Secondary Price Cap level |

### Expander 3: "MGEN Plant Fleet"

Editable table (3 rows × 6 columns):

| Cluster | Fuel | Capacity (MW) | Availability (%) | Heat Rate (GJ/MWh) | Variable O&M (PHP/MWh) | Base Dispatch (MWh/month) |
|---|---|---|---|---|---|---|
| Coal cluster | Coal | 1,200 | 90% | 9.6 | 260 | 700,000 |
| Gas cluster | Gas/LNG | 1,200 | 88% | 7.2 | 180 | 250,000 |
| Oil peakers | Oil | 300 | 95% | 11.5 | 450 | 10,000 |

Description: "MGEN's own generation fleet. Heat rate determines fuel consumption per MWh. Variable O&M is the non-fuel running cost. Base dispatch is monthly generation volume before scenario adjustments (gas dispatch scales by LNG availability; displaced gas volume shifts to oil)."

Additional input:
- Oil product differential: 10 USD/bbl (description: "Premium of fuel oil product over Brent crude; used in oil peaker SRMC")

### Expander 4: "Luzon WESM Stack (System-Level)"

Description: "Technology stack representing the Luzon interconnected grid. Used to build the merit-order model that determines WESM clearing prices. MGEN's fleet is a subset of this stack. Dependable capacities based on DOE 2024 data."

Editable table:

| Cluster | Dep. MW | Tech Avail % | Off-pk profile | Shoulder profile | Peak profile | Scenario driver | SRMC anchor |
|---|---|---|---|---|---|---|---|
| Solar | 1,674 | 98% | (from VRE shape) | (from VRE shape) | (from VRE shape) | Solar mult | 0 / 0 / 0 / 0 |
| Wind | 337 | 95% | (from VRE shape) | (from VRE shape) | (from VRE shape) | Wind mult | 0 / 0 / 0 / 0 |
| Geothermal | 714 | 92% | 1.0 | 1.0 | 1.0 | — | 600 / 650 / 700 / 800 |
| Biomass | 145 | 85% | 1.0 | 1.0 | 1.0 | — | 1,200 / 1,250 / 1,300 / 1,400 |
| Hydro | 2,382 | 93% | 0.6 | 0.45 | 0.5 | Hydro mult + budget | 1,500 / 1,600 / 1,900 / 2,300 |
| ESS | 341 | 95% | 0.05 | 0.10 | 0.25 | — | 3,000 / 3,200 / 3,500 / 4,200 |
| Coal (system) | 8,589 | 92% | 1.0 | 1.0 | 1.0 | — | → Linked to coal SRMC calc |
| Gas (system) | 3,281 | 88% | 1.0 | 1.0 | 1.0 | LNG_Availability | → Linked to gas SRMC calc |
| Oil (system) | 1,648 | 95% | 1.0 | 1.0 | 1.0 | — | → Linked to oil SRMC calc |

Note: SRMC anchors for Solar/Wind/Geo/Bio/Hydro/ESS are placeholder market proxies (editable). Coal/Gas/Oil SRMC are computed from the fuel landing chain and cannot be overridden here.

### Expander 5: "LNG Terminal Fees"

Editable table (intermediate fuel landing inputs):

| Component | Unit | Base | S1 | S2 | S3 | Description |
|---|---|---|---|---|---|---|
| Regas / terminal fee | USD/MMBtu | 0.9 | 1.0 | 1.1 | 1.3 | Regasification and terminal throughput charge |
| Delay / demurrage | USD/MMBtu | 0 | 0 | 0.3 | 0.8 | Vessel waiting / demurrage cost due to port congestion |

### Expander 6: "Supply & Wholesale Contracts"

| Input | Default | Unit | Description |
|---|---|---|---|
| BCQ volume | 300,000 | MWh/month | Bilateral contract quantity — fixed-price volume sold to offtakers. Exposed to WESM-vs-contract price gap. |
| BCQ sell price | 5,800 | PHP/MWh | Contracted bilateral selling price. When WESM rises above this, BCQ margin turns negative (selling cheap, buying dear). |
| Spot sales volume | 120,000 | MWh/month | Volume sold at WESM spot prices. Benefits from WESM price rises but exposed to SRMC increases. |
| Imbalance volume | 30,000 | MWh/month | Net imbalance exposure (purchase volume when short). Priced at WESM, costed against reference price. |
| Imbalance reference price | 5,900 | PHP/MWh | Reference settlement price for imbalance obligations. |
| Repricing beta | 0.30 | fraction | Share of WESM price shock recoverable through contract repricing clauses. 0 = fully fixed; 1 = fully indexed. |
| Wholesale opex | 50 | PHP mn/month | Monthly wholesale trading and operations cost. |

### Expander 7: "Retail Portfolio"

Editable table (3 segments × 10 columns):

| Segment | Volume (MWh/mo) | Base Tariff (PHP/kWh) | WESM Link (x) | Pass-through % | Bad Debt Base % | Attrition S1 % | Attrition S2 % | Attrition S3 % | Opex (PHP mn/mo) |
|---|---|---|---|---|---|---|---|---|---|
| Fixed C&I | 250,000 | 7.2 | 1.00 | 20% | 1.0% | 1.0% | 3.0% | 6.0% | 35 |
| Indexed C&I | 180,000 | 6.8 | 0.95 | 80% | 0.7% | 0.5% | 1.5% | 3.0% | 20 |
| Other Retail | 120,000 | 6.2 | 0.90 | 30% | 1.5% | 0.5% | 2.0% | 4.0% | 15 |

Column descriptions (show as header tooltips):
- **Volume**: Monthly retail sales volume by segment
- **Base Tariff**: Contract tariff charged to customers (PHP/kWh)
- **WESM Link**: Procurement cost = WESM price × this multiplier (1.0 = full WESM exposure)
- **Pass-through**: Fraction of procurement cost increase above base that can be passed to customer via tariff adjustment
- **Bad Debt Base**: Base-case non-collection rate
- **Attrition S1/S2/S3**: Volume loss from customer churn under each scenario
- **Opex**: Segment-specific monthly operating expenses

### Expander 8: "Liquidity Position & Working Capital"

| Input | Default | Unit | Description |
|---|---|---|---|
| Coal inventory days | 20 | days | On-hand coal stockpile buffer |
| Gas inventory days | 10 | days | LNG working stock days |
| Oil inventory days | 7 | days | Oil product inventory days |
| Coal payables days | 15 | days | Supplier payment terms (offset to inventory) |
| Gas payables days | 0 | days | LNG payment terms |
| Oil payables days | 5 | days | Oil payment terms |
| LC margin — Base | 20% | % | Letter-of-credit / collateral margin requirement |
| LC margin — 30d | 25% | % | Margin under 30-day stress |
| LC margin — 90d | 30% | % | Margin under 90-day stress |
| LC margin — 180d | 35% | % | Margin under 180-day stress |
| Starting cash | 10,000 | PHP mn | Opening cash position |
| Undrawn facilities | 15,000 | PHP mn | Committed but undrawn credit lines |
| Minimum cash buffer | 2,000 | PHP mn | Board-mandated liquidity floor |
| Debt service | 300 | PHP mn/month | Monthly principal + interest payments |
| Net debt | 40,000 | PHP mn | Outstanding net debt for covenant calculations |
| Base EBITDA (annual) | 18,000 | PHP mn | Full-year baseline EBITDA |
| Covenant max ND/EBITDA | 4.5 | x | Maximum net debt / EBITDA ratio before covenant breach |

### Expander 9: "AGRA Regulatory Recovery"

Description: "Models the AGRA-style generation charge adjustment, recovery, and disallowance cycle. Controls how incremental fuel costs under stress are billed, deferred, and potentially refunded."

Editable table (4 columns: Base / 30d / 90d / 180d):

| Parameter | Base | 30d | 90d | 180d | Description |
|---|---|---|---|---|---|
| Immediate recovery % | 100% | 90% | 75% | 60% | Share of monthly gen cost shock billed and collected immediately |
| Disallowance % | 0.5% | 1.0% | 2.0% | 4.0% | Share flagged for potential refund after ERC verification |
| Collection lag | 30 | 30 | 30 | 30 | Days between billing and cash receipt |
| Refund lag | 1 | 1 | 1 | 1 | Months before refunds start being paid out |
| True-up horizon | 36 | 36 | 36 | 36 | Months over which deferred regulatory receivable amortizes |
| Carrying cost p.a. | 7% | 7% | 7% | 7% | Annual interest on deferred regulatory receivable balance |

### Expander 10: "Trigger Playbook"

Editable table (6 triggers):

| Trigger | Operator | Current Level | Threshold | Unit | Duration Actual (days) | Duration Threshold (days) | Action |
|---|---|---|---|---|---|---|---|
| Brent | > | 93.04 | 110 | USD/bbl | 5 | 3 | Activate hedging review / revise procurement cover |
| JKM | > | 15.71 | 20 | USD/MMBtu | 6 | 5 | Review gas dispatch / emergency LNG sourcing |
| USD/PHP | > | 59.05 | 58 | PHP/USD | 4 | 3 | Reassess FX hedging / collateral plan |
| WESM | > | 9,500 | 9,000 | PHP/MWh | 3 | 2 | Retail repricing review / reserve bidding posture |
| Gas availability | < | 0.75 | 0.80 | % | 7 | 5 | Activate alternate dispatch / oil backup plan |
| Coal delay | > | 10 | 7 | days | 4 | 2 | Increase inventory buffer / alternate logistics |

Description: "Status = TRIGGERED when (level breaches threshold in operator direction) AND (duration actual ≥ duration threshold). Otherwise Monitor."

---

## 6. Tab 3 — Results & Dashboard

### Purpose
The primary output view. Replicates the `60_Outputs` Excel sheet as a live dashboard with charts. User can copy/download all output data.

### Layout

**Top: Model status banner**
Run all checks from §7. If all pass → green bar: "✓ MODEL OK — all 15 checks pass". If any fail → red bar listing failures.

**Section A: Scenario Matrix (read-only summary table)**

Use custom-named scenario columns from Tab 1.

| Variable | Unit | {Base name} | {S1 name} | {S2 name} | {S3 name} |
|---|---|---|---|---|---|
| Duration | days | 0 | 30 | 120 | 180 |
| Brent | USD/bbl | 72.48 | 80 | 95 | 135 |
| JKM | USD/MMBtu | 10.725 | 12.334 | 15.551 | 23.059 |
| Newcastle | USD/t | 115.8 | 124.485 | 141.855 | 167.91 |
| FX | PHP/USD | 57.741 | 58.896 | 60.34 | 62.36 |
| Coal freight | USD/t | 10 | 11.5 | 14.5 | 19.5 |
| LNG basis | USD/MMBtu | 0 | 0.5 | 2 | 5 |
| LNG availability | % | 100% | 97% | 85% | 70% |
| Coal delay | days | 0 | 5 | 14 | 28 |

**Section B: Generation Sensitivity**

Table:
| Metric | Unit | Base | S1 | S2 | S3 |
|---|---|---|---|---|---|
| Coal SRMC | PHP/MWh | — | — | — | — |
| Gas SRMC | PHP/MWh | — | — | — | — |
| Oil SRMC | PHP/MWh | — | — | — | — |
| WESM Avg Luzon | PHP/MWh | — | — | — | — |
| Reserve Price | PHP/MW-h | — | — | — | — |
| Generation Gross Margin | PHP mn/month | — | — | — | — |

**Chart B1**: Grouped bar chart — SRMC by fuel type across scenarios (3 clusters × 4 bars).
**Chart B2**: Line chart — WESM price escalation across scenarios with coal/gas/oil SRMC bands.

**Section C: Supply & Retail Margin Sensitivity**

Table:
| Segment | Unit | Base | S1 | S2 | S3 |
|---|---|---|---|---|---|
| BCQ Exposure | PHP mn/month | — | — | — | — |
| Spot Sales | PHP mn/month | — | — | — | — |
| Retail Fixed C&I EBIT | PHP mn/month | — | — | — | — |
| Portfolio Retail EBIT | PHP mn/month | — | — | — | — |
| Supply & Wholesale Margin | PHP mn/month | — | — | — | — |

**Chart C1**: Waterfall chart — margin bridge from Base to S3 (drivers: BCQ/WESM effect, Spot/WESM effect, Fuel/SRMC effect, Imbalance effect, Repricing recovery).
**Chart C2**: Stacked bar chart — retail EBIT by segment across scenarios.

**Section D: Liquidity Stress Structure**

Note: column headers change to Base / 30 Days / 90 Days / 180 Days.

Table:
| Metric | Unit | Base | 30 Days | 90 Days | 180 Days |
|---|---|---|---|---|---|
| Working Capital | PHP mn | — | — | — | — |
| LC Requirements | PHP mn | — | — | — | — |
| Cash Balance | PHP mn | — | — | — | — |
| Covenant Headroom | PHP mn | — | — | — | — |
| Liquidity Runway | days | — | — | — | — |
| Regulatory Receivable | PHP mn | — | — | — | — |
| Immediate Recovery % | % | — | — | — | — |
| Refund Provision | PHP mn | — | — | — | — |

Color rules: Cash Balance and Covenant Headroom cells → green if > 0, red if ≤ 0. Liquidity Runway → red if < 90 days.

**Chart D1**: Stacked bar chart — liquidity uses (Working Capital + LC + Debt Service + Regulatory Receivable + Refund) vs. starting liquidity line.
**Chart D2**: Gauge or bullet chart — liquidity runway in days (thresholds: green > 180, yellow 90–180, red < 90).

**Section E: Trigger Matrix**

Table:
| Trigger | Current | Threshold | Status | Action | Duration | Dur. Threshold |
|---|---|---|---|---|---|---|
Row styling: "TRIGGERED" rows → light red background `#FFEBEE`, "Monitor" rows → white.

**Bottom: Download controls**

Two buttons:
1. **"📋 Copy to clipboard"** — copies the Section A–E tables as tab-separated text (pasteable into Excel).
2. **"⬇️ Download Results (.xlsx)"** — generates a single-sheet Excel file with all 5 output tables using `openpyxl`, formatted with Bain-style headers. Trigger `st.download_button`.

---

## 7. Tab 4 — Intermediate Calculations

### Purpose
Expose every calculation step for auditability. Organized as sub-tabs mirroring the Excel workbook structure. User can download the entire set as an Excel "data pack".

### Sub-tab layout
```python
sub1, sub2, sub3, sub4, sub5, sub6, sub7, sub8, sub9 = st.tabs([
    "Fuel Landing", "Plant SRMC", "Merit Order",
    "Reserve Pricing", "Gen Margin", "Wholesale Margin",
    "Margin Bridge", "Retail EBIT", "Liquidity Model"
])
```

Each sub-tab displays a styled table mirroring the Excel sheet's layout (Metric | Unit | Base | S1 | S2 | S3 or Base | 30d | 90d | 180d).

**Sub-tab: Fuel Landing (10_FuelLanding)**
Show full coal/LNG/oil landing cost build-up chain.

**Sub-tab: Plant SRMC (12_PlantSRMC)**
Show coal/gas/oil SRMC decomposition + dispatch volumes + weighted fleet SRMC.

**Sub-tab: Merit Order (13_MeritOrder_WESM)**
Show demand blocks, clearing prices, marginal clusters.
**Chart**: Stepped area / stacked bar merit-order curve (x = cumulative MW, y = SRMC) with demand lines overlaid. One chart per scenario or a scenario selector dropdown.

**Sub-tab: Reserve Pricing (14_ReservePricing)**
Show WESM → alpha → scarcity → reserve price → revenue chain.

**Sub-tab: Gen Margin (15_GenMargin)**
Show per-fuel margin and total.

**Sub-tab: Wholesale Margin (21_SupplyWholesale_Margin)**
Show BCQ/spot/imbalance/repricing decomposition.

**Sub-tab: Margin Bridge (22_MarginBridge)**
Show bridge table + reconciliation status.
**Chart**: Waterfall chart for each scenario.

**Sub-tab: Retail EBIT (31_Retail_EBIT)**
Show per-segment build-up: volume → procurement → tariff → revenue → cost → bad debt → EBIT.

**Sub-tab: Liquidity Model (41_Liquidity_Model)**
Show full model including AGRA regulatory recovery engine.

### Download: Data Pack

**"⬇️ Download Full Data Pack (.xlsx)"** button at the top of Tab 4.

Generates a multi-sheet Excel workbook matching the original Excel structure:
- Sheet `00_ReadMe` — model description
- Sheet `01_Constants` — physical constants
- Sheet `02_Inputs_Base` — base operating inputs + seasonality
- Sheet `03_Scenarios` — scenario matrix
- Sheet `04_HorizonMap` — horizon → scenario mapping
- Sheet `10_FuelLanding` — fuel cost chain
- Sheet `11_Plants` — plant assumptions
- Sheet `12_PlantSRMC` — SRMC build-up
- Sheet `13_MeritOrder_WESM` — merit order stack + clearing
- Sheet `14_ReservePricing` — reserve pricing
- Sheet `15_GenMargin` — generation margin
- Sheet `20_SupplyWholesale_Contracts` — contract inputs
- Sheet `21_SupplyWholesale_Margin` — wholesale margin
- Sheet `22_MarginBridge` — margin bridge + reconciliation
- Sheet `30_Retail_Inputs` — retail portfolio
- Sheet `31_Retail_EBIT` — retail EBIT
- Sheet `40_Liquidity_Inputs` — liquidity inputs
- Sheet `41_Liquidity_Model` — liquidity model
- Sheet `50_Triggers_Playbook` — trigger matrix
- Sheet `60_Outputs` — deck-ready outputs
- Sheet `99_Checks` — model checks

Each sheet should have:
- Row 1: sheet title (bold)
- Row 2: description
- Row 4+: headers (bold) + data
- Column A frozen
- Number formatting matching the original (2 decimal for prices, 0 for volumes, 1 for PHP mn)

---

## 8. Calculation Engine — Complete Specification

All calculations operate over 4 columns: **[Base, S1, S2, S3]**. Use numpy arrays of shape (4,). The engine function signature:

```python
def run_model(scenarios, base_inputs, plants, system_stack, fuel_intermediates,
              contracts, retail, liquidity, agra, triggers, season_config) -> dict:
    """Returns dict with keys for every intermediate and final output table."""
```

### 8.1 Constants

```python
MWh_to_GJ = 3.6
MMBtu_to_GJ = 1.055056
MMBtu_per_bbl = 5.8
GJ_per_bbl = MMBtu_to_GJ * MMBtu_per_bbl  # 6.1193
kWh_per_MWh = 1000
GAR_to_GJ_factor = 0.0041868
```

### 8.2 Seasonality

```python
solar_mult, wind_mult, hydro_mult, demand_uplift = season_table[selected_season]

off_peak_mw = demand_blocks.off_peak_base * demand_uplift
shoulder_mw = demand_blocks.shoulder_base * demand_uplift
peak_mw     = demand_blocks.peak_base * demand_uplift

solar_cf = (hours_off*solar_shape_off + hours_shldr*solar_shape_shldr + hours_peak*solar_shape_peak) / 24 * solar_mult
wind_cf  = (hours_off*wind_shape_off  + hours_shldr*wind_shape_shldr  + hours_peak*wind_shape_peak)  / 24 * wind_mult

hydro_budget_gwh = hydro_budget_table[selected_season]
hydro_peak_limit = hydro_peak_table[selected_season]

raw_hydro_energy = hydro_dep_mw * hydro_avail * hydro_mult * (off_profile*hours_off + shldr_profile*hours_shldr + peak_profile*hours_peak)
hydro_budget_scale = min(1.0, hydro_budget_gwh * 1000 / raw_hydro_energy) if raw_hydro_energy > 0 else 1.0
```

### 8.3 Fuel Landing (10_FuelLanding)

For each scenario index `s` in [0=Base, 1=S1, 2=S2, 3=S3]:

```python
# Coal
coal_landed_usd_t[s] = newcastle[s] + freight[s] + insurance[s] + logistics[s]
coal_landed_php_t[s] = coal_landed_usd_t[s] * fx[s]
coal_landed_php_gj[s] = coal_landed_php_t[s] / selected_coal_cv

# LNG
delivered_lng_usd[s] = jkm[s] + des_basis[s]
lng_landed_php_mmbtu[s] = (delivered_lng_usd[s] + regas[s] + delay[s]) * fx[s]

# Oil
oil_landed_usd_bbl[s] = brent[s] + oil_product_diff
oil_landed_php_bbl[s] = oil_landed_usd_bbl[s] * fx[s]
oil_fuel_php_gj[s] = oil_landed_php_bbl[s] / MMBtu_per_bbl  # Excel: =C26/C27 where C27='01_Constants'!B6=5.8
```

### 8.4 Plant SRMC (12_PlantSRMC)

```python
# Coal
coal_fuel_cost[s] = coal_heat_rate * coal_landed_php_gj[s]  # GJ/MWh × PHP/GJ
coal_srmc[s] = coal_fuel_cost[s] + coal_vom

# Gas
gas_heat_rate_mmbtu = gas_heat_rate_gj / MMBtu_to_GJ  # convert GJ/MWh → MMBtu/MWh
gas_fuel_cost[s] = gas_heat_rate_mmbtu * lng_landed_php_mmbtu[s]
gas_srmc[s] = gas_fuel_cost[s] + gas_vom

# Oil
oil_fuel_cost_mwh[s] = oil_heat_rate * oil_fuel_php_gj[s]
oil_srmc[s] = oil_fuel_cost_mwh[s] + oil_vom

# Dispatch (MGEN fleet)
coal_dispatch[s] = base_coal_dispatch  # constant
gas_dispatch[s]  = base_gas_dispatch * lng_availability[s]
oil_dispatch[s]  = base_oil_dispatch + (base_gas_dispatch - gas_dispatch[s])  # displaced gas → oil
total_dispatch[s] = coal_dispatch[s] + gas_dispatch[s] + oil_dispatch[s]

weighted_fleet_srmc[s] = (coal_srmc[s]*coal_dispatch[s] + gas_srmc[s]*gas_dispatch[s] + oil_srmc[s]*oil_dispatch[s]) / total_dispatch[s]
```

### 8.5 Merit Order / WESM (13_MeritOrder_WESM)

Build the 9-cluster Luzon supply stack per scenario. Stack order (fixed): Solar → Wind → Geothermal → Biomass → Hydro → ESS → Coal → Gas → Oil.

For each scenario `s` and each demand block `b` ∈ {off-peak, shoulder, peak}:

```python
# Available MW per cluster
for each cluster i:
    avail_mw[i][b][s] = dep_mw[i] * tech_avail[i] * profile[i][b] * seasonal_factor[i] * scenario_factor[i][s]

# Special cluster rules:
#   Solar: seasonal_factor = solar_mult, scenario_factor = 1.0
#   Wind:  seasonal_factor = wind_mult,  scenario_factor = 1.0
#   Hydro: avail_mw = MIN(dep*avail*profile*hydro_mult*hydro_budget_scale, hydro_peak_limit)
#   Gas:   scenario_factor = lng_availability[s]
#   All others: seasonal_factor = 1.0, scenario_factor = 1.0

# Cumulative MW
cum_mw[0][b][s] = avail_mw[0][b][s]
for i in 1..8:
    cum_mw[i][b][s] = cum_mw[i-1][b][s] + avail_mw[i][b][s]

# Find marginal cluster index for each block
demand = [off_peak_mw, shoulder_mw, peak_mw]
for block b:
    marginal_idx[b][s] = first i where cum_mw[i][b][s] >= demand[b]
    if no cluster clears → marginal_idx = 8 (Oil, last in stack)

# SRMC array per scenario
srmc_array[s] = [solar_srmc[s], wind_srmc[s], geo_srmc[s], bio_srmc[s],
                 hydro_srmc[s], ess_srmc[s], coal_srmc[s], gas_srmc[s], oil_srmc[s]]
# Note: coal/gas/oil entries link to 12_PlantSRMC; others are the editable anchors

# Clearing price per block
clearing[b][s] = srmc_array[s][marginal_idx[b][s]]
if spc_toggle == 1:
    clearing[b][s] = min(clearing[b][s], spc_cap)

# Weighted average pre-uplift
weighted_pre[s] = (clearing[off]*hours_off + clearing[shldr]*hours_shldr + clearing[peak]*hours_peak) / 24

# WESM average (LWAP proxy)
wesm_avg[s] = weighted_pre[s] * (1 + bid_uplift[s])

# Peak adequacy buffer
peak_buffer[s] = cum_mw[8][peak][s] - peak_mw
peak_scarcity[s] = peak_mw / cum_mw[8][peak][s] if cum_mw[8][peak][s] > 0 else 0
```

### 8.6 Reserve Pricing (14_ReservePricing)

```python
reserve_requirement = 1458  # MW constant
scarcity_mult[s] = max(1, 1 + max(0, -peak_buffer[s]) / reserve_requirement)
reserve_price[s] = wesm_avg[s] * reserve_alpha[s] * scarcity_mult[s]
reserve_revenue[s] = reserve_price[s] * reserve_volume / 1_000_000
```

### 8.7 Generation Gross Margin (15_GenMargin)

```python
coal_margin[s] = (wesm_avg[s] - coal_srmc[s]) * coal_dispatch[s] / 1_000_000
gas_margin[s]  = (wesm_avg[s] - gas_srmc[s])  * gas_dispatch[s]  / 1_000_000
oil_margin[s]  = (wesm_avg[s] - oil_srmc[s])  * oil_dispatch[s]  / 1_000_000
energy_margin[s] = coal_margin[s] + gas_margin[s] + oil_margin[s]
total_gen_margin[s] = energy_margin[s] + reserve_revenue[s]
```

### 8.8 Supply & Wholesale Margin (21_SupplyWholesale_Margin)

```python
bcq_margin[s] = (bcq_price - wesm_avg[s]) * bcq_vol / 1e6
spot_margin[s] = (wesm_avg[s] - weighted_fleet_srmc[s]) * spot_vol / 1e6
imbalance[s] = -(wesm_avg[s] - imb_ref_price) * imb_vol / 1e6
repricing[s] = ((wesm_avg[s] - wesm_avg[0]) * beta * bcq_vol / 1e6) if wesm_avg[s] > wesm_avg[0] else 0
total_sw_margin[s] = bcq_margin[s] + spot_margin[s] + imbalance[s] + repricing[s] - wholesale_opex
```

### 8.9 Margin Bridge (22_MarginBridge)

For each scenario s in [S1, S2, S3]:

```python
base_margin = total_sw_margin[0]
dW = wesm_avg[s] - wesm_avg[0]
dS = weighted_fleet_srmc[s] - weighted_fleet_srmc[0]

bridge = {
    "Base margin": base_margin,
    "BCQ / WESM effect": -dW * bcq_vol / 1e6,
    "Spot / WESM effect": dW * spot_vol / 1e6,
    "Fuel / SRMC effect": -dS * spot_vol / 1e6,
    "Imbalance effect": -dW * imb_vol / 1e6,
    "Repricing recovery": repricing[s],
}
bridge_total = sum(bridge.values())
reconciliation = total_sw_margin[s] - bridge_total  # should be ~0
```

### 8.10 Retail EBIT (31_Retail_EBIT)

For each segment `seg` and scenario `s`:

```python
attrition = [0, seg.attrition_s1, seg.attrition_s2, seg.attrition_s3]
volume[s] = seg.volume * (1 - attrition[s])
procurement[s] = wesm_avg[s] * seg.wesm_link
base_procurement = wesm_avg[0] * seg.wesm_link

tariff[s] = seg.base_tariff + seg.pass_through * max(0, procurement[s] - base_procurement) / 1000

revenue[s] = volume[s] * 1000 * tariff[s] / 1e6   # MWh × kWh/MWh × PHP/kWh / 1M
energy_cost[s] = volume[s] * procurement[s] / 1e6
bad_debt[s] = revenue[s] * seg.bad_debt_base * bad_debt_mult[s]
ebit[s] = revenue[s] - energy_cost[s] - bad_debt[s] - seg.opex

portfolio_ebit[s] = sum of all segment ebit[s]
```

### 8.11 Liquidity Model (41_Liquidity_Model)

Horizon mapping: h ∈ [0=Base, 1=30d→S1, 2=90d→S2, 3=180d→S3]. Horizon months: [0, 1, 3, 6].

```python
months = [0, 1, 3, 6]

# Fuel spend — IMPORTANT: uses specific cost components, not full SRMC
coal_fuel_spend[h] = coal_dispatch[h] * coal_vom / 1e6          # ='12_PlantSRMC'!C31*C10
gas_fuel_spend[h]  = gas_dispatch[h] * gas_fuel_cost[h] / 1e6   # ='12_PlantSRMC'!C32*C19
oil_fuel_spend[h]  = oil_dispatch[h] * oil_fuel_cost_mwh[h] / 1e6  # ='12_PlantSRMC'!C33*C26
total_fuel[h] = coal_fuel_spend[h] + gas_fuel_spend[h] + oil_fuel_spend[h]

# Working capital
coal_wc_days[h] = coal_inv_days + coal_delay[h] - coal_pay_days
coal_wc[h] = coal_fuel_spend[h] / 30 * coal_wc_days[h]
gas_wc_days = gas_inv_days - gas_pay_days  # constant
gas_wc[h] = gas_fuel_spend[h] / 30 * gas_wc_days
oil_wc_days = oil_inv_days - oil_pay_days  # constant
oil_wc[h] = oil_fuel_spend[h] / 30 * oil_wc_days
working_capital[h] = coal_wc[h] + gas_wc[h] + oil_wc[h]

# LC
lc_margin = [lc_base, lc_30d, lc_90d, lc_180d]
lc_req[h] = total_fuel[h] * lc_margin[h]

# Operating contribution
op_contrib[h] = total_gen_margin[h] + total_sw_margin[h] + portfolio_ebit[h]
cf_compression[h] = op_contrib[0] - op_contrib[h]

# AGRA regulatory recovery
incr_gen_cost[h] = max(0, total_fuel[h] - total_fuel[0])
monthly_billed[h] = incr_gen_cost[h] * immediate_recovery[h]
monthly_deferred[h] = incr_gen_cost[h] * (1 - immediate_recovery[h])
monthly_refund[h] = incr_gen_cost[h] * disallowance[h]

roll_fwd[h] = 1 - 1/true_up_horizon[h] + carrying_cost[h]/12
if months[h] == 0:
    reg_receivable[h] = 0
elif abs(roll_fwd[h] - 1) < 1e-6:
    reg_receivable[h] = monthly_deferred[h] * months[h]
else:
    reg_receivable[h] = monthly_deferred[h] * ((roll_fwd[h]**months[h]) - 1) / (roll_fwd[h] - 1)

refund_cum[h] = monthly_refund[h] * max(0, months[h] - refund_lag[h])

# Liquidity
starting_liq = starting_cash + undrawn_facilities
debt_svc_cum[h] = months[h] * debt_service_monthly

cash_balance[h] = starting_liq - working_capital[h] - lc_req[h] - cf_compression[h]*months[h] - debt_svc_cum[h] - reg_receivable[h] - refund_cum[h]

# Covenant
stress_ebitda[h] = base_ebitda + (op_contrib[h] - op_contrib[0]) * 12
max_nd[h] = stress_ebitda[h] * covenant_max
covenant_headroom[h] = max_nd[h] - net_debt

# Runway
buffer_headroom[h] = cash_balance[h] - min_cash_buffer
monthly_burn = cf_compression[h] + debt_service_monthly + monthly_deferred[h] + monthly_refund[h]
if monthly_burn > 0:
    runway_days[h] = (buffer_headroom[h] / monthly_burn) * 30 if buffer_headroom[h] > 0 else 0
else:
    runway_days[h] = 999

# Collection info
collection_months[h] = max(0, months[h] - ceil(collection_lag[h]/30))
cash_collected[h] = monthly_billed[h] * collection_months[h]
```

### 8.12 Trigger Logic (50_Triggers_Playbook)

```python
for trigger in triggers:
    if trigger.operator == ">":
        breached = trigger.current > trigger.threshold
    else:
        breached = trigger.current < trigger.threshold
    trigger.status = "TRIGGERED" if (breached and trigger.duration_actual >= trigger.duration_threshold) else "Monitor"
```

---

## 9. Model Checks

Run these checks and display results on Tab 3 banner and optionally on Tab 4:

| # | Check | Logic | Pass condition |
|---|---|---|---|
| 1 | Scenario inputs complete | Count non-null scenario cells | 56 filled |
| 2 | Coal SRMC positive | min(coal_srmc) | > 0 |
| 3 | Gas availability bounded | all lng_availability in [0,1] | True |
| 4 | Merit order monotonic | coal_srmc ≤ gas_srmc ≤ oil_srmc per scenario | True for all 4 |
| 5 | Bridge ties — S1 | abs(reconciliation_s1) | < 0.01 |
| 6 | Bridge ties — S2 | abs(reconciliation_s2) | < 0.01 |
| 7 | Bridge ties — S3 | abs(reconciliation_s3) | < 0.01 |
| 8 | Retail EBIT sum ties | portfolio_ebit == sum(segment ebits) per scenario | < 0.01 |
| 9 | Base cash above buffer | cash_balance[Base] > min_cash_buffer | True |
| 10 | WESM output links | 60_Outputs WESM == merit_order WESM | Exact |
| 11 | AGRA output links | 60_Outputs reg_receivable == liquidity reg_receivable | Exact |
| 12 | Coal CV propagation | fuel_landing coal_cv == plants selected_cv | < 0.0001 |
| 13 | S3 peak marginal = Oil | marginal_cluster[peak][S3] | == "Oil" |
| 14 | Solar CF anchor | solar_cf ≈ 16% | ±1% |
| 15 | Base LWAP sanity | wesm_avg[Base] in [3500, 5500] | True |

---

## 10. Validation Reference Values

The engine **must reproduce** these values when run with all default inputs (Hot-dry season, GAR 5250):

**Generation:**
| Metric | Base | S1 | S2 | S3 |
|---|---|---|---|---|
| Coal SRMC | 3,445.06 | 3,790.05 | 4,452.94 | 5,527.62 |
| Gas SRMC | 4,760.73 | 5,740.10 | 7,983.69 | 13,014.43 |
| Oil SRMC | 9,892.84 | 10,959.89 | 13,012.16 | 18,378.50 |
| WESM Avg | 4,538.28 | 5,446.39 | 8,870.28 | 13,638.82 |
| Reserve Price | 1,134.57 | 1,524.99 | 3,104.60 | 6,137.47 |
| Gen Gross Margin | 712.82 | 1,068.0 | 3,239.03 | 5,691.11 |

**Supply & Retail:**
| Metric | Base | S1 | S2 | S3 |
|---|---|---|---|---|
| BCQ Exposure | 378.52 | 106.08 | -921.08 | -2,351.65 |
| Spot Sales | 82.01 | 123.97 | 385.47 | 673.03 |
| Portfolio EBIT | 1,259.52 | 966.91 | -93.65 | -1,508.35 |
| S&W Margin | 451.38 | 275.39 | -284.84 | -1,141.73 |

**Liquidity:**
| Metric | Base | 30d | 90d | 180d |
|---|---|---|---|---|
| Working Capital | 418.36 | 522.37 | 707.81 | 1,050.47 |
| LC Requirements | 284.32 | 428.56 | 731.10 | 1,383.18 |
| Cash Balance | 24,297.32 | 23,606.35 | 23,185.98 | 18,214.82 |
| Covenant Headroom | 41,000.00 | 34,873.34 | 64,587.99 | 74,334.02 |
| Runway (days) | 2,229.73 | 1,454.49 | 4,627.87 | 611.07 |
| Reg Receivable | 0.00 | 29.26 | 744.94 | 5,749.24 |
| Refund Provision | 0.00 | 0.00 | 40.62 | 506.07 |

**Triggers (default inputs):**
| Trigger | Status |
|---|---|
| Brent | Monitor |
| JKM | Monitor |
| USD/PHP | TRIGGERED |
| WESM | TRIGGERED |
| Gas availability | TRIGGERED |
| Coal delay | TRIGGERED |

Tolerance for numerical validation: ±0.1 on PHP mn values, ±0.01 on PHP/MWh values.

---

## 11. Technical Requirements

```
# requirements.txt
streamlit>=1.30
openpyxl>=3.1
numpy>=1.24
pandas>=2.0
plotly>=5.18
```

- Use `st.session_state` to persist inputs across tabs.
- All input widgets use `key=` parameters tied to session state.
- Changes in Tab 1 or Tab 2 immediately recompute and update Tab 3 and Tab 4.
- Use `@st.cache_data` on the engine function, keyed on a hash of all inputs.
- Use Plotly for all charts (Bain palette, no gridlines, clean axis labels).
- Excel downloads use `openpyxl` with formatting (bold headers, number formats, column widths).
- The app must be runnable with `streamlit run app.py` with no additional setup.
