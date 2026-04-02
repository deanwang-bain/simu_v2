"""
Default input values for Gen Co Stress Test Model
All values calibrated to Excel reference model
"""

import numpy as np

# Scenario defaults (14 variables × 4 scenarios)
SCENARIOS_DEFAULT = {
    'names': ['Base', 'Scenario 1', 'Scenario 2', 'Scenario 3'],
    'duration': np.array([0, 30, 120, 180]),
    'brent': np.array([72.48, 80.0, 95.0, 135.0]),
    'jkm': np.array([10.725, 12.334, 15.551, 23.059]),
    'coal': np.array([115.8, 124.485, 141.855, 167.91]),
    'freight': np.array([10.0, 11.5, 14.5, 19.5]),
    'insurance': np.array([0.5, 0.75, 1.25, 2.0]),
    'logistics': np.array([0.0, 0.5, 1.5, 4.0]),
    'fx': np.array([57.741, 58.896, 60.34, 62.36]),
    'des_basis': np.array([0.0, 0.5, 2.0, 5.0]),
    'lng_availability': np.array([1.00, 0.97, 0.85, 0.70]),
    'coal_delay': np.array([0, 5, 14, 28]),
    'bid_uplift': np.array([0.05, 0.07, 0.10, 0.15]),
    'reserve_alpha': np.array([0.25, 0.28, 0.35, 0.45]),
    'bad_debt_multiplier': np.array([1.0, 1.05, 1.15, 1.30]),
}

# Physical constants
CONSTANTS = {
    'MWh_to_GJ': 3.6,
    'MMBtu_to_GJ': 1.055056,
    'MMBtu_per_bbl': 5.8,
    'GJ_per_bbl': 6.1193,
    'kWh_per_MWh': 1000,
    'GAR_to_GJ_factor': 0.0041868,
}

# Coal quality options
COAL_QUALITY = {
    'GAR 5000': {'gar': 5000, 'gj_per_t': 20.934},
    'GAR 5250': {'gar': 5250, 'gj_per_t': 21.981},
    'GAR 5500': {'gar': 5500, 'gj_per_t': 23.027},
}

# Seasonal multipliers
SEASONS = {
    'Hot-dry': {
        'solar_mult': 1.02,
        'wind_mult': 0.95,
        'hydro_mult': 0.85,
        'demand_uplift': 1.05,
        'hydro_budget_gwh': 16.0,
        'hydro_peak_limit': 1200.0,
        'character': 'Higher temp load; hydro deration risk',
    },
    'Wet': {
        'solar_mult': 0.80,
        'wind_mult': 1.05,
        'hydro_mult': 1.10,
        'demand_uplift': 1.00,
        'hydro_budget_gwh': 22.0,
        'hydro_peak_limit': 1500.0,
        'character': 'Cloud suppresses solar; hydro improves',
    },
    'Cool-dry': {
        'solar_mult': 0.95,
        'wind_mult': 1.00,
        'hydro_mult': 0.95,
        'demand_uplift': 0.97,
        'hydro_budget_gwh': 18.0,
        'hydro_peak_limit': 1300.0,
        'character': 'Lower cooling demand; benign',
    },
}

# Demand blocks
DEMAND_BLOCKS = {
    'off_peak_base': 8500.0,
    'shoulder_base': 9700.0,
    'peak_base': 11600.0,
    'hours_off': 8.0,
    'hours_shoulder': 10.0,
    'hours_peak': 6.0,
}

# VRE block shapes
VRE_SHAPES = {
    'solar': {'off_peak': 0.0, 'shoulder': 0.35, 'peak': 0.05},
    'wind': {'off_peak': 0.34, 'shoulder': 0.31, 'peak': 0.29},
}

# SPC settings
SPC = {
    'toggle': 0,  # 0 = off, 1 = on
    'cap': 9000.0,  # PHP/MWh
}

# Gen Co fleet
PLANTS = {
    'coal': {
        'capacity': 1200.0,
        'availability': 0.90,
        'heat_rate': 9.6,
        'vom': 260.0,
        'base_dispatch': 700000.0,
    },
    'gas': {
        'capacity': 1200.0,
        'availability': 0.88,
        'heat_rate': 7.2,
        'vom': 180.0,
        'base_dispatch': 250000.0,
    },
    'oil': {
        'capacity': 300.0,
        'availability': 0.95,
        'heat_rate': 11.5,
        'vom': 450.0,
        'base_dispatch': 10000.0,
    },
    'oil_product_diff': 10.0,
}

# Luzon WESM stack
SYSTEM_STACK = [
    {
        'name': 'Solar',
        'dep_mw': 1674.0,
        'tech_avail': 0.98,
        'profile': {'off_peak': 0.0, 'shoulder': 0.35, 'peak': 0.05},
        'srmc_base': [0.0, 0.0, 0.0, 0.0],
    },
    {
        'name': 'Wind',
        'dep_mw': 337.0,
        'tech_avail': 0.95,
        'profile': {'off_peak': 0.34, 'shoulder': 0.31, 'peak': 0.29},
        'srmc_base': [0.0, 0.0, 0.0, 0.0],
    },
    {
        'name': 'Geothermal',
        'dep_mw': 714.0,
        'tech_avail': 0.92,
        'profile': {'off_peak': 1.0, 'shoulder': 1.0, 'peak': 1.0},
        'srmc_base': [600.0, 650.0, 700.0, 800.0],
    },
    {
        'name': 'Biomass',
        'dep_mw': 145.0,
        'tech_avail': 0.85,
        'profile': {'off_peak': 1.0, 'shoulder': 1.0, 'peak': 1.0},
        'srmc_base': [1200.0, 1250.0, 1300.0, 1400.0],
    },
    {
        'name': 'Hydro',
        'dep_mw': 2382.0,
        'tech_avail': 0.93,
        'profile': {'off_peak': 0.6, 'shoulder': 0.45, 'peak': 0.5},
        'srmc_base': [1500.0, 1600.0, 1900.0, 2300.0],
    },
    {
        'name': 'ESS',
        'dep_mw': 341.0,
        'tech_avail': 0.95,
        'profile': {'off_peak': 0.05, 'shoulder': 0.10, 'peak': 0.25},
        'srmc_base': [3000.0, 3200.0, 3500.0, 4200.0],
    },
    {
        'name': 'Coal',
        'dep_mw': 8589.0,
        'tech_avail': 0.92,
        'profile': {'off_peak': 1.0, 'shoulder': 1.0, 'peak': 1.0},
        'srmc_base': None,  # linked to calculation
    },
    {
        'name': 'Gas',
        'dep_mw': 3281.0,
        'tech_avail': 0.88,
        'profile': {'off_peak': 1.0, 'shoulder': 1.0, 'peak': 1.0},
        'srmc_base': None,  # linked to calculation
    },
    {
        'name': 'Oil',
        'dep_mw': 1648.0,
        'tech_avail': 0.95,
        'profile': {'off_peak': 1.0, 'shoulder': 1.0, 'peak': 1.0},
        'srmc_base': None,  # linked to calculation
    },
]

# LNG terminal fees (4 scenarios)
FUEL_INTERMEDIATES = {
    'regas': np.array([0.9, 1.0, 1.1, 1.3]),
    'demurrage': np.array([0.0, 0.0, 0.3, 0.8]),
}

# Supply & Wholesale Contracts
CONTRACTS = {
    'bcq_volume': 300000.0,
    'bcq_price': 5800.0,
    'spot_volume': 120000.0,
    'imbalance_volume': 30000.0,
    'imbalance_ref_price': 5900.0,
    'repricing_beta': 0.30,
    'wholesale_opex': 50.0,
}

# Retail portfolio
RETAIL = [
    {
        'name': 'Fixed C&I',
        'volume': 250000.0,
        'base_tariff': 7.2,
        'wesm_link': 1.00,
        'pass_through': 0.20,
        'bad_debt_base': 0.01,
        'attrition': [0.0, 0.01, 0.03, 0.06],
        'opex': 35.0,
    },
    {
        'name': 'Indexed C&I',
        'volume': 180000.0,
        'base_tariff': 6.8,
        'wesm_link': 0.95,
        'pass_through': 0.80,
        'bad_debt_base': 0.007,
        'attrition': [0.0, 0.005, 0.015, 0.03],
        'opex': 20.0,
    },
    {
        'name': 'Other Retail',
        'volume': 120000.0,
        'base_tariff': 6.2,
        'wesm_link': 0.90,
        'pass_through': 0.30,
        'bad_debt_base': 0.015,
        'attrition': [0.0, 0.005, 0.02, 0.04],
        'opex': 15.0,
    },
]

# Liquidity position
LIQUIDITY = {
    'coal_inv_days': 20,
    'gas_inv_days': 10,
    'oil_inv_days': 7,
    'coal_pay_days': 15,
    'gas_pay_days': 0,
    'oil_pay_days': 5,
    'lc_margin': [0.20, 0.25, 0.30, 0.35],
    'starting_cash': 10000.0,
    'undrawn_facilities': 15000.0,
    'min_cash_buffer': 2000.0,
    'debt_service_monthly': 300.0,
    'net_debt': 40000.0,
    'base_ebitda': 18000.0,
    'covenant_max': 4.5,
}

# AGRA regulatory recovery
AGRA = {
    'immediate_recovery': np.array([1.00, 0.90, 0.75, 0.60]),
    'disallowance': np.array([0.005, 0.01, 0.02, 0.04]),
    'collection_lag': np.array([30, 30, 30, 30]),
    'refund_lag': np.array([1, 1, 1, 1]),
    'true_up_horizon': np.array([36, 36, 36, 36]),
    'carrying_cost': np.array([0.07, 0.07, 0.07, 0.07]),
}

# Trigger playbook
TRIGGERS = [
    {
        'name': 'Brent',
        'operator': '>',
        'current': 93.04,
        'threshold': 110.0,
        'unit': 'USD/bbl',
        'duration_actual': 5,
        'duration_threshold': 3,
        'action': 'Activate hedging review / revise procurement cover',
    },
    {
        'name': 'JKM',
        'operator': '>',
        'current': 15.71,
        'threshold': 20.0,
        'unit': 'USD/MMBtu',
        'duration_actual': 6,
        'duration_threshold': 5,
        'action': 'Review gas dispatch / emergency LNG sourcing',
    },
    {
        'name': 'USD/PHP',
        'operator': '>',
        'current': 59.05,
        'threshold': 58.0,
        'unit': 'PHP/USD',
        'duration_actual': 4,
        'duration_threshold': 3,
        'action': 'Reassess FX hedging / collateral plan',
    },
    {
        'name': 'WESM',
        'operator': '>',
        'current': 9500.0,
        'threshold': 9000.0,
        'unit': 'PHP/MWh',
        'duration_actual': 3,
        'duration_threshold': 2,
        'action': 'Retail repricing review / reserve bidding posture',
    },
    {
        'name': 'Gas availability',
        'operator': '<',
        'current': 0.75,
        'threshold': 0.80,
        'unit': '%',
        'duration_actual': 7,
        'duration_threshold': 5,
        'action': 'Activate alternate dispatch / oil backup plan',
    },
    {
        'name': 'Coal delay',
        'operator': '>',
        'current': 10.0,
        'threshold': 7.0,
        'unit': 'days',
        'duration_actual': 4,
        'duration_threshold': 2,
        'action': 'Increase inventory buffer / alternate logistics',
    },
]

# Reserve market settings
RESERVE = {
    'requirement': 1458.0,  # MW
    'volume': 50000.0,  # MWh/month
}
