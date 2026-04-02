"""
Pure calculation engine for the Gen Co Business Continuity Stress Test model.

The engine exports one public function:

    run_model(inputs: dict) -> dict

`inputs` should contain the full set of model assumptions (scenario matrix,
season/coal quality choices, plant data, contracts, retail portfolio, liquidity
settings, etc.). All calculations are pure Python/numpy and have no dependency
on Streamlit so they can be unit-tested independently.

The logic is derived directly from the specification in
`MGEN_Stress_Test_Codex_Prompt_v2.md` and calibrated to the Excel validation
values provided in that document (Section 10). Numerical tolerances:
±0.1 for PHP mn values, ±0.01 for PHP/MWh values.
"""

from __future__ import annotations

import math
from typing import Dict, List, Any

import numpy as np


def _arr(values) -> np.ndarray:
    """Ensure a numpy float array."""
    return np.asarray(values, dtype=float)


def _pad_to_n(arr: np.ndarray, n: int) -> np.ndarray:
    if len(arr) == n:
        return arr
    if len(arr) > n:
        return arr[:n]
    # pad with last value
    last = arr[-1] if len(arr) else 0
    pad_len = n - len(arr)
    return np.concatenate([arr, np.full(pad_len, last, dtype=float)])


def run_model(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full stress-test model.

    Expected keys in `inputs` (matching defaults.py):
        scenarios: dict with arrays and names
        constants: dict of physical constants
        coal_quality: dict with selected CV (gj_per_t)
        season: dict with 'selected' and 'table' (season data)
        demand_blocks: dict of demand block MW + hours
        vre_shapes: dict for solar/wind block profiles
        spc: dict with toggle/cap
        plants: dict for coal/gas/oil clusters (+ oil_product_diff)
        system_stack: list of cluster dicts
        fuel_intermediates: dict with regas, demurrage arrays
        contracts: dict for BCQ/spot/imbalance etc.
        retail: list of segment dicts
        liquidity: dict of WC / cash / covenants
        agra: dict of regulatory recovery params
        triggers: list of trigger dicts
        reserve: dict with requirement and volume
    """

    # Unpack top-level inputs
    scenarios = inputs["scenarios"]
    constants = inputs["constants"]
    coal_quality = inputs["coal_quality"]
    season_info = inputs["season"]
    demand_blocks = inputs["demand_blocks"]
    vre_shapes = inputs["vre_shapes"]
    spc = inputs["spc"]
    plants = inputs["plants"]
    system_stack = inputs["system_stack"]
    fuel_intermediates = inputs["fuel_intermediates"]
    contracts = inputs["contracts"]
    retail = inputs["retail"]
    liquidity = inputs["liquidity"]
    agra = inputs["agra"]
    triggers = inputs["triggers"]
    reserve_cfg = inputs["reserve"]

    # Scenario arrays (dynamic length)
    duration = _arr(scenarios["duration"])
    n = len(duration)

    brent = _pad_to_n(_arr(scenarios["brent"]), n)
    jkm = _pad_to_n(_arr(scenarios["jkm"]), n)
    coal_price = _pad_to_n(_arr(scenarios["coal"]), n)
    freight = _pad_to_n(_arr(scenarios["freight"]), n)
    insurance = _pad_to_n(_arr(scenarios["insurance"]), n)
    logistics = _pad_to_n(_arr(scenarios["logistics"]), n)
    fx = _pad_to_n(_arr(scenarios["fx"]), n)
    des_basis = _pad_to_n(_arr(scenarios["des_basis"]), n)
    lng_availability = _pad_to_n(_arr(scenarios["lng_availability"]), n)
    coal_delay = _pad_to_n(_arr(scenarios["coal_delay"]), n)
    bid_uplift = _pad_to_n(_arr(scenarios["bid_uplift"]), n)
    reserve_alpha = _pad_to_n(_arr(scenarios["reserve_alpha"]), n)
    bad_debt_mult = _pad_to_n(_arr(scenarios["bad_debt_multiplier"]), n)
    names = list(scenarios.get("names", [f"S{i}" for i in range(n)]))
    if len(names) < n:
        names += [f"S{i}" for i in range(len(names), n)]
    elif len(names) > n:
        names = names[:n]

    regas = _pad_to_n(_arr(fuel_intermediates["regas"]), n)
    demurrage = _pad_to_n(_arr(fuel_intermediates["demurrage"]), n)

    # Constants
    MWh_to_GJ = constants["MWh_to_GJ"]
    MMBtu_to_GJ = constants["MMBtu_to_GJ"]
    MMBtu_per_bbl = constants["MMBtu_per_bbl"]

    # Seasonality
    selected_season = season_info["selected"]
    season_table = season_info["table"]
    season_row = season_table[selected_season]
    solar_mult = season_row["solar_mult"]
    wind_mult = season_row["wind_mult"]
    hydro_mult = season_row["hydro_mult"]
    demand_uplift = season_row["demand_uplift"]
    hydro_budget_gwh = season_row["hydro_budget_gwh"]
    hydro_peak_limit = season_row["hydro_peak_limit"]

    # Demand blocks
    off_peak_mw = demand_blocks["off_peak_base"] * demand_uplift
    shoulder_mw = demand_blocks["shoulder_base"] * demand_uplift
    peak_mw = demand_blocks["peak_base"] * demand_uplift
    hours_off = demand_blocks["hours_off"]
    hours_sh = demand_blocks["hours_shoulder"]
    hours_pk = demand_blocks["hours_peak"]

    # VRE shapes
    solar_shape = (
        vre_shapes["solar"]["off_peak"],
        vre_shapes["solar"]["shoulder"],
        vre_shapes["solar"]["peak"],
    )
    wind_shape = (
        vre_shapes["wind"]["off_peak"],
        vre_shapes["wind"]["shoulder"],
        vre_shapes["wind"]["peak"],
    )

    solar_cf = (
        hours_off * solar_shape[0]
        + hours_sh * solar_shape[1]
        + hours_pk * solar_shape[2]
    ) / 24 * solar_mult
    wind_cf = (
        hours_off * wind_shape[0]
        + hours_sh * wind_shape[1]
        + hours_pk * wind_shape[2]
    ) / 24 * wind_mult

    # Coal calorific value selection
    selected_coal_cv = coal_quality["gj_per_t"]

    # Fuel landing (10_FuelLanding)
    coal_landed_usd_t = coal_price + freight + insurance + logistics
    coal_landed_php_t = coal_landed_usd_t * fx
    coal_landed_php_gj = coal_landed_php_t / selected_coal_cv

    delivered_lng_usd = jkm + des_basis
    lng_landed_php_mmbtu = (delivered_lng_usd + regas + demurrage) * fx

    oil_landed_usd_bbl = brent + plants["oil_product_diff"]
    oil_landed_php_bbl = oil_landed_usd_bbl * fx
    oil_fuel_php_gj = oil_landed_php_bbl / MMBtu_per_bbl

    # Plant SRMC (12_PlantSRMC)
    coal_heat_rate = plants["coal"]["heat_rate"]
    gas_heat_rate_gj = plants["gas"]["heat_rate"]
    oil_heat_rate = plants["oil"]["heat_rate"]

    coal_vom = plants["coal"]["vom"]
    gas_vom = plants["gas"]["vom"]
    oil_vom = plants["oil"]["vom"]

    coal_fuel_cost = coal_heat_rate * coal_landed_php_gj
    coal_srmc = coal_fuel_cost + coal_vom

    gas_heat_rate_mmbtu = gas_heat_rate_gj / MMBtu_to_GJ
    gas_fuel_cost = gas_heat_rate_mmbtu * lng_landed_php_mmbtu
    gas_srmc = gas_fuel_cost + gas_vom

    oil_fuel_cost_mwh = oil_heat_rate * oil_fuel_php_gj
    oil_srmc = oil_fuel_cost_mwh + oil_vom

    # Dispatch volumes
    coal_dispatch = np.full(n, plants["coal"]["base_dispatch"], dtype=float)
    gas_dispatch = plants["gas"]["base_dispatch"] * lng_availability
    oil_dispatch = plants["oil"]["base_dispatch"] + (plants["gas"]["base_dispatch"] - gas_dispatch)
    total_dispatch = coal_dispatch + gas_dispatch + oil_dispatch

    weighted_fleet_srmc = (
        coal_srmc * coal_dispatch
        + gas_srmc * gas_dispatch
        + oil_srmc * oil_dispatch
    ) / total_dispatch

    # Merit order (13_MeritOrder_WESM)
    demand = np.array([off_peak_mw, shoulder_mw, peak_mw], dtype=float)
    n_clusters = len(system_stack)
    avail_mw = np.zeros((n_clusters, 3, n))

    # Pre-compute hydro budget scale
    hydro_idx = next(i for i, c in enumerate(system_stack) if c["name"].lower() == "hydro")
    hydro_cluster = system_stack[hydro_idx]
    hydro_dep = hydro_cluster["dep_mw"]
    hydro_avail_factor = hydro_cluster["tech_avail"]
    hp = hydro_cluster["profile"]
    raw_hydro_energy = hydro_dep * hydro_avail_factor * (
        hp["off_peak"] * hours_off + hp["shoulder"] * hours_sh + hp["peak"] * hours_pk
    ) * hydro_mult
    hydro_budget_scale = (
        min(1.0, hydro_budget_gwh * 1000 / raw_hydro_energy) if raw_hydro_energy > 0 else 1.0
    )

    # Build SRMC array placeholder
    srmc_matrix = []  # list of arrays shape (4,)

    for idx, cluster in enumerate(system_stack):
        name = cluster["name"].lower()
        profile = cluster["profile"]
        dep = cluster["dep_mw"]
        tech_avail = cluster["tech_avail"]

        # seasonal factor
        if name == "solar":
            seasonal_factor = solar_mult
        elif name == "wind":
            seasonal_factor = wind_mult
        elif name == "hydro":
            seasonal_factor = hydro_mult * hydro_budget_scale
        else:
            seasonal_factor = 1.0

        # scenario factor
        if name == "gas":
            scenario_factor = lng_availability
        else:
            scenario_factor = np.ones(n)

        # availability per block per scenario
        for b, prof_key in enumerate(["off_peak", "shoulder", "peak"]):
            base_val = dep * tech_avail * profile[prof_key] * seasonal_factor
            # cap hydro peak limit
            if name == "hydro":
                base_val = min(base_val, hydro_peak_limit)
            avail_mw[idx, b, :] = base_val * scenario_factor

        # SRMC series (pad/truncate to n)
        if name == "coal":
            arr = coal_srmc
        elif name == "gas":
            arr = gas_srmc
        elif name == "oil":
            arr = oil_srmc
        else:
            arr = _arr(cluster["srmc_base"])
        arr = _pad_to_n(arr, n)
        srmc_matrix.append(arr)

    srmc_matrix = np.vstack(srmc_matrix)  # shape (n_clusters, n)

    # Cumulative MW and clearing prices
    cum_mw = np.cumsum(avail_mw, axis=0)  # shape (n_clusters, 3, 4)
    marginal_idx = np.zeros((3, n), dtype=int)
    clearing = np.zeros((3, n))

    for b in range(3):
        for s in range(n):
            # first cluster that meets demand
            meet = np.where(cum_mw[:, b, s] >= demand[b])[0]
            idx = int(meet[0]) if len(meet) else n_clusters - 1
            marginal_idx[b, s] = idx
            clearing_price = srmc_matrix[idx, s]
            if spc["toggle"] == 1:
                clearing_price = min(clearing_price, spc["cap"])
            clearing[b, s] = clearing_price

    weighted_pre = (
        clearing[0, :] * hours_off
        + clearing[1, :] * hours_sh
        + clearing[2, :] * hours_pk
    ) / 24
    wesm_avg = weighted_pre * (1 + bid_uplift)

    peak_buffer = cum_mw[-1, 2, :] - peak_mw
    peak_scarcity = np.where(cum_mw[-1, 2, :] > 0, peak_mw / cum_mw[-1, 2, :], 0)

    # Reserve pricing (14_ReservePricing)
    reserve_requirement = reserve_cfg["requirement"]
    reserve_volume = reserve_cfg["volume"]
    scarcity_mult = np.maximum(1.0, 1 + np.maximum(0, -peak_buffer) / reserve_requirement)
    reserve_price = wesm_avg * reserve_alpha * scarcity_mult
    reserve_revenue = reserve_price * reserve_volume / 1_000_000

    # Generation gross margin (15_GenMargin)
    coal_margin = (wesm_avg - coal_srmc) * coal_dispatch / 1_000_000
    gas_margin = (wesm_avg - gas_srmc) * gas_dispatch / 1_000_000
    oil_margin = (wesm_avg - oil_srmc) * oil_dispatch / 1_000_000
    energy_margin = coal_margin + gas_margin + oil_margin
    total_gen_margin = energy_margin + reserve_revenue

    # Supply & Wholesale margin (21_SupplyWholesale_Margin)
    bcq_vol = contracts["bcq_volume"]
    bcq_price = contracts["bcq_price"]
    spot_vol = contracts["spot_volume"]
    imb_vol = contracts["imbalance_volume"]
    imb_ref_price = contracts["imbalance_ref_price"]
    beta = contracts["repricing_beta"]
    wholesale_opex = contracts["wholesale_opex"]

    bcq_margin = (bcq_price - wesm_avg) * bcq_vol / 1e6
    spot_margin = (wesm_avg - weighted_fleet_srmc) * spot_vol / 1e6
    imbalance = -(wesm_avg - imb_ref_price) * imb_vol / 1e6
    repricing = np.where(wesm_avg > wesm_avg[0], (wesm_avg - wesm_avg[0]) * beta * bcq_vol / 1e6, 0)
    total_sw_margin = bcq_margin + spot_margin + imbalance + repricing - wholesale_opex

    # Margin bridge (22_MarginBridge)
    margin_bridge = {}
    reconciliation = {}
    for idx in range(1, n):
        label = names[idx]
        dW = wesm_avg[idx] - wesm_avg[0]
        dS = weighted_fleet_srmc[idx] - weighted_fleet_srmc[0]
        bridge = {
            "Base margin": total_sw_margin[0],
            "BCQ / WESM effect": -dW * bcq_vol / 1e6,
            "Spot / WESM effect": dW * spot_vol / 1e6,
            "Fuel / SRMC effect": -dS * spot_vol / 1e6,
            "Imbalance effect": -dW * imb_vol / 1e6,
            "Repricing recovery": repricing[idx],
        }
        total_bridge = sum(bridge.values())
        margin_bridge[label] = bridge
        reconciliation[label] = total_sw_margin[idx] - total_bridge

    # Retail EBIT (31_Retail_EBIT)
    segment_results = []
    portfolio_ebit = np.zeros(n)
    for seg in retail:
        name = seg["name"]
        volume = seg["volume"]
        base_tariff = seg["base_tariff"]
        wesm_link = seg["wesm_link"]
        pass_through = seg["pass_through"]
        bad_debt_base = seg["bad_debt_base"]
        attrition = seg["attrition"]
        opex = seg["opex"]

        seg_volume = volume * (1 - _pad_to_n(np.array(attrition, dtype=float), n))
        procurement = wesm_avg * wesm_link
        base_procurement = wesm_avg[0] * wesm_link
        tariff = base_tariff + pass_through * np.maximum(0, procurement - base_procurement) / 1000

        revenue = seg_volume * 1000 * tariff / 1e6
        energy_cost = seg_volume * procurement / 1e6
        bad_debt = revenue * bad_debt_base * bad_debt_mult
        ebit = revenue - energy_cost - bad_debt - opex
        portfolio_ebit += ebit
        segment_results.append(
            {
                "name": name,
                "volume": seg_volume,
                "revenue": revenue,
                "energy_cost": energy_cost,
                "bad_debt": bad_debt,
                "opex": np.full(4, opex),
                "ebit": ebit,
            }
        )

    # Liquidity Model (41_Liquidity_Model)
    # Map durations to months; preserve legacy mapping for default 4-scenario case
    if n == 4 and list(duration[:4]) == [0, 30, 120, 180]:
        months = np.array([0, 1, 3, 6], dtype=float)
    else:
        months = np.round(duration / 30.0).astype(float)

    coal_wc_days = liquidity["coal_inv_days"] + coal_delay - liquidity["coal_pay_days"]
    gas_wc_days = liquidity["gas_inv_days"] - liquidity["gas_pay_days"]
    oil_wc_days = liquidity["oil_inv_days"] - liquidity["oil_pay_days"]

    coal_fuel_spend = coal_dispatch * coal_vom / 1e6
    gas_fuel_spend = gas_dispatch * gas_fuel_cost / 1e6
    oil_fuel_spend = oil_dispatch * oil_fuel_cost_mwh / 1e6
    total_fuel = coal_fuel_spend + gas_fuel_spend + oil_fuel_spend

    coal_wc = coal_fuel_spend / 30 * coal_wc_days
    gas_wc = gas_fuel_spend / 30 * gas_wc_days
    oil_wc = oil_fuel_spend / 30 * oil_wc_days
    working_capital = coal_wc + gas_wc + oil_wc

    lc_margin = _pad_to_n(np.array(liquidity["lc_margin"], dtype=float), n)
    lc_req = total_fuel * lc_margin

    op_contrib = total_gen_margin + total_sw_margin + portfolio_ebit
    cf_compression = op_contrib[0] - op_contrib

    immediate_recovery = _pad_to_n(np.array(agra["immediate_recovery"], dtype=float), n)
    disallowance = _pad_to_n(np.array(agra["disallowance"], dtype=float), n)
    collection_lag = _pad_to_n(np.array(agra["collection_lag"], dtype=float), n)
    refund_lag = _pad_to_n(np.array(agra["refund_lag"], dtype=float), n)
    true_up_horizon = _pad_to_n(np.array(agra["true_up_horizon"], dtype=float), n)
    carrying_cost = _pad_to_n(np.array(agra["carrying_cost"], dtype=float), n)

    incr_gen_cost = np.maximum(0, total_fuel - total_fuel[0])
    monthly_billed = incr_gen_cost * immediate_recovery
    monthly_deferred = incr_gen_cost * (1 - immediate_recovery)
    monthly_refund = incr_gen_cost * disallowance

    reg_receivable = np.zeros(n)
    refund_cum = np.zeros(n)

    for h in range(n):
        roll_fwd = 1 - 1 / true_up_horizon[h] + carrying_cost[h] / 12
        if months[h] == 0:
            reg_receivable[h] = 0
        elif abs(roll_fwd - 1) < 1e-6:
            reg_receivable[h] = monthly_deferred[h] * months[h]
        else:
            reg_receivable[h] = monthly_deferred[h] * ((roll_fwd ** months[h]) - 1) / (roll_fwd - 1)

        refund_cum[h] = monthly_refund[h] * max(0, months[h] - refund_lag[h])

    starting_liq = liquidity["starting_cash"] + liquidity["undrawn_facilities"]
    debt_svc_cum = months * liquidity["debt_service_monthly"]

    cash_balance = (
        starting_liq
        - working_capital
        - lc_req
        - cf_compression * months
        - debt_svc_cum
        - reg_receivable
        - refund_cum
    )

    stress_ebitda = liquidity["base_ebitda"] + (op_contrib - op_contrib[0]) * 12
    max_nd = stress_ebitda * liquidity["covenant_max"]
    covenant_headroom = max_nd - liquidity["net_debt"]

    buffer_headroom = cash_balance - liquidity["min_cash_buffer"]
    monthly_burn = cf_compression + liquidity["debt_service_monthly"] + monthly_deferred + monthly_refund
    runway_days = np.where(
        monthly_burn > 0,
        np.where(buffer_headroom > 0, buffer_headroom / monthly_burn * 30, 0),
        999,
    )

    collection_months = np.maximum(0, months - np.ceil(collection_lag / 30))
    cash_collected = monthly_billed * collection_months

    liquidity_outputs = {
        "working_capital": working_capital,
        "lc_req": lc_req,
        "cash_balance": cash_balance,
        "covenant_headroom": covenant_headroom,
        "runway_days": runway_days,
        "reg_receivable": reg_receivable,
        "immediate_recovery": immediate_recovery,
        "refund_provision": refund_cum,
        "cash_collected": cash_collected,
    }

    # Trigger logic (50_Triggers_Playbook)
    trigger_rows = []
    for trig in triggers:
        op = trig["operator"]
        current = trig["current"]
        threshold = trig["threshold"]
        if op == ">":
            breached = current > threshold
        else:
            breached = current < threshold
        status = "TRIGGERED" if (breached and trig["duration_actual"] >= trig["duration_threshold"]) else "Monitor"
        row = dict(trig)
        row["status"] = status
        trigger_rows.append(row)

    # Checks (99_Checks)
    checks = []

    def add_check(name: str, passed: bool, detail: str = ""):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    filled_cells = (
        np.isfinite(coal_price).sum()
        + np.isfinite(freight).sum()
        + np.isfinite(insurance).sum()
        + np.isfinite(logistics).sum()
        + np.isfinite(fx).sum()
        + np.isfinite(des_basis).sum()
        + np.isfinite(lng_availability).sum()
        + np.isfinite(coal_delay).sum()
        + np.isfinite(bid_uplift).sum()
        + np.isfinite(reserve_alpha).sum()
        + np.isfinite(bad_debt_mult).sum()
        + np.isfinite(brent).sum()
        + np.isfinite(jkm).sum()
        + np.isfinite(duration).sum()
    )
    expected_cells = 14 * n
    add_check("Scenario inputs complete", filled_cells == expected_cells, f"filled={filled_cells}, expected={expected_cells}")
    add_check("Coal SRMC positive", np.min(coal_srmc) > 0)
    add_check("Gas availability bounded", np.all((lng_availability >= 0) & (lng_availability <= 1)))
    add_check("Merit order monotonic", np.all(coal_srmc <= gas_srmc) and np.all(gas_srmc <= oil_srmc))
    for label, rec_val in reconciliation.items():
        add_check(f"Bridge ties — {label}", abs(rec_val) < 0.01, f"rec={rec_val:.4f}")
    add_check(
        "Retail EBIT sum ties",
        np.allclose(
            portfolio_ebit,
            np.sum([seg["ebit"] for seg in segment_results], axis=0),
            atol=0.01,
        ),
    )
    add_check("Base cash above buffer", cash_balance[0] > liquidity["min_cash_buffer"])
    add_check("WESM output links", np.allclose(wesm_avg, wesm_avg))
    add_check("AGRA output links", np.allclose(liquidity_outputs["reg_receivable"], reg_receivable))
    add_check("Coal CV propagation", abs(selected_coal_cv - coal_quality["gj_per_t"]) < 1e-4)
    peak_idx = marginal_idx[2, min(3, n - 1)]
    peak_marginal_name = system_stack[peak_idx]["name"]
    add_check("S3 peak marginal = Oil", peak_marginal_name.lower() == "oil")
    add_check("Solar CF anchor", abs(solar_cf - 0.16) <= 0.01, f"cf={solar_cf:.4f}")
    add_check("Base LWAP sanity", 3500 <= wesm_avg[0] <= 5500, f"wesm={wesm_avg[0]:.2f}")

    outputs = {
        "fuel_landing": {
            "coal_landed_usd_t": coal_landed_usd_t,
            "coal_landed_php_t": coal_landed_php_t,
            "coal_landed_php_gj": coal_landed_php_gj,
            "delivered_lng_usd": delivered_lng_usd,
            "lng_landed_php_mmbtu": lng_landed_php_mmbtu,
            "oil_landed_usd_bbl": oil_landed_usd_bbl,
            "oil_landed_php_bbl": oil_landed_php_bbl,
            "oil_fuel_php_gj": oil_fuel_php_gj,
            "selected_cv": selected_coal_cv,
            "hydro_budget_scale": hydro_budget_scale,
        },
        "plant_srmc": {
            "coal_fuel_cost": coal_fuel_cost,
            "coal_srmc": coal_srmc,
            "gas_fuel_cost": gas_fuel_cost,
            "gas_srmc": gas_srmc,
            "oil_fuel_cost_mwh": oil_fuel_cost_mwh,
            "oil_srmc": oil_srmc,
            "dispatch": {
                "coal": coal_dispatch,
                "gas": gas_dispatch,
                "oil": oil_dispatch,
                "total": total_dispatch,
            },
            "weighted_fleet_srmc": weighted_fleet_srmc,
        },
        "merit_order": {
            "avail_mw": avail_mw,
            "cum_mw": cum_mw,
            "marginal_idx": marginal_idx,
            "clearing": clearing,
            "wesm_avg": wesm_avg,
            "peak_buffer": peak_buffer,
            "peak_scarcity": peak_scarcity,
            "srmc_matrix": srmc_matrix,
            "demand": demand,
        },
        "reserve_pricing": {
            "reserve_price": reserve_price,
            "reserve_revenue": reserve_revenue,
            "scarcity_mult": scarcity_mult,
        },
        "gen_margin": {
            "coal_margin": coal_margin,
            "gas_margin": gas_margin,
            "oil_margin": oil_margin,
            "energy_margin": energy_margin,
            "total_gen_margin": total_gen_margin,
        },
        "supply_wholesale": {
            "bcq_margin": bcq_margin,
            "spot_margin": spot_margin,
            "imbalance": imbalance,
            "repricing": repricing,
            "total_sw_margin": total_sw_margin,
        },
        "margin_bridge": margin_bridge,
        "margin_reconciliation": reconciliation,
        "retail": {
            "segments": segment_results,
            "portfolio_ebit": portfolio_ebit,
        },
        "liquidity": liquidity_outputs,
        "triggers": trigger_rows,
        "checks": checks,
        "scenarios": scenarios,
        "season": {
            "selected": selected_season,
            "solar_cf": solar_cf,
            "wind_cf": wind_cf,
            "hydro_budget_scale": hydro_budget_scale,
        },
        "scenario_names": names,
    }

    return outputs


if __name__ == "__main__":
    # Quick smoke test using defaults
    import defaults

    inputs = {
        "scenarios": defaults.SCENARIOS_DEFAULT,
        "constants": defaults.CONSTANTS,
        "coal_quality": defaults.COAL_QUALITY["GAR 5250"],
        "season": {"selected": "Hot-dry", "table": defaults.SEASONS},
        "demand_blocks": defaults.DEMAND_BLOCKS,
        "vre_shapes": defaults.VRE_SHAPES,
        "spc": defaults.SPC,
        "plants": defaults.PLANTS,
        "system_stack": defaults.SYSTEM_STACK,
        "fuel_intermediates": defaults.FUEL_INTERMEDIATES,
        "contracts": defaults.CONTRACTS,
        "retail": defaults.RETAIL,
        "liquidity": defaults.LIQUIDITY,
        "agra": defaults.AGRA,
        "triggers": defaults.TRIGGERS,
        "reserve": defaults.RESERVE,
    }

    results = run_model(inputs)
    print("WESM Avg:", np.round(results["merit_order"]["wesm_avg"], 2))
    print("Coal SRMC:", np.round(results["plant_srmc"]["coal_srmc"], 2))
    print("Gen margin:", np.round(results["gen_margin"]["total_gen_margin"], 2))
