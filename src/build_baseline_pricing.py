from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLAIMS_PATH = PROCESSED_DIR / "exposure_claims_synthetic.csv"
BASELINE_PATH = PROCESSED_DIR / "pricing_baseline.csv"
SUMMARY_PATH = PROCESSED_DIR / "pricing_baseline_summary.json"

TARGET_LOSS_RATIO = 0.60
CATEGORY_MIN_EXPOSURE = 500
ROUTE_MIN_EXPOSURE = 500
SELLER_MIN_EXPOSURE = 100


def read_claims() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def portfolio_metrics(claims: pd.DataFrame) -> dict:
    eligible = claims["claim_eligible_flag"] == 1
    eligible_exposures = int(eligible.sum())
    covered_claim_count = int(claims.loc[eligible, "covered_claim_flag"].sum())
    total_net_loss = float(claims.loc[eligible, "net_loss"].sum())
    total_paid_loss = float(claims.loc[eligible, "paid_loss"].sum())
    total_gross_loss = float(claims.loc[eligible, "gross_loss"].sum())
    total_recovery = float(claims.loc[eligible, "recovery_from_carrier"].sum())

    pure_premium = safe_divide(total_net_loss, eligible_exposures)
    commercial_premium = pure_premium / TARGET_LOSS_RATIO
    total_commercial_premium = commercial_premium * eligible_exposures

    return {
        "target_loss_ratio": TARGET_LOSS_RATIO,
        "rows": int(len(claims)),
        "eligible_exposures": eligible_exposures,
        "ineligible_exposures": int((~eligible).sum()),
        "covered_claim_count": covered_claim_count,
        "claim_frequency": safe_divide(covered_claim_count, eligible_exposures),
        "total_gross_loss": total_gross_loss,
        "total_recovery_from_carrier": total_recovery,
        "total_paid_loss": total_paid_loss,
        "total_net_loss": total_net_loss,
        "average_severity": safe_divide(total_net_loss, covered_claim_count),
        "portfolio_pure_premium": pure_premium,
        "portfolio_commercial_premium": commercial_premium,
        "total_commercial_premium": total_commercial_premium,
        "expected_loss_ratio": safe_divide(total_net_loss, total_commercial_premium),
    }


def grouped_pricing_summary(
    claims: pd.DataFrame,
    group_column: str,
    *,
    portfolio_pure_premium: float,
    min_exposure: int,
) -> pd.DataFrame:
    eligible = claims[claims["claim_eligible_flag"] == 1].copy()

    summary = (
        eligible.groupby(group_column, dropna=False)
        .agg(
            eligible_exposures=("claim_eligible_flag", "size"),
            covered_claim_count=("covered_claim_flag", "sum"),
            total_gross_loss=("gross_loss", "sum"),
            total_recovery_from_carrier=("recovery_from_carrier", "sum"),
            total_paid_loss=("paid_loss", "sum"),
            total_net_loss=("net_loss", "sum"),
            average_freight_value=("freight_value", "mean"),
            average_freight_value_capped=("freight_value_capped", "mean"),
            unique_orders=("order_id", "nunique"),
            unique_sellers=("seller_id", "nunique"),
            unique_products=("product_id", "nunique"),
        )
        .reset_index()
    )

    summary["claim_frequency"] = (
        summary["covered_claim_count"] / summary["eligible_exposures"]
    )
    summary["average_severity"] = np.where(
        summary["covered_claim_count"] > 0,
        summary["total_net_loss"] / summary["covered_claim_count"],
        0.0,
    )
    summary["pure_premium"] = summary["total_net_loss"] / summary["eligible_exposures"]
    summary["relativity"] = np.where(
        portfolio_pure_premium > 0,
        summary["pure_premium"] / portfolio_pure_premium,
        0.0,
    )
    summary["commercial_premium"] = summary["pure_premium"] / TARGET_LOSS_RATIO
    summary["credibility_flag"] = np.where(
        summary["eligible_exposures"] >= min_exposure,
        "credible_for_baseline",
        "insufficient",
    )

    return summary.sort_values(
        ["eligible_exposures", group_column],
        ascending=[False, True],
    )


def build_exposure_pricing_table(claims: pd.DataFrame, metrics: dict) -> pd.DataFrame:
    priced = claims.copy()
    eligible = priced["claim_eligible_flag"] == 1

    priced["target_loss_ratio"] = TARGET_LOSS_RATIO
    priced["portfolio_pure_premium"] = metrics["portfolio_pure_premium"]
    priced["portfolio_commercial_premium"] = metrics["portfolio_commercial_premium"]
    priced["baseline_pure_premium"] = np.where(
        eligible,
        metrics["portfolio_pure_premium"],
        0.0,
    )
    priced["baseline_commercial_premium"] = np.where(
        eligible,
        metrics["portfolio_commercial_premium"],
        0.0,
    )
    priced["expected_loss"] = priced["baseline_pure_premium"]
    priced["expected_loss_ratio_to_freight"] = np.where(
        priced["freight_value_capped"] > 0,
        priced["expected_loss"] / priced["freight_value_capped"],
        0.0,
    )
    priced["expected_portfolio_loss_ratio"] = np.where(
        priced["baseline_commercial_premium"] > 0,
        priced["expected_loss"] / priced["baseline_commercial_premium"],
        0.0,
    )

    return priced


def make_summary(
    metrics: dict,
    category_summary: pd.DataFrame,
    route_summary: pd.DataFrame,
    cross_state_summary: pd.DataFrame,
    seller_summary: pd.DataFrame,
) -> dict:
    def top_records(frame: pd.DataFrame, group_column: str, n: int = 10) -> list[dict]:
        credible = frame[frame["credibility_flag"] == "credible_for_baseline"]
        return (
            credible.sort_values("pure_premium", ascending=False)
            .head(n)[
                [
                    group_column,
                    "eligible_exposures",
                    "covered_claim_count",
                    "claim_frequency",
                    "average_severity",
                    "pure_premium",
                    "relativity",
                    "commercial_premium",
                ]
            ]
            .to_dict(orient="records")
        )

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "category_min_exposure": CATEGORY_MIN_EXPOSURE,
            "route_min_exposure": ROUTE_MIN_EXPOSURE,
            "seller_min_exposure": SELLER_MIN_EXPOSURE,
        },
        "portfolio": metrics,
        "credible_group_counts": {
            "category": int(
                (category_summary["credibility_flag"] == "credible_for_baseline").sum()
            ),
            "route": int((route_summary["credibility_flag"] == "credible_for_baseline").sum()),
            "seller": int(
                (seller_summary["credibility_flag"] == "credible_for_baseline").sum()
            ),
        },
        "top_categories_by_pure_premium": top_records(
            category_summary,
            "product_category_name_english",
        ),
        "top_routes_by_pure_premium": top_records(route_summary, "route_state"),
        "cross_state_pricing": cross_state_summary.to_dict(orient="records"),
    }


def validate_outputs(priced: pd.DataFrame, metrics: dict) -> dict:
    eligible = priced["claim_eligible_flag"] == 1
    total_commercial_premium = float(priced["baseline_commercial_premium"].sum())
    total_expected_loss = float(priced["expected_loss"].sum())

    checks = {
        "rows_match_claims": int(len(priced)),
        "ineligible_baseline_pure_premium_nonzero": int(
            ((~eligible) & (priced["baseline_pure_premium"] != 0)).sum()
        ),
        "ineligible_baseline_commercial_premium_nonzero": int(
            ((~eligible) & (priced["baseline_commercial_premium"] != 0)).sum()
        ),
        "total_expected_loss": total_expected_loss,
        "total_commercial_premium": total_commercial_premium,
        "expected_loss_ratio": safe_divide(total_expected_loss, total_commercial_premium),
        "portfolio_pure_premium_matches": bool(
            np.isclose(metrics["portfolio_pure_premium"], priced.loc[eligible, "expected_loss"].mean())
        ),
    }
    return checks


def main() -> None:
    claims = read_claims()
    metrics = portfolio_metrics(claims)
    priced = build_exposure_pricing_table(claims, metrics)

    category_summary = grouped_pricing_summary(
        claims,
        "product_category_name_english",
        portfolio_pure_premium=metrics["portfolio_pure_premium"],
        min_exposure=CATEGORY_MIN_EXPOSURE,
    )
    route_summary = grouped_pricing_summary(
        claims,
        "route_state",
        portfolio_pure_premium=metrics["portfolio_pure_premium"],
        min_exposure=ROUTE_MIN_EXPOSURE,
    )
    cross_state_summary = grouped_pricing_summary(
        claims,
        "cross_state_flag",
        portfolio_pure_premium=metrics["portfolio_pure_premium"],
        min_exposure=1,
    )
    seller_summary = grouped_pricing_summary(
        claims,
        "seller_id",
        portfolio_pure_premium=metrics["portfolio_pure_premium"],
        min_exposure=SELLER_MIN_EXPOSURE,
    )

    priced.to_csv(BASELINE_PATH, index=False)
    category_summary.to_csv(PROCESSED_DIR / "pricing_by_category.csv", index=False)
    route_summary.to_csv(PROCESSED_DIR / "pricing_by_route.csv", index=False)
    cross_state_summary.to_csv(PROCESSED_DIR / "pricing_by_cross_state.csv", index=False)
    seller_summary.to_csv(PROCESSED_DIR / "pricing_by_seller.csv", index=False)

    summary = make_summary(
        metrics,
        category_summary,
        route_summary,
        cross_state_summary,
        seller_summary,
    )
    summary["validation"] = validate_outputs(priced, metrics)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {BASELINE_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(json.dumps(summary["portfolio"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
