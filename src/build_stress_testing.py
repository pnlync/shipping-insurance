from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRICING_PATH = PROCESSED_DIR / "pricing_glm_credibility.csv"
BACKTEST_CATEGORY_PATH = PROCESSED_DIR / "backtest_by_category.csv"
BACKTEST_ROUTE_PATH = PROCESSED_DIR / "backtest_by_route.csv"
BACKTEST_SELLER_TIER_PATH = PROCESSED_DIR / "backtest_by_seller_tier.csv"
BACKTEST_SUMMARY_PATH = PROCESSED_DIR / "loss_ratio_backtesting_summary.json"

SUMMARY_PATH = PROCESSED_DIR / "stress_testing_summary.json"
PORTFOLIO_STRESS_PATH = PROCESSED_DIR / "stress_test_portfolio.csv"
SELLER_TIER_STRESS_PATH = PROCESSED_DIR / "stress_test_by_seller_tier.csv"
WATCHLIST_STRESS_PATH = PROCESSED_DIR / "stress_test_watchlist_segments.csv"

TARGET_LOSS_RATIO = 0.60
CATEGORY_MIN_EXPOSURE = 500
ROUTE_MIN_EXPOSURE = 500
WATCHLIST_TOP_N = 5

PRICING_BASES = {
    "baseline": "baseline_commercial_premium",
    "glm": "glm_commercial_premium",
    "credibility": "credibility_commercial_premium",
}

PORTFOLIO_SCENARIOS = [
    {
        "scenario": "base_observed",
        "frequency_multiplier": 1.00,
        "severity_multiplier": 1.00,
        "description": "Observed synthetic actual loss.",
    },
    {
        "scenario": "frequency_plus_10",
        "frequency_multiplier": 1.10,
        "severity_multiplier": 1.00,
        "description": "Covered claim frequency increases by 10%.",
    },
    {
        "scenario": "frequency_plus_20",
        "frequency_multiplier": 1.20,
        "severity_multiplier": 1.00,
        "description": "Covered claim frequency increases by 20%.",
    },
    {
        "scenario": "severity_plus_10",
        "frequency_multiplier": 1.00,
        "severity_multiplier": 1.10,
        "description": "Claim severity increases by 10%.",
    },
    {
        "scenario": "severity_plus_20",
        "frequency_multiplier": 1.00,
        "severity_multiplier": 1.20,
        "description": "Claim severity increases by 20%.",
    },
    {
        "scenario": "combined_10_10",
        "frequency_multiplier": 1.10,
        "severity_multiplier": 1.10,
        "description": "Frequency and severity both increase by 10%.",
    },
    {
        "scenario": "combined_20_20",
        "frequency_multiplier": 1.20,
        "severity_multiplier": 1.20,
        "description": "Frequency and severity both increase by 20%.",
    },
]


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pricing = pd.read_csv(PRICING_PATH)
    category = pd.read_csv(BACKTEST_CATEGORY_PATH)
    route = pd.read_csv(BACKTEST_ROUTE_PATH)
    seller_tier = pd.read_csv(BACKTEST_SELLER_TIER_PATH)
    return pricing, category, route, seller_tier


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def adequacy_flag(loss_ratio: float) -> str:
    if loss_ratio <= TARGET_LOSS_RATIO:
        return "within_target"
    if loss_ratio <= 0.80:
        return "above_target"
    if loss_ratio <= 1.00:
        return "high_pressure"
    return "premium_inadequate"


def eligible_pricing(pricing: pd.DataFrame) -> pd.DataFrame:
    return pricing[pricing["claim_eligible_flag"] == 1].copy()


def portfolio_premium_totals(frame: pd.DataFrame) -> dict[str, float]:
    return {
        basis: float(frame[premium_column].sum())
        for basis, premium_column in PRICING_BASES.items()
    }


def make_result_row(
    *,
    scenario: str,
    segment_type: str,
    segment_value: str,
    eligible_exposures: int,
    covered_claim_count: int,
    portfolio_base_actual_loss: float,
    portfolio_stressed_actual_loss: float,
    segment_base_actual_loss: float,
    segment_stressed_actual_loss: float,
    premium_totals: dict[str, float],
    frequency_multiplier: float,
    severity_multiplier: float,
    stressed_scope: str,
    description: str,
) -> dict:
    row = {
        "scenario": scenario,
        "segment_type": segment_type,
        "segment_value": segment_value,
        "stressed_scope": stressed_scope,
        "description": description,
        "eligible_exposures": eligible_exposures,
        "covered_claim_count": covered_claim_count,
        "portfolio_base_actual_loss": portfolio_base_actual_loss,
        "segment_base_actual_loss": segment_base_actual_loss,
        "frequency_multiplier": frequency_multiplier,
        "severity_multiplier": severity_multiplier,
        "combined_loss_multiplier": frequency_multiplier * severity_multiplier,
        "segment_stressed_actual_loss": segment_stressed_actual_loss,
        "segment_stressed_loss_increase": (
            segment_stressed_actual_loss - segment_base_actual_loss
        ),
        "segment_stressed_loss_increase_pct": safe_divide(
            segment_stressed_actual_loss,
            segment_base_actual_loss,
        )
        - 1,
        "portfolio_stressed_actual_loss": portfolio_stressed_actual_loss,
        "portfolio_stressed_loss_increase": (
            portfolio_stressed_actual_loss - portfolio_base_actual_loss
        ),
        "portfolio_stressed_loss_increase_pct": safe_divide(
            portfolio_stressed_actual_loss,
            portfolio_base_actual_loss,
        )
        - 1,
    }

    for basis, premium in premium_totals.items():
        loss_ratio = safe_divide(portfolio_stressed_actual_loss, premium)
        row[f"{basis}_commercial_premium"] = premium
        row[f"{basis}_stressed_loss_ratio"] = loss_ratio
        row[f"{basis}_loss_ratio_vs_target"] = loss_ratio - TARGET_LOSS_RATIO
        row[f"{basis}_premium_adequacy_flag"] = adequacy_flag(loss_ratio)

    return row


def build_portfolio_stress(pricing: pd.DataFrame) -> pd.DataFrame:
    eligible = eligible_pricing(pricing)
    base_actual_loss = float(eligible["net_loss"].sum())
    premium_totals = portfolio_premium_totals(eligible)
    rows = []

    for scenario in PORTFOLIO_SCENARIOS:
        multiplier = scenario["frequency_multiplier"] * scenario["severity_multiplier"]
        stressed_actual_loss = base_actual_loss * multiplier
        rows.append(
            make_result_row(
                scenario=scenario["scenario"],
                segment_type="portfolio",
                segment_value="all",
                eligible_exposures=int(len(eligible)),
                covered_claim_count=int(eligible["covered_claim_flag"].sum()),
                portfolio_base_actual_loss=base_actual_loss,
                portfolio_stressed_actual_loss=stressed_actual_loss,
                segment_base_actual_loss=base_actual_loss,
                segment_stressed_actual_loss=stressed_actual_loss,
                premium_totals=premium_totals,
                frequency_multiplier=scenario["frequency_multiplier"],
                severity_multiplier=scenario["severity_multiplier"],
                stressed_scope="all_eligible_exposures",
                description=scenario["description"],
            )
        )

    return pd.DataFrame(rows)


def build_segment_stress(
    pricing: pd.DataFrame,
    *,
    group_column: str,
    segment_type: str,
    frequency_multiplier: float,
    severity_multiplier: float,
) -> pd.DataFrame:
    eligible = eligible_pricing(pricing)
    premium_totals = portfolio_premium_totals(eligible)
    portfolio_base_actual_loss = float(eligible["net_loss"].sum())

    rows = []
    for segment_value, group in eligible.groupby(group_column, dropna=False):
        segment_base_loss = float(group["net_loss"].sum())
        segment_multiplier = frequency_multiplier * severity_multiplier
        segment_stressed_loss = segment_base_loss * segment_multiplier
        portfolio_stressed_loss = (
            portfolio_base_actual_loss - segment_base_loss + segment_stressed_loss
        )
        rows.append(
            make_result_row(
                scenario=f"{segment_type}_combined_stress",
                segment_type=segment_type,
                segment_value=str(segment_value),
                eligible_exposures=int(len(group)),
                covered_claim_count=int(group["covered_claim_flag"].sum()),
                portfolio_base_actual_loss=portfolio_base_actual_loss,
                portfolio_stressed_actual_loss=portfolio_stressed_loss,
                segment_base_actual_loss=segment_base_loss,
                segment_stressed_actual_loss=segment_stressed_loss,
                premium_totals=premium_totals,
                frequency_multiplier=frequency_multiplier,
                severity_multiplier=severity_multiplier,
                stressed_scope=f"only_{segment_type}",
                description=(
                    f"Only {segment_type}={segment_value} receives frequency "
                    f"and severity stress."
                ),
            )
        )

    return pd.DataFrame(rows).sort_values(
        "credibility_stressed_loss_ratio",
        ascending=False,
    )


def select_watchlist_values(
    backtest: pd.DataFrame,
    *,
    group_column: str,
    min_exposure: int,
) -> list[str]:
    watchlist = (
        backtest[backtest["eligible_exposures"] >= min_exposure]
        .sort_values("credibility_loss_ratio", ascending=False)
        .head(WATCHLIST_TOP_N)[group_column]
        .astype(str)
        .tolist()
    )
    return watchlist


def build_watchlist_stress(
    pricing: pd.DataFrame,
    category_backtest: pd.DataFrame,
    route_backtest: pd.DataFrame,
) -> pd.DataFrame:
    eligible = eligible_pricing(pricing)
    premium_totals = portfolio_premium_totals(eligible)
    base_actual_loss = float(eligible["net_loss"].sum())

    watchlists: list[tuple[str, str, Callable[[pd.DataFrame], pd.Series]]] = []

    for category in select_watchlist_values(
        category_backtest,
        group_column="product_category_name_english",
        min_exposure=CATEGORY_MIN_EXPOSURE,
    ):
        watchlists.append(
            (
                "category_watchlist",
                category,
                lambda frame, value=category: frame["product_category_name_english"].astype(str)
                == value,
            )
        )

    for route in select_watchlist_values(
        route_backtest,
        group_column="route_state",
        min_exposure=ROUTE_MIN_EXPOSURE,
    ):
        watchlists.append(
            (
                "route_watchlist",
                route,
                lambda frame, value=route: frame["route_state"].astype(str) == value,
            )
        )

    rows = []
    frequency_multiplier = 1.15
    severity_multiplier = 1.15
    combined_multiplier = frequency_multiplier * severity_multiplier

    for segment_type, segment_value, mask_fn in watchlists:
        mask = mask_fn(eligible)
        segment = eligible[mask]
        segment_base_loss = float(segment["net_loss"].sum())
        segment_stressed_loss = segment_base_loss * combined_multiplier
        portfolio_stressed_loss = base_actual_loss - segment_base_loss + segment_stressed_loss

        rows.append(
            make_result_row(
                scenario=f"{segment_type}_plus_15_15",
                segment_type=segment_type,
                segment_value=segment_value,
                eligible_exposures=int(len(segment)),
                covered_claim_count=int(segment["covered_claim_flag"].sum()),
                portfolio_base_actual_loss=base_actual_loss,
                portfolio_stressed_actual_loss=portfolio_stressed_loss,
                segment_base_actual_loss=segment_base_loss,
                segment_stressed_actual_loss=segment_stressed_loss,
                premium_totals=premium_totals,
                frequency_multiplier=frequency_multiplier,
                severity_multiplier=severity_multiplier,
                stressed_scope=f"only_{segment_type}",
                description=(
                    f"Only watchlist {segment_type}={segment_value} receives "
                    "frequency +15% and severity +15%."
                ),
            )
        )

    return pd.DataFrame(rows).sort_values(
        "credibility_stressed_loss_ratio",
        ascending=False,
    )


def make_summary(
    portfolio_stress: pd.DataFrame,
    seller_tier_stress: pd.DataFrame,
    watchlist_stress: pd.DataFrame,
) -> dict:
    worst_portfolio = portfolio_stress.sort_values(
        "credibility_stressed_loss_ratio",
        ascending=False,
    ).iloc[0]
    worst_segment = pd.concat(
        [seller_tier_stress, watchlist_stress],
        ignore_index=True,
    ).sort_values("credibility_stressed_loss_ratio", ascending=False).iloc[0]

    base = portfolio_stress[portfolio_stress["scenario"] == "base_observed"].iloc[0]
    backtest_summary = json.loads(BACKTEST_SUMMARY_PATH.read_text(encoding="utf-8"))
    backtest_credibility_loss_ratio = float(
        backtest_summary["portfolio"]["credibility_loss_ratio"]
    )

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "category_min_exposure": CATEGORY_MIN_EXPOSURE,
            "route_min_exposure": ROUTE_MIN_EXPOSURE,
            "watchlist_top_n": WATCHLIST_TOP_N,
            "input": str(PRICING_PATH.relative_to(PROJECT_ROOT)),
        },
        "base_observed": base.to_dict(),
        "worst_portfolio_scenario": worst_portfolio.to_dict(),
        "worst_segment_scenario": worst_segment.to_dict(),
        "portfolio_scenarios": portfolio_stress.to_dict(orient="records"),
        "validation": {
            "base_credibility_loss_ratio": float(
                base["credibility_stressed_loss_ratio"]
            ),
            "base_loss_ratio_matches_backtesting": bool(
                np.isclose(
                    base["credibility_stressed_loss_ratio"],
                    backtest_credibility_loss_ratio,
                )
            ),
            "backtesting_credibility_loss_ratio": backtest_credibility_loss_ratio,
            "combined_20_20_multiplier": float(
                portfolio_stress.loc[
                    portfolio_stress["scenario"] == "combined_20_20",
                    "combined_loss_multiplier",
                ].iloc[0]
            ),
        },
        "output": {
            "stress_testing_summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT)),
            "stress_test_portfolio": str(PORTFOLIO_STRESS_PATH.relative_to(PROJECT_ROOT)),
            "stress_test_by_seller_tier": str(
                SELLER_TIER_STRESS_PATH.relative_to(PROJECT_ROOT)
            ),
            "stress_test_watchlist_segments": str(
                WATCHLIST_STRESS_PATH.relative_to(PROJECT_ROOT)
            ),
        },
    }


def main() -> None:
    pricing, category_backtest, route_backtest, _seller_tier_backtest = read_inputs()

    portfolio_stress = build_portfolio_stress(pricing)
    seller_tier_stress = build_segment_stress(
        pricing,
        group_column="seller_risk_tier",
        segment_type="seller_tier",
        frequency_multiplier=1.20,
        severity_multiplier=1.20,
    )
    watchlist_stress = build_watchlist_stress(
        pricing,
        category_backtest,
        route_backtest,
    )

    portfolio_stress.to_csv(PORTFOLIO_STRESS_PATH, index=False)
    seller_tier_stress.to_csv(SELLER_TIER_STRESS_PATH, index=False)
    watchlist_stress.to_csv(WATCHLIST_STRESS_PATH, index=False)

    summary = make_summary(
        portfolio_stress,
        seller_tier_stress,
        watchlist_stress,
    )
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {PORTFOLIO_STRESS_PATH}")
    print(f"Wrote {SELLER_TIER_STRESS_PATH}")
    print(f"Wrote {WATCHLIST_STRESS_PATH}")
    print(json.dumps(summary["worst_portfolio_scenario"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
