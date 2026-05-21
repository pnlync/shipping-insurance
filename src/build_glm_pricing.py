from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.metrics import (
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CLAIMS_PATH = PROCESSED_DIR / "exposure_claims_synthetic.csv"
BASELINE_PATH = PROCESSED_DIR / "pricing_baseline.csv"

PRICING_OUTPUT_PATH = PROCESSED_DIR / "pricing_glm.csv"
SUMMARY_PATH = PROCESSED_DIR / "glm_pricing_summary.json"
FREQUENCY_COEFFICIENTS_PATH = PROCESSED_DIR / "glm_frequency_coefficients.csv"
SEVERITY_COEFFICIENTS_PATH = PROCESSED_DIR / "glm_severity_coefficients.csv"
FREQUENCY_CALIBRATION_PATH = PROCESSED_DIR / "glm_frequency_calibration.csv"
SEVERITY_CALIBRATION_PATH = PROCESSED_DIR / "glm_severity_calibration.csv"
PURE_PREMIUM_CALIBRATION_PATH = PROCESSED_DIR / "glm_pure_premium_calibration.csv"

TARGET_LOSS_RATIO = 0.60
RANDOM_SEED = 20260521
TEST_SIZE = 0.20
CATEGORY_MIN_EXPOSURE = 500
ROUTE_MIN_EXPOSURE = 500

NUMERIC_FEATURES = [
    "price",
    "freight_value_capped",
    "freight_to_price_ratio_capped",
    "product_weight_g_filled",
    "product_volume_cm3_filled",
    "estimated_delivery_days",
]

FORMULA_TERMS = [
    "C(category_group)",
    "C(route_group)",
    "C(cross_state_flag_cat)",
    "C(purchase_month_cat)",
    "C(purchase_weekday_cat)",
    "log_price",
    "log_freight_value_capped",
    "log_freight_to_price_ratio_capped",
    "log_product_weight_g_filled",
    "log_product_volume_cm3_filled",
    "log_estimated_delivery_days",
]

FREQUENCY_FORMULA = "covered_claim_flag ~ " + " + ".join(FORMULA_TERMS)
SEVERITY_FORMULA = "net_loss ~ " + " + ".join(FORMULA_TERMS)

OUTPUT_COLUMNS = [
    "order_id",
    "order_item_id",
    "seller_id",
    "product_id",
    "customer_id",
    "order_status",
    "product_category_name_english",
    "route_state",
    "cross_state_flag",
    "purchase_month",
    "purchase_weekday",
    "price",
    "freight_value",
    "freight_value_capped",
    "freight_to_price_ratio_capped",
    "product_weight_g_filled",
    "product_volume_cm3_filled",
    "estimated_delivery_days",
    "claim_eligible_flag",
    "covered_claim_flag",
    "paid_loss",
    "net_loss",
    "target_loss_ratio",
    "baseline_pure_premium",
    "baseline_commercial_premium",
    "category_group",
    "route_group",
    "glm_frequency",
    "glm_severity",
    "glm_expected_loss",
    "glm_commercial_premium",
    "glm_expected_loss_ratio_to_freight",
    "glm_expected_loss_ratio_to_baseline",
]


def read_claims() -> pd.DataFrame:
    return pd.read_csv(CLAIMS_PATH)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def make_order_split(claims: pd.DataFrame) -> tuple[set[str], set[str]]:
    rng = np.random.default_rng(RANDOM_SEED)
    order_ids = claims["order_id"].drop_duplicates().to_numpy()
    rng.shuffle(order_ids)
    test_count = int(round(len(order_ids) * TEST_SIZE))
    test_orders = set(order_ids[:test_count])
    train_orders = set(order_ids[test_count:])
    return train_orders, test_orders


def selected_levels(frame: pd.DataFrame, column: str, min_exposure: int) -> set[str]:
    counts = frame[column].fillna("Unknown").astype(str).value_counts()
    return set(counts[counts >= min_exposure].index)


def prepare_features(
    frame: pd.DataFrame,
    *,
    category_levels: set[str],
    route_levels: set[str],
) -> pd.DataFrame:
    prepared = frame.copy()

    prepared["category_group"] = (
        prepared["product_category_name_english"]
        .fillna("Unknown")
        .astype(str)
        .where(
            prepared["product_category_name_english"].fillna("Unknown").astype(str).isin(category_levels),
            "Other",
        )
    )
    prepared["route_group"] = (
        prepared["route_state"]
        .fillna("Unknown")
        .astype(str)
        .where(prepared["route_state"].fillna("Unknown").astype(str).isin(route_levels), "Other")
    )
    prepared["cross_state_flag_cat"] = prepared["cross_state_flag"].astype(int).astype(str)
    prepared["purchase_month_cat"] = prepared["purchase_month"].astype(int).astype(str)
    prepared["purchase_weekday_cat"] = prepared["purchase_weekday"].astype(int).astype(str)

    for column in NUMERIC_FEATURES:
        prepared[column] = prepared[column].fillna(0).clip(lower=0)
        prepared[f"log_{column}"] = np.log1p(prepared[column])

    return prepared


def fit_frequency_model(train: pd.DataFrame):
    return smf.glm(
        formula=FREQUENCY_FORMULA,
        data=train,
        family=sm.families.Binomial(),
    ).fit()


def fit_severity_model(train_claims: pd.DataFrame):
    return smf.glm(
        formula=SEVERITY_FORMULA,
        data=train_claims,
        family=sm.families.Gamma(link=sm.families.links.Log()),
    ).fit()


def coefficient_frame(model, model_name: str) -> pd.DataFrame:
    conf_int = model.conf_int()
    frame = pd.DataFrame(
        {
            "model": model_name,
            "term": model.params.index,
            "coefficient": model.params.values,
            "standard_error": model.bse.values,
            "p_value": model.pvalues.values,
            "conf_low": conf_int[0].values,
            "conf_high": conf_int[1].values,
        }
    )
    frame["relativity"] = np.exp(frame["coefficient"])
    frame["conf_low_relativity"] = np.exp(frame["conf_low"])
    frame["conf_high_relativity"] = np.exp(frame["conf_high"])
    return frame


def add_prediction_deciles(
    frame: pd.DataFrame,
    prediction_column: str,
    output_column: str = "prediction_decile",
) -> pd.DataFrame:
    out = frame.copy()
    try:
        out[output_column] = pd.qcut(
            out[prediction_column].rank(method="first"),
            q=10,
            labels=False,
            duplicates="drop",
        ) + 1
    except ValueError:
        out[output_column] = 1
    return out


def frequency_calibration(frame: pd.DataFrame) -> pd.DataFrame:
    scored = add_prediction_deciles(frame, "pred_frequency")
    return (
        scored.groupby("prediction_decile", dropna=False)
        .agg(
            exposures=("covered_claim_flag", "size"),
            actual_claims=("covered_claim_flag", "sum"),
            actual_frequency=("covered_claim_flag", "mean"),
            predicted_frequency=("pred_frequency", "mean"),
        )
        .reset_index()
    )


def severity_calibration(frame: pd.DataFrame) -> pd.DataFrame:
    scored = add_prediction_deciles(frame, "pred_severity")
    grouped = (
        scored.groupby("prediction_decile", dropna=False)
        .agg(
            claims=("net_loss", "size"),
            actual_total_loss=("net_loss", "sum"),
            predicted_total_loss=("pred_severity", "sum"),
            actual_severity=("net_loss", "mean"),
            predicted_severity=("pred_severity", "mean"),
        )
        .reset_index()
    )
    grouped["actual_to_expected"] = np.where(
        grouped["predicted_total_loss"] > 0,
        grouped["actual_total_loss"] / grouped["predicted_total_loss"],
        0.0,
    )
    return grouped


def pure_premium_calibration(frame: pd.DataFrame) -> pd.DataFrame:
    scored = add_prediction_deciles(frame, "pred_expected_loss")
    grouped = (
        scored.groupby("prediction_decile", dropna=False)
        .agg(
            exposures=("covered_claim_flag", "size"),
            actual_claims=("covered_claim_flag", "sum"),
            actual_total_loss=("net_loss", "sum"),
            predicted_total_loss=("pred_expected_loss", "sum"),
            actual_frequency=("covered_claim_flag", "mean"),
            predicted_frequency=("pred_frequency", "mean"),
            actual_pure_premium=("net_loss", "mean"),
            predicted_pure_premium=("pred_expected_loss", "mean"),
        )
        .reset_index()
    )
    grouped["actual_to_expected"] = np.where(
        grouped["predicted_total_loss"] > 0,
        grouped["actual_total_loss"] / grouped["predicted_total_loss"],
        0.0,
    )
    return grouped


def rmse(actual: pd.Series, predicted: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def model_metrics(
    frequency_train: pd.DataFrame,
    frequency_test: pd.DataFrame,
    severity_train: pd.DataFrame,
    severity_test: pd.DataFrame,
) -> dict:
    train_actual_loss = float(frequency_train["net_loss"].sum())
    train_expected_loss = float(frequency_train["pred_expected_loss"].sum())
    test_actual_loss = float(frequency_test["net_loss"].sum())
    test_expected_loss = float(frequency_test["pred_expected_loss"].sum())

    return {
        "frequency": {
            "train": {
                "exposures": int(len(frequency_train)),
                "actual_claims": int(frequency_train["covered_claim_flag"].sum()),
                "actual_frequency": float(frequency_train["covered_claim_flag"].mean()),
                "predicted_frequency": float(frequency_train["pred_frequency"].mean()),
                "auc": float(
                    roc_auc_score(
                        frequency_train["covered_claim_flag"],
                        frequency_train["pred_frequency"],
                    )
                ),
                "brier_score": float(
                    brier_score_loss(
                        frequency_train["covered_claim_flag"],
                        frequency_train["pred_frequency"],
                    )
                ),
            },
            "test": {
                "exposures": int(len(frequency_test)),
                "actual_claims": int(frequency_test["covered_claim_flag"].sum()),
                "actual_frequency": float(frequency_test["covered_claim_flag"].mean()),
                "predicted_frequency": float(frequency_test["pred_frequency"].mean()),
                "auc": float(
                    roc_auc_score(
                        frequency_test["covered_claim_flag"],
                        frequency_test["pred_frequency"],
                    )
                ),
                "brier_score": float(
                    brier_score_loss(
                        frequency_test["covered_claim_flag"],
                        frequency_test["pred_frequency"],
                    )
                ),
            },
        },
        "severity": {
            "train": {
                "claims": int(len(severity_train)),
                "actual_severity": float(severity_train["net_loss"].mean()),
                "predicted_severity": float(severity_train["pred_severity"].mean()),
                "mae": float(
                    mean_absolute_error(
                        severity_train["net_loss"],
                        severity_train["pred_severity"],
                    )
                ),
                "rmse": rmse(severity_train["net_loss"], severity_train["pred_severity"]),
            },
            "test": {
                "claims": int(len(severity_test)),
                "actual_severity": float(severity_test["net_loss"].mean()),
                "predicted_severity": float(severity_test["pred_severity"].mean()),
                "mae": float(
                    mean_absolute_error(
                        severity_test["net_loss"],
                        severity_test["pred_severity"],
                    )
                ),
                "rmse": rmse(severity_test["net_loss"], severity_test["pred_severity"]),
            },
        },
        "pure_premium": {
            "train": {
                "actual_total_loss": train_actual_loss,
                "predicted_total_loss": train_expected_loss,
                "actual_to_expected": safe_divide(train_actual_loss, train_expected_loss),
                "actual_pure_premium": float(frequency_train["net_loss"].mean()),
                "predicted_pure_premium": float(frequency_train["pred_expected_loss"].mean()),
            },
            "test": {
                "actual_total_loss": test_actual_loss,
                "predicted_total_loss": test_expected_loss,
                "actual_to_expected": safe_divide(test_actual_loss, test_expected_loss),
                "actual_pure_premium": float(frequency_test["net_loss"].mean()),
                "predicted_pure_premium": float(frequency_test["pred_expected_loss"].mean()),
            },
        },
    }


def read_baseline_columns(expected_rows: int) -> pd.DataFrame:
    columns = [
        "order_id",
        "order_item_id",
        "seller_id",
        "product_id",
        "baseline_pure_premium",
        "baseline_commercial_premium",
    ]
    baseline = pd.read_csv(BASELINE_PATH, usecols=columns)
    if len(baseline) != expected_rows:
        raise ValueError("pricing_baseline.csv row count does not match claims input.")
    return baseline


def build_summary(
    claims: pd.DataFrame,
    priced: pd.DataFrame,
    metrics: dict,
    frequency_model,
    severity_model,
    category_levels: set[str],
    route_levels: set[str],
) -> dict:
    eligible = priced["claim_eligible_flag"] == 1
    eligible_priced = priced[eligible]
    actual_total_loss = float(eligible_priced["net_loss"].sum())
    expected_total_loss = float(eligible_priced["glm_expected_loss"].sum())
    baseline_total_loss = float(eligible_priced["baseline_pure_premium"].sum())

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "random_seed": RANDOM_SEED,
            "test_size": TEST_SIZE,
            "category_min_exposure": CATEGORY_MIN_EXPOSURE,
            "route_min_exposure": ROUTE_MIN_EXPOSURE,
            "frequency_model": "Binomial GLM with logit link",
            "severity_model": "Gamma GLM with log link",
            "severity_target": "net_loss",
            "pricing_unit": "order_id + order_item_id + seller_id + product_id",
        },
        "input": {
            "rows": int(len(claims)),
            "unique_exposure_keys": int(
                claims[["order_id", "order_item_id", "seller_id", "product_id"]]
                .drop_duplicates()
                .shape[0]
            ),
            "eligible_exposures": int((claims["claim_eligible_flag"] == 1).sum()),
            "covered_claims": int(claims["covered_claim_flag"].sum()),
            "actual_total_net_loss": float(claims.loc[claims["claim_eligible_flag"] == 1, "net_loss"].sum()),
        },
        "feature_controls": {
            "allowed_features": [
                "product_category_name_english",
                "route_state",
                "cross_state_flag",
                "purchase_month",
                "purchase_weekday",
                *NUMERIC_FEATURES,
            ],
            "excluded_outcome_fields": [
                "return_requested",
                "return_approved",
                "refund_without_return",
                "partial_refund",
                "request_days_after_delivery",
                "return_reason",
                "covered_claim_flag",
                "claim_type",
                "gross_loss",
                "recovery_from_carrier",
                "paid_loss",
                "net_loss",
                "claim_status",
            ],
            "excluded_synthetic_generation_fields": [
                "return_probability",
                "covered_claim_probability",
                "return_factor_category",
                "return_factor_route",
                "return_factor_freight_ratio",
                "return_factor_size",
                "return_factor_month",
            ],
        },
        "selected_level_counts": {
            "category_levels_plus_other": len(category_levels) + 1,
            "route_levels_plus_other": len(route_levels) + 1,
        },
        "validation": metrics,
        "final_model_fit": {
            "frequency_aic": float(frequency_model.aic),
            "severity_aic": float(severity_model.aic),
            "frequency_nobs": int(frequency_model.nobs),
            "severity_nobs": int(severity_model.nobs),
        },
        "portfolio_pricing": {
            "actual_total_net_loss": actual_total_loss,
            "glm_expected_total_loss": expected_total_loss,
            "glm_actual_to_expected": safe_divide(actual_total_loss, expected_total_loss),
            "baseline_expected_total_loss": baseline_total_loss,
            "baseline_actual_to_expected": safe_divide(actual_total_loss, baseline_total_loss),
            "glm_mean_expected_loss": float(eligible_priced["glm_expected_loss"].mean()),
            "baseline_mean_expected_loss": float(eligible_priced["baseline_pure_premium"].mean()),
            "glm_total_commercial_premium": float(eligible_priced["glm_commercial_premium"].sum()),
            "glm_expected_loss_ratio": safe_divide(
                expected_total_loss,
                float(eligible_priced["glm_commercial_premium"].sum()),
            ),
        },
        "output": {
            "pricing_glm": str(PRICING_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
            "glm_pricing_summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT)),
            "glm_frequency_coefficients": str(FREQUENCY_COEFFICIENTS_PATH.relative_to(PROJECT_ROOT)),
            "glm_severity_coefficients": str(SEVERITY_COEFFICIENTS_PATH.relative_to(PROJECT_ROOT)),
            "glm_frequency_calibration": str(FREQUENCY_CALIBRATION_PATH.relative_to(PROJECT_ROOT)),
            "glm_severity_calibration": str(SEVERITY_CALIBRATION_PATH.relative_to(PROJECT_ROOT)),
            "glm_pure_premium_calibration": str(PURE_PREMIUM_CALIBRATION_PATH.relative_to(PROJECT_ROOT)),
        },
    }


def main() -> None:
    claims = read_claims()
    train_orders, test_orders = make_order_split(claims)

    eligible = claims[claims["claim_eligible_flag"] == 1].copy()
    train_eligible_raw = eligible[eligible["order_id"].isin(train_orders)].copy()
    test_eligible_raw = eligible[eligible["order_id"].isin(test_orders)].copy()

    category_levels_train = selected_levels(
        train_eligible_raw,
        "product_category_name_english",
        CATEGORY_MIN_EXPOSURE,
    )
    route_levels_train = selected_levels(train_eligible_raw, "route_state", ROUTE_MIN_EXPOSURE)

    train_eligible = prepare_features(
        train_eligible_raw,
        category_levels=category_levels_train,
        route_levels=route_levels_train,
    )
    test_eligible = prepare_features(
        test_eligible_raw,
        category_levels=category_levels_train,
        route_levels=route_levels_train,
    )

    train_claims = train_eligible[
        (train_eligible["covered_claim_flag"] == 1) & (train_eligible["net_loss"] > 0)
    ].copy()
    test_claims = test_eligible[
        (test_eligible["covered_claim_flag"] == 1) & (test_eligible["net_loss"] > 0)
    ].copy()

    frequency_validation_model = fit_frequency_model(train_eligible)
    severity_validation_model = fit_severity_model(train_claims)

    train_eligible["pred_frequency"] = frequency_validation_model.predict(train_eligible)
    test_eligible["pred_frequency"] = frequency_validation_model.predict(test_eligible)
    train_eligible["pred_severity"] = severity_validation_model.predict(train_eligible)
    test_eligible["pred_severity"] = severity_validation_model.predict(test_eligible)
    train_claims["pred_severity"] = severity_validation_model.predict(train_claims)
    test_claims["pred_severity"] = severity_validation_model.predict(test_claims)

    train_eligible["pred_expected_loss"] = (
        train_eligible["pred_frequency"] * train_eligible["pred_severity"]
    )
    test_eligible["pred_expected_loss"] = (
        test_eligible["pred_frequency"] * test_eligible["pred_severity"]
    )

    metrics = model_metrics(train_eligible, test_eligible, train_claims, test_claims)
    frequency_cal = frequency_calibration(test_eligible)
    severity_cal = severity_calibration(test_claims)
    pure_premium_cal = pure_premium_calibration(test_eligible)

    category_levels_full = selected_levels(eligible, "product_category_name_english", CATEGORY_MIN_EXPOSURE)
    route_levels_full = selected_levels(eligible, "route_state", ROUTE_MIN_EXPOSURE)
    eligible_full = prepare_features(
        eligible,
        category_levels=category_levels_full,
        route_levels=route_levels_full,
    )
    full_claims = eligible_full[
        (eligible_full["covered_claim_flag"] == 1) & (eligible_full["net_loss"] > 0)
    ].copy()

    frequency_model = fit_frequency_model(eligible_full)
    severity_model = fit_severity_model(full_claims)

    all_features = prepare_features(
        claims,
        category_levels=category_levels_full,
        route_levels=route_levels_full,
    )
    all_features["glm_frequency"] = frequency_model.predict(all_features)
    all_features["glm_severity"] = severity_model.predict(all_features)

    is_eligible = all_features["claim_eligible_flag"] == 1
    all_features["glm_frequency"] = np.where(is_eligible, all_features["glm_frequency"], 0.0)
    all_features["glm_severity"] = np.where(is_eligible, all_features["glm_severity"], 0.0)
    all_features["glm_expected_loss"] = all_features["glm_frequency"] * all_features["glm_severity"]
    all_features["glm_commercial_premium"] = all_features["glm_expected_loss"] / TARGET_LOSS_RATIO
    all_features["target_loss_ratio"] = TARGET_LOSS_RATIO

    baseline = read_baseline_columns(len(all_features))
    merge_columns = ["order_id", "order_item_id", "seller_id", "product_id"]
    priced = all_features.merge(baseline, on=merge_columns, how="left", validate="one_to_one")
    if priced["baseline_pure_premium"].isna().any():
        raise ValueError("Missing baseline pricing values after merge.")

    priced["glm_expected_loss_ratio_to_freight"] = np.where(
        priced["freight_value_capped"] > 0,
        priced["glm_expected_loss"] / priced["freight_value_capped"],
        0.0,
    )
    priced["glm_expected_loss_ratio_to_baseline"] = np.where(
        priced["baseline_pure_premium"] > 0,
        priced["glm_expected_loss"] / priced["baseline_pure_premium"],
        0.0,
    )

    pricing_output = priced[OUTPUT_COLUMNS].copy()
    pricing_output.to_csv(PRICING_OUTPUT_PATH, index=False)
    coefficient_frame(frequency_model, "frequency").to_csv(FREQUENCY_COEFFICIENTS_PATH, index=False)
    coefficient_frame(severity_model, "severity").to_csv(SEVERITY_COEFFICIENTS_PATH, index=False)
    frequency_cal.to_csv(FREQUENCY_CALIBRATION_PATH, index=False)
    severity_cal.to_csv(SEVERITY_CALIBRATION_PATH, index=False)
    pure_premium_cal.to_csv(PURE_PREMIUM_CALIBRATION_PATH, index=False)

    summary = build_summary(
        claims,
        pricing_output,
        metrics,
        frequency_model,
        severity_model,
        category_levels_full,
        route_levels_full,
    )
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {PRICING_OUTPUT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(json.dumps(summary["portfolio_pricing"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
