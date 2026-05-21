from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPOSURE_PATH = PROCESSED_DIR / "exposure_table.csv"
OUTPUT_PATH = PROCESSED_DIR / "exposure_claims_synthetic.csv"
SUMMARY_PATH = PROCESSED_DIR / "synthetic_claims_summary.json"

RANDOM_SEED = 20260521
BASE_RETURN_RATE = 0.08
MIN_RETURN_PROBABILITY = 0.01
MAX_RETURN_PROBABILITY = 0.25
FREIGHT_VALUE_CAP = 84.52
FREIGHT_TO_PRICE_RATIO_CAP = 1.5494505494505493

HIGH_FREIGHT_ROUTES = {
    "SP_to_MA",
    "SP_to_PA",
    "RS_to_SP",
    "SP_to_CE",
    "SP_to_PE",
    "SP_to_MT",
    "MG_to_RJ",
    "SC_to_RJ",
    "SP_to_BA",
    "SP_to_MS",
}

CATEGORY_FACTORS = {
    "electronics": 1.25,
    "telephony": 1.20,
    "fashion_bags_accessories": 1.15,
    "health_beauty": 1.15,
    "perfumery": 1.10,
    "baby": 1.05,
    "bed_bath_table": 1.05,
    "sports_leisure": 1.00,
    "computers_accessories": 0.95,
    "auto": 0.90,
    "furniture_decor": 0.90,
    "garden_tools": 0.85,
    "housewares": 0.85,
    "watches_gifts": 0.85,
    "office_furniture": 0.70,
    "furniture_living_room": 0.75,
}


def read_exposure_table() -> pd.DataFrame:
    return pd.read_csv(EXPOSURE_PATH)


def fill_by_category_median(
    exposure: pd.DataFrame,
    column: str,
    *,
    zero_is_invalid: bool,
) -> tuple[pd.Series, pd.Series]:
    values = exposure[column].copy()
    invalid = values.isna()
    if zero_is_invalid:
        invalid = invalid | (values <= 0)

    category = exposure["product_category_name_english"]
    valid_values = values.mask(invalid)
    category_median = valid_values.groupby(category).transform("median")
    global_median = valid_values.median()

    filled = values.mask(invalid, category_median)
    filled = filled.fillna(global_median)
    return filled, invalid.astype(int)


def build_frequency_factors(exposure: pd.DataFrame) -> pd.DataFrame:
    factors = pd.DataFrame(index=exposure.index)

    category_factor = exposure["product_category_name_english"].map(CATEGORY_FACTORS).fillna(1.0)
    factors["return_factor_category"] = category_factor

    route_factor = np.where(exposure["cross_state_flag"] == 1, 1.10, 0.90)
    route_factor = np.where(exposure["route_state"].isin(HIGH_FREIGHT_ROUTES), 1.20, route_factor)
    factors["return_factor_route"] = route_factor

    ratio = exposure["freight_to_price_ratio_capped"]
    factors["return_factor_freight_ratio"] = np.select(
        [ratio < 0.15, ratio < 0.40, ratio < 0.90, ratio >= 0.90],
        [0.90, 1.00, 1.10, 1.25],
        default=1.00,
    )

    weight_p95 = exposure["product_weight_g_filled"].quantile(0.95)
    volume_p95 = exposure["product_volume_cm3_filled"].quantile(0.95)
    bulky = (exposure["product_weight_g_filled"] > weight_p95) | (
        exposure["product_volume_cm3_filled"] > volume_p95
    )
    factors["return_factor_size"] = np.where(bulky, 0.85, 1.00)

    factors["return_factor_month"] = np.where(
        exposure["purchase_month"].isin([11, 12]),
        1.10,
        np.where(exposure["purchase_month"].isin([1, 2]), 1.05, 1.00),
    )

    return factors


def build_synthetic_claims(exposure: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    claims = exposure.copy()

    claims["claim_eligible_flag"] = (claims["order_status"] == "delivered").astype(int)
    claims["freight_value_capped"] = claims["freight_value"].clip(upper=FREIGHT_VALUE_CAP)
    claims["freight_to_price_ratio_capped"] = claims["freight_to_price_ratio"].clip(
        upper=FREIGHT_TO_PRICE_RATIO_CAP
    )

    claims["product_weight_g_filled"], claims["product_weight_g_imputed_flag"] = (
        fill_by_category_median(claims, "product_weight_g", zero_is_invalid=True)
    )
    claims["product_volume_cm3_filled"], claims["product_volume_cm3_imputed_flag"] = (
        fill_by_category_median(claims, "product_volume_cm3", zero_is_invalid=True)
    )

    factors = build_frequency_factors(claims)
    claims = pd.concat([claims, factors], axis=1)

    raw_probability = (
        BASE_RETURN_RATE
        * claims["return_factor_category"]
        * claims["return_factor_route"]
        * claims["return_factor_freight_ratio"]
        * claims["return_factor_size"]
        * claims["return_factor_month"]
    )
    claims["return_probability"] = np.where(
        claims["claim_eligible_flag"] == 1,
        raw_probability.clip(MIN_RETURN_PROBABILITY, MAX_RETURN_PROBABILITY),
        0.0,
    )

    claims["return_requested"] = (
        rng.random(len(claims)) < claims["return_probability"]
    ).astype(int)

    approval_probability = np.where(claims["freight_to_price_ratio_capped"] > 1.0, 0.88, 0.93)
    claims["return_approved"] = (
        (claims["return_requested"] == 1) & (rng.random(len(claims)) < approval_probability)
    ).astype(int)

    refund_without_return_probability = np.where(claims["price"] < 20, 0.05, 0.02)
    claims["refund_without_return"] = (
        (claims["return_approved"] == 1)
        & (rng.random(len(claims)) < refund_without_return_probability)
    ).astype(int)

    partial_refund_probability = np.where(claims["price"] < 30, 0.08, 0.04)
    claims["partial_refund"] = (
        (claims["return_approved"] == 1)
        & (claims["refund_without_return"] == 0)
        & (rng.random(len(claims)) < partial_refund_probability)
    ).astype(int)

    request_days = rng.integers(1, 31, size=len(claims))
    claims["request_days_after_delivery"] = np.where(
        claims["return_requested"] == 1,
        request_days,
        0,
    )

    reason_options = np.array(
        ["none", "buyer_remorse", "wrong_size_or_fit", "damaged_or_defective", "late_delivery"]
    )
    reason_probabilities = np.array([0.0, 0.45, 0.25, 0.20, 0.10])
    sampled_reasons = rng.choice(reason_options[1:], size=len(claims), p=reason_probabilities[1:])
    claims["return_reason"] = np.where(claims["return_requested"] == 1, sampled_reasons, "none")

    claims["covered_claim_flag"] = (
        (claims["claim_eligible_flag"] == 1)
        & (claims["return_requested"] == 1)
        & (claims["return_approved"] == 1)
        & (claims["refund_without_return"] == 0)
        & (claims["freight_value_capped"] > 0)
    ).astype(int)
    claims["covered_claim_probability"] = (
        claims["return_probability"] * approval_probability * (1 - refund_without_return_probability)
    )
    claims["covered_claim_probability"] = np.where(
        (claims["claim_eligible_flag"] == 1) & (claims["freight_value_capped"] > 0),
        claims["covered_claim_probability"],
        0.0,
    )

    claims["claim_type"] = np.where(
        claims["covered_claim_flag"] == 1,
        "return_shipping",
        "none",
    )

    severity_noise = rng.uniform(0.8, 1.2, size=len(claims))
    partial_refund_multiplier = np.where(claims["partial_refund"] == 1, 0.50, 1.00)
    claims["gross_loss"] = np.where(
        claims["covered_claim_flag"] == 1,
        claims["freight_value_capped"] * severity_noise * partial_refund_multiplier,
        0.0,
    )

    recovery_probability = 0.05
    recovery_multiplier = rng.uniform(0.10, 0.30, size=len(claims))
    has_recovery = (claims["covered_claim_flag"] == 1) & (
        rng.random(len(claims)) < recovery_probability
    )
    claims["recovery_from_carrier"] = np.where(
        has_recovery,
        claims["gross_loss"] * recovery_multiplier,
        0.0,
    )

    claims["paid_loss"] = (claims["gross_loss"] - claims["recovery_from_carrier"]).clip(lower=0)
    claims["net_loss"] = claims["paid_loss"]

    claims["claim_status"] = np.select(
        [
            claims["claim_eligible_flag"] == 0,
            claims["covered_claim_flag"] == 1,
            (claims["return_requested"] == 1) & (claims["return_approved"] == 0),
            (claims["return_approved"] == 1) & (claims["refund_without_return"] == 1),
            claims["return_requested"] == 1,
        ],
        [
            "not_eligible",
            "paid",
            "declined_not_approved",
            "closed_refund_without_return",
            "closed_no_covered_loss",
        ],
        default="no_return",
    )

    return claims


def make_summary(claims: pd.DataFrame) -> dict:
    eligible = claims["claim_eligible_flag"] == 1
    covered = claims["covered_claim_flag"] == 1
    returned = claims["return_requested"] == 1

    return {
        "random_seed": RANDOM_SEED,
        "parameters": {
            "base_return_rate": BASE_RETURN_RATE,
            "min_return_probability": MIN_RETURN_PROBABILITY,
            "max_return_probability": MAX_RETURN_PROBABILITY,
            "freight_value_cap": FREIGHT_VALUE_CAP,
            "freight_to_price_ratio_cap": FREIGHT_TO_PRICE_RATIO_CAP,
            "recovery_probability": 0.05,
        },
        "rows": int(len(claims)),
        "eligible_exposures": int(eligible.sum()),
        "ineligible_exposures": int((~eligible).sum()),
        "return_requested_count": int(returned.sum()),
        "return_requested_rate_all": float(returned.mean()),
        "return_requested_rate_eligible": float(returned[eligible].mean()),
        "return_approved_count": int(claims["return_approved"].sum()),
        "refund_without_return_count": int(claims["refund_without_return"].sum()),
        "partial_refund_count": int(claims["partial_refund"].sum()),
        "covered_claim_count": int(covered.sum()),
        "covered_claim_frequency_all": float(covered.mean()),
        "covered_claim_frequency_eligible": float(covered[eligible].mean()),
        "total_gross_loss": float(claims["gross_loss"].sum()),
        "total_recovery_from_carrier": float(claims["recovery_from_carrier"].sum()),
        "total_paid_loss": float(claims["paid_loss"].sum()),
        "total_net_loss": float(claims["net_loss"].sum()),
        "average_paid_loss_among_claims": float(claims.loc[covered, "paid_loss"].mean()),
        "pure_premium_per_all_exposure": float(claims["net_loss"].sum() / len(claims)),
        "pure_premium_per_eligible_exposure": float(claims.loc[eligible, "net_loss"].sum() / eligible.sum()),
        "imputation": {
            "product_weight_g_imputed_rows": int(claims["product_weight_g_imputed_flag"].sum()),
            "product_volume_cm3_imputed_rows": int(
                claims["product_volume_cm3_imputed_flag"].sum()
            ),
        },
        "claim_status": claims["claim_status"].value_counts().to_dict(),
        "claim_type": claims["claim_type"].value_counts().to_dict(),
        "return_reason": claims["return_reason"].value_counts().to_dict(),
    }


def main() -> None:
    exposure = read_exposure_table()
    claims = build_synthetic_claims(exposure)
    summary = make_summary(claims)

    claims.to_csv(OUTPUT_PATH, index=False)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
