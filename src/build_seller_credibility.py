from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GLM_PRICING_PATH = PROCESSED_DIR / "pricing_glm.csv"

CREDIBILITY_PRICING_PATH = PROCESSED_DIR / "pricing_glm_credibility.csv"
SELLER_SUMMARY_PATH = PROCESSED_DIR / "seller_credibility_summary.csv"
SUMMARY_JSON_PATH = PROCESSED_DIR / "seller_credibility_summary.json"

TARGET_LOSS_RATIO = 0.60
CREDIBILITY_K = 500
RELATIVITY_MIN = 0.50
RELATIVITY_MAX = 2.00


def read_glm_pricing() -> pd.DataFrame:
    return pd.read_csv(GLM_PRICING_PATH)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def build_seller_summary(pricing: pd.DataFrame) -> pd.DataFrame:
    eligible = pricing[pricing["claim_eligible_flag"] == 1].copy()

    seller_summary = (
        eligible.groupby("seller_id", dropna=False)
        .agg(
            seller_eligible_exposures=("claim_eligible_flag", "size"),
            seller_claim_count=("covered_claim_flag", "sum"),
            seller_actual_net_loss=("net_loss", "sum"),
            seller_glm_expected_loss=("glm_expected_loss", "sum"),
            seller_glm_commercial_premium=("glm_commercial_premium", "sum"),
            seller_average_glm_expected_loss=("glm_expected_loss", "mean"),
            seller_average_glm_commercial_premium=("glm_commercial_premium", "mean"),
            unique_orders=("order_id", "nunique"),
            unique_products=("product_id", "nunique"),
        )
        .reset_index()
    )

    seller_summary["seller_observed_frequency"] = (
        seller_summary["seller_claim_count"] / seller_summary["seller_eligible_exposures"]
    )
    seller_summary["seller_observed_pure_premium"] = (
        seller_summary["seller_actual_net_loss"] / seller_summary["seller_eligible_exposures"]
    )
    seller_summary["seller_glm_pure_premium"] = (
        seller_summary["seller_glm_expected_loss"] / seller_summary["seller_eligible_exposures"]
    )
    seller_summary["seller_observed_ae"] = np.where(
        seller_summary["seller_glm_expected_loss"] > 0,
        seller_summary["seller_actual_net_loss"] / seller_summary["seller_glm_expected_loss"],
        1.0,
    )
    seller_summary["seller_credibility_weight"] = (
        seller_summary["seller_eligible_exposures"]
        / (seller_summary["seller_eligible_exposures"] + CREDIBILITY_K)
    )
    seller_summary["seller_credibility_relativity_raw"] = (
        seller_summary["seller_credibility_weight"] * seller_summary["seller_observed_ae"]
        + (1 - seller_summary["seller_credibility_weight"]) * 1.0
    )
    seller_summary["seller_credibility_relativity_capped"] = seller_summary[
        "seller_credibility_relativity_raw"
    ].clip(lower=RELATIVITY_MIN, upper=RELATIVITY_MAX)

    total_glm_expected_loss = float(seller_summary["seller_glm_expected_loss"].sum())
    total_pre_normalized_expected_loss = float(
        (
            seller_summary["seller_glm_expected_loss"]
            * seller_summary["seller_credibility_relativity_capped"]
        ).sum()
    )
    normalization_factor = safe_divide(
        total_glm_expected_loss,
        total_pre_normalized_expected_loss,
    )

    seller_summary["seller_credibility_normalization_factor"] = normalization_factor
    seller_summary["seller_credibility_relativity"] = (
        seller_summary["seller_credibility_relativity_capped"] * normalization_factor
    )
    seller_summary["seller_credibility_expected_loss"] = (
        seller_summary["seller_glm_expected_loss"]
        * seller_summary["seller_credibility_relativity"]
    )
    seller_summary["seller_credibility_commercial_premium"] = (
        seller_summary["seller_credibility_expected_loss"] / TARGET_LOSS_RATIO
    )
    seller_summary["seller_credibility_ae"] = np.where(
        seller_summary["seller_credibility_expected_loss"] > 0,
        seller_summary["seller_actual_net_loss"]
        / seller_summary["seller_credibility_expected_loss"],
        0.0,
    )
    seller_summary["seller_risk_tier"] = np.select(
        [
            seller_summary["seller_credibility_relativity"] < 0.90,
            seller_summary["seller_credibility_relativity"] < 1.10,
            seller_summary["seller_credibility_relativity"] < 1.30,
        ],
        [
            "lower_than_glm",
            "near_glm",
            "elevated",
        ],
        default="high",
    )

    return seller_summary.sort_values(
        ["seller_eligible_exposures", "seller_id"],
        ascending=[False, True],
    )


def build_exposure_pricing(pricing: pd.DataFrame, seller_summary: pd.DataFrame) -> pd.DataFrame:
    seller_columns = [
        "seller_id",
        "seller_eligible_exposures",
        "seller_claim_count",
        "seller_actual_net_loss",
        "seller_glm_expected_loss",
        "seller_observed_ae",
        "seller_credibility_weight",
        "seller_credibility_relativity_raw",
        "seller_credibility_relativity_capped",
        "seller_credibility_normalization_factor",
        "seller_credibility_relativity",
        "seller_risk_tier",
    ]
    priced = pricing.merge(
        seller_summary[seller_columns],
        on="seller_id",
        how="left",
        validate="many_to_one",
    )

    eligible = priced["claim_eligible_flag"] == 1
    fill_zero_columns = [
        "seller_eligible_exposures",
        "seller_claim_count",
        "seller_actual_net_loss",
        "seller_glm_expected_loss",
        "seller_observed_ae",
        "seller_credibility_weight",
        "seller_credibility_relativity_raw",
        "seller_credibility_relativity_capped",
        "seller_credibility_normalization_factor",
        "seller_credibility_relativity",
    ]
    priced[fill_zero_columns] = priced[fill_zero_columns].fillna(0.0)
    priced["seller_risk_tier"] = priced["seller_risk_tier"].fillna("not_eligible")

    priced["credibility_expected_loss"] = np.where(
        eligible,
        priced["glm_expected_loss"] * priced["seller_credibility_relativity"],
        0.0,
    )
    priced["credibility_commercial_premium"] = (
        priced["credibility_expected_loss"] / TARGET_LOSS_RATIO
    )
    priced["credibility_expected_loss_ratio_to_glm"] = np.where(
        priced["glm_expected_loss"] > 0,
        priced["credibility_expected_loss"] / priced["glm_expected_loss"],
        0.0,
    )
    priced["credibility_premium_ratio_to_glm"] = np.where(
        priced["glm_commercial_premium"] > 0,
        priced["credibility_commercial_premium"] / priced["glm_commercial_premium"],
        0.0,
    )
    priced["credibility_expected_loss_ratio_to_freight"] = np.where(
        priced["freight_value_capped"] > 0,
        priced["credibility_expected_loss"] / priced["freight_value_capped"],
        0.0,
    )

    return priced


def make_summary(priced: pd.DataFrame, seller_summary: pd.DataFrame) -> dict:
    eligible = priced["claim_eligible_flag"] == 1
    eligible_priced = priced[eligible]

    total_actual_loss = float(eligible_priced["net_loss"].sum())
    total_glm_expected_loss = float(eligible_priced["glm_expected_loss"].sum())
    total_credibility_expected_loss = float(
        eligible_priced["credibility_expected_loss"].sum()
    )
    total_credibility_premium = float(
        eligible_priced["credibility_commercial_premium"].sum()
    )

    tier_summary = (
        seller_summary.groupby("seller_risk_tier")
        .agg(
            sellers=("seller_id", "size"),
            eligible_exposures=("seller_eligible_exposures", "sum"),
            actual_net_loss=("seller_actual_net_loss", "sum"),
            glm_expected_loss=("seller_glm_expected_loss", "sum"),
            credibility_expected_loss=("seller_credibility_expected_loss", "sum"),
        )
        .reset_index()
    )
    tier_summary["glm_ae"] = np.where(
        tier_summary["glm_expected_loss"] > 0,
        tier_summary["actual_net_loss"] / tier_summary["glm_expected_loss"],
        0.0,
    )
    tier_summary["credibility_ae"] = np.where(
        tier_summary["credibility_expected_loss"] > 0,
        tier_summary["actual_net_loss"] / tier_summary["credibility_expected_loss"],
        0.0,
    )

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "credibility_k": CREDIBILITY_K,
            "relativity_min": RELATIVITY_MIN,
            "relativity_max": RELATIVITY_MAX,
            "formula": "Z = n / (n + k); relativity = Z * seller_observed_ae + (1 - Z)",
            "portfolio_normalization": "preserve total GLM expected loss",
        },
        "input": {
            "rows": int(len(priced)),
            "eligible_exposures": int(eligible.sum()),
            "sellers_with_eligible_exposure": int(len(seller_summary)),
            "unique_exposure_keys": int(
                priced[["order_id", "order_item_id", "seller_id", "product_id"]]
                .drop_duplicates()
                .shape[0]
            ),
        },
        "portfolio": {
            "actual_total_net_loss": total_actual_loss,
            "glm_expected_total_loss": total_glm_expected_loss,
            "credibility_expected_total_loss": total_credibility_expected_loss,
            "glm_actual_to_expected": safe_divide(
                total_actual_loss,
                total_glm_expected_loss,
            ),
            "credibility_actual_to_expected": safe_divide(
                total_actual_loss,
                total_credibility_expected_loss,
            ),
            "credibility_total_commercial_premium": total_credibility_premium,
            "credibility_expected_loss_ratio": safe_divide(
                total_credibility_expected_loss,
                total_credibility_premium,
            ),
            "portfolio_expected_loss_change_vs_glm": safe_divide(
                total_credibility_expected_loss,
                total_glm_expected_loss,
            )
            - 1,
        },
        "seller_distribution": {
            "eligible_exposures_per_seller": seller_summary[
                "seller_eligible_exposures"
            ].describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).to_dict(),
            "credibility_weight": seller_summary["seller_credibility_weight"]
            .describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
            .to_dict(),
            "final_relativity": seller_summary["seller_credibility_relativity"]
            .describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
            .to_dict(),
        },
        "tier_summary": tier_summary.to_dict(orient="records"),
        "validation": {
            "pricing_rows": int(len(priced)),
            "unique_exposure_keys": int(
                priced[["order_id", "order_item_id", "seller_id", "product_id"]]
                .drop_duplicates()
                .shape[0]
            ),
            "ineligible_credibility_expected_loss_nonzero": int(
                ((~eligible) & (priced["credibility_expected_loss"] != 0)).sum()
            ),
            "ineligible_credibility_premium_nonzero": int(
                ((~eligible) & (priced["credibility_commercial_premium"] != 0)).sum()
            ),
            "portfolio_expected_loss_preserved": bool(
                np.isclose(total_credibility_expected_loss, total_glm_expected_loss)
            ),
        },
        "output": {
            "pricing_glm_credibility": str(
                CREDIBILITY_PRICING_PATH.relative_to(PROJECT_ROOT)
            ),
            "seller_credibility_summary": str(
                SELLER_SUMMARY_PATH.relative_to(PROJECT_ROOT)
            ),
            "seller_credibility_summary_json": str(
                SUMMARY_JSON_PATH.relative_to(PROJECT_ROOT)
            ),
        },
    }


def main() -> None:
    pricing = read_glm_pricing()
    seller_summary = build_seller_summary(pricing)
    priced = build_exposure_pricing(pricing, seller_summary)

    priced.to_csv(CREDIBILITY_PRICING_PATH, index=False)
    seller_summary.to_csv(SELLER_SUMMARY_PATH, index=False)

    summary = make_summary(priced, seller_summary)
    SUMMARY_JSON_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote {CREDIBILITY_PRICING_PATH}")
    print(f"Wrote {SELLER_SUMMARY_PATH}")
    print(f"Wrote {SUMMARY_JSON_PATH}")
    print(json.dumps(summary["portfolio"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
