from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PRICING_PATH = PROCESSED_DIR / "pricing_glm_credibility.csv"

SUMMARY_PATH = PROCESSED_DIR / "loss_ratio_backtesting_summary.json"
BACKTEST_BY_MONTH_PATH = PROCESSED_DIR / "backtest_by_month.csv"
BACKTEST_BY_CATEGORY_PATH = PROCESSED_DIR / "backtest_by_category.csv"
BACKTEST_BY_ROUTE_PATH = PROCESSED_DIR / "backtest_by_route.csv"
BACKTEST_BY_SELLER_TIER_PATH = PROCESSED_DIR / "backtest_by_seller_tier.csv"
BACKTEST_BY_SELLER_PATH = PROCESSED_DIR / "backtest_by_seller.csv"

TARGET_LOSS_RATIO = 0.60


def read_pricing() -> pd.DataFrame:
    return pd.read_csv(PRICING_PATH)


def safe_divide(numerator: pd.Series | float, denominator: pd.Series | float):
    return np.where(denominator != 0, numerator / denominator, 0.0)


def summarize(
    pricing: pd.DataFrame,
    group_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    eligible = pricing[pricing["claim_eligible_flag"] == 1].copy()

    agg_spec = {
        "eligible_exposures": ("claim_eligible_flag", "size"),
        "covered_claim_count": ("covered_claim_flag", "sum"),
        "actual_loss": ("net_loss", "sum"),
        "baseline_expected_loss": ("baseline_pure_premium", "sum"),
        "glm_expected_loss": ("glm_expected_loss", "sum"),
        "credibility_expected_loss": ("credibility_expected_loss", "sum"),
        "baseline_commercial_premium": ("baseline_commercial_premium", "sum"),
        "glm_commercial_premium": ("glm_commercial_premium", "sum"),
        "credibility_commercial_premium": ("credibility_commercial_premium", "sum"),
        "unique_orders": ("order_id", "nunique"),
        "unique_sellers": ("seller_id", "nunique"),
        "unique_products": ("product_id", "nunique"),
    }

    if group_columns:
        grouped = eligible.groupby(list(group_columns), dropna=False).agg(**agg_spec).reset_index()
    else:
        grouped = pd.DataFrame(
            [
                {
                    "eligible_exposures": int(len(eligible)),
                    "covered_claim_count": int(eligible["covered_claim_flag"].sum()),
                    "actual_loss": float(eligible["net_loss"].sum()),
                    "baseline_expected_loss": float(
                        eligible["baseline_pure_premium"].sum()
                    ),
                    "glm_expected_loss": float(eligible["glm_expected_loss"].sum()),
                    "credibility_expected_loss": float(
                        eligible["credibility_expected_loss"].sum()
                    ),
                    "baseline_commercial_premium": float(
                        eligible["baseline_commercial_premium"].sum()
                    ),
                    "glm_commercial_premium": float(
                        eligible["glm_commercial_premium"].sum()
                    ),
                    "credibility_commercial_premium": float(
                        eligible["credibility_commercial_premium"].sum()
                    ),
                    "unique_orders": int(eligible["order_id"].nunique()),
                    "unique_sellers": int(eligible["seller_id"].nunique()),
                    "unique_products": int(eligible["product_id"].nunique()),
                }
            ]
        )

    grouped["claim_frequency"] = safe_divide(
        grouped["covered_claim_count"],
        grouped["eligible_exposures"],
    )
    grouped["average_severity"] = safe_divide(
        grouped["actual_loss"],
        grouped["covered_claim_count"],
    )
    grouped["actual_pure_premium"] = safe_divide(
        grouped["actual_loss"],
        grouped["eligible_exposures"],
    )

    for basis in ["baseline", "glm", "credibility"]:
        expected_col = f"{basis}_expected_loss"
        premium_col = f"{basis}_commercial_premium"
        grouped[f"{basis}_expected_pure_premium"] = safe_divide(
            grouped[expected_col],
            grouped["eligible_exposures"],
        )
        grouped[f"{basis}_ae"] = safe_divide(
            grouped["actual_loss"],
            grouped[expected_col],
        )
        grouped[f"{basis}_loss_ratio"] = safe_divide(
            grouped["actual_loss"],
            grouped[premium_col],
        )
        grouped[f"{basis}_loss_ratio_vs_target"] = (
            grouped[f"{basis}_loss_ratio"] - TARGET_LOSS_RATIO
        )

    grouped["glm_ae_improvement_vs_baseline"] = (
        grouped["baseline_ae"].sub(1).abs() - grouped["glm_ae"].sub(1).abs()
    )
    grouped["credibility_ae_improvement_vs_glm"] = (
        grouped["glm_ae"].sub(1).abs() - grouped["credibility_ae"].sub(1).abs()
    )
    grouped["credibility_expected_loss_change_vs_glm"] = safe_divide(
        grouped["credibility_expected_loss"],
        grouped["glm_expected_loss"],
    ) - 1

    return grouped


def sort_backtest(frame: pd.DataFrame, group_column: str) -> pd.DataFrame:
    return frame.sort_values(
        ["eligible_exposures", group_column],
        ascending=[False, True],
    )


def top_segments(
    frame: pd.DataFrame,
    group_column: str,
    metric: str,
    *,
    min_exposures: int,
    n: int = 10,
    ascending: bool = False,
) -> list[dict]:
    filtered = frame[frame["eligible_exposures"] >= min_exposures].copy()
    columns = [
        group_column,
        "eligible_exposures",
        "covered_claim_count",
        "actual_loss",
        "credibility_expected_loss",
        "credibility_ae",
        "credibility_loss_ratio",
        metric,
    ]
    columns = list(dict.fromkeys(columns))
    return (
        filtered.sort_values(metric, ascending=ascending)
        .head(n)[columns]
        .to_dict(orient="records")
    )


def make_summary(
    portfolio: pd.DataFrame,
    by_month: pd.DataFrame,
    by_category: pd.DataFrame,
    by_route: pd.DataFrame,
    by_seller_tier: pd.DataFrame,
    by_seller: pd.DataFrame,
) -> dict:
    portfolio_record = portfolio.iloc[0].to_dict()

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "input": str(PRICING_PATH.relative_to(PROJECT_ROOT)),
            "pricing_bases": ["baseline", "glm", "credibility"],
            "note": "Current version is a synthetic-data monitoring framework, not a true out-of-time production backtest.",
        },
        "portfolio": portfolio_record,
        "monitoring_dimensions": {
            "month_count": int(len(by_month)),
            "category_count": int(len(by_category)),
            "route_count": int(len(by_route)),
            "seller_tier_count": int(len(by_seller_tier)),
            "seller_count": int(len(by_seller)),
        },
        "top_category_high_loss_ratio": top_segments(
            by_category,
            "product_category_name_english",
            "credibility_loss_ratio",
            min_exposures=500,
        ),
        "top_route_high_loss_ratio": top_segments(
            by_route,
            "route_state",
            "credibility_loss_ratio",
            min_exposures=500,
        ),
        "top_seller_high_loss_ratio": top_segments(
            by_seller,
            "seller_id",
            "credibility_loss_ratio",
            min_exposures=100,
        ),
        "seller_tier_summary": by_seller_tier.to_dict(orient="records"),
        "validation": {
            "portfolio_actual_loss": float(portfolio_record["actual_loss"]),
            "portfolio_baseline_expected_loss": float(
                portfolio_record["baseline_expected_loss"]
            ),
            "portfolio_glm_expected_loss": float(portfolio_record["glm_expected_loss"]),
            "portfolio_credibility_expected_loss": float(
                portfolio_record["credibility_expected_loss"]
            ),
            "credibility_expected_loss_matches_glm": bool(
                np.isclose(
                    portfolio_record["credibility_expected_loss"],
                    portfolio_record["glm_expected_loss"],
                )
            ),
            "credibility_loss_ratio_equals_target_times_ae": bool(
                np.isclose(
                    portfolio_record["credibility_loss_ratio"],
                    portfolio_record["credibility_ae"] * TARGET_LOSS_RATIO,
                )
            ),
        },
        "output": {
            "loss_ratio_backtesting_summary": str(
                SUMMARY_PATH.relative_to(PROJECT_ROOT)
            ),
            "backtest_by_month": str(BACKTEST_BY_MONTH_PATH.relative_to(PROJECT_ROOT)),
            "backtest_by_category": str(
                BACKTEST_BY_CATEGORY_PATH.relative_to(PROJECT_ROOT)
            ),
            "backtest_by_route": str(BACKTEST_BY_ROUTE_PATH.relative_to(PROJECT_ROOT)),
            "backtest_by_seller_tier": str(
                BACKTEST_BY_SELLER_TIER_PATH.relative_to(PROJECT_ROOT)
            ),
            "backtest_by_seller": str(BACKTEST_BY_SELLER_PATH.relative_to(PROJECT_ROOT)),
        },
    }


def main() -> None:
    pricing = read_pricing()

    portfolio = summarize(pricing)
    by_month = summarize(pricing, ["purchase_month"]).sort_values("purchase_month")
    by_category = sort_backtest(
        summarize(pricing, ["product_category_name_english"]),
        "product_category_name_english",
    )
    by_route = sort_backtest(summarize(pricing, ["route_state"]), "route_state")
    by_seller_tier = sort_backtest(
        summarize(pricing, ["seller_risk_tier"]),
        "seller_risk_tier",
    )
    by_seller = sort_backtest(summarize(pricing, ["seller_id"]), "seller_id")

    by_month.to_csv(BACKTEST_BY_MONTH_PATH, index=False)
    by_category.to_csv(BACKTEST_BY_CATEGORY_PATH, index=False)
    by_route.to_csv(BACKTEST_BY_ROUTE_PATH, index=False)
    by_seller_tier.to_csv(BACKTEST_BY_SELLER_TIER_PATH, index=False)
    by_seller.to_csv(BACKTEST_BY_SELLER_PATH, index=False)

    summary = make_summary(
        portfolio,
        by_month,
        by_category,
        by_route,
        by_seller_tier,
        by_seller,
    )
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {BACKTEST_BY_MONTH_PATH}")
    print(f"Wrote {BACKTEST_BY_CATEGORY_PATH}")
    print(f"Wrote {BACKTEST_BY_ROUTE_PATH}")
    print(f"Wrote {BACKTEST_BY_SELLER_TIER_PATH}")
    print(f"Wrote {BACKTEST_BY_SELLER_PATH}")
    print(json.dumps(summary["portfolio"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
