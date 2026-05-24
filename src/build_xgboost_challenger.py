from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import (
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import build_glm_pricing as glm_pricing  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GLM_PRICING_PATH = PROCESSED_DIR / "pricing_glm.csv"

PRICING_OUTPUT_PATH = PROCESSED_DIR / "pricing_xgboost_challenger.csv"
SUMMARY_PATH = PROCESSED_DIR / "xgboost_challenger_summary.json"
COMPARISON_PATH = PROCESSED_DIR / "model_comparison_glm_vs_xgboost.csv"
CALIBRATION_PATH = PROCESSED_DIR / "xgboost_challenger_pure_premium_calibration.csv"

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

CATEGORICAL_FEATURES = [
    "category_group",
    "route_group",
    "cross_state_flag_cat",
    "purchase_month_cat",
    "purchase_weekday_cat",
]

LOG_NUMERIC_FEATURES = [f"log_{column}" for column in NUMERIC_FEATURES]
MODEL_FEATURES = [*CATEGORICAL_FEATURES, *LOG_NUMERIC_FEATURES]

XGB_FREQUENCY_PARAMS = {
    "n_estimators": 500,
    "max_depth": 2,
    "learning_rate": 0.03,
    "subsample": 0.80,
    "colsample_bytree": 0.80,
    "reg_lambda": 5,
    "min_child_weight": 20,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": RANDOM_SEED,
    "n_jobs": 4,
}

XGB_SEVERITY_PARAMS = {
    "n_estimators": 350,
    "max_depth": 3,
    "learning_rate": 0.04,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "objective": "reg:squarederror",
    "random_state": RANDOM_SEED,
    "n_jobs": 4,
}

LEAKAGE_FIELDS = [
    "return_probability",
    "covered_claim_probability",
    "return_factor_category",
    "return_factor_route",
    "return_factor_freight_ratio",
    "return_factor_size",
    "return_factor_month",
    "return_requested",
    "return_approved",
    "refund_without_return",
    "partial_refund",
    "request_days_after_delivery",
    "return_reason",
    "claim_type",
    "gross_loss",
    "paid_loss",
    "net_loss",
    "claim_status",
]

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
    "glm_frequency",
    "glm_severity",
    "glm_expected_loss",
    "glm_commercial_premium",
    "category_group",
    "route_group",
    "challenger_model_family",
    "challenger_frequency",
    "challenger_severity",
    "challenger_expected_loss_raw",
    "challenger_calibration_factor",
    "challenger_expected_loss",
    "challenger_commercial_premium",
    "challenger_expected_loss_ratio_to_glm",
    "challenger_risk_score_decile",
]


def read_glm_pricing() -> pd.DataFrame:
    return pd.read_csv(GLM_PRICING_PATH)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def selected_levels(frame: pd.DataFrame, column: str, min_exposure: int) -> set[str]:
    counts = frame[column].fillna("Unknown").astype(str).value_counts()
    return set(counts[counts >= min_exposure].index)


def prepare_challenger_features(
    frame: pd.DataFrame,
    *,
    category_levels: set[str],
    route_levels: set[str],
) -> pd.DataFrame:
    prepared = frame.copy()

    raw_category = prepared["product_category_name_english"].fillna("Unknown").astype(str)
    raw_route = prepared["route_state"].fillna("Unknown").astype(str)
    prepared["category_group"] = raw_category.where(raw_category.isin(category_levels), "Other")
    prepared["route_group"] = raw_route.where(raw_route.isin(route_levels), "Other")
    prepared["cross_state_flag_cat"] = prepared["cross_state_flag"].fillna(0).astype(int).astype(str)
    prepared["purchase_month_cat"] = prepared["purchase_month"].fillna(0).astype(int).astype(str)
    prepared["purchase_weekday_cat"] = prepared["purchase_weekday"].fillna(0).astype(int).astype(str)

    for column in NUMERIC_FEATURES:
        prepared[column] = prepared[column].fillna(0).clip(lower=0)
        prepared[f"log_{column}"] = np.log1p(prepared[column])

    return prepared


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("numeric", "passthrough", LOG_NUMERIC_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def load_xgboost_classes() -> tuple[Any | None, Any | None]:
    try:
        from xgboost import XGBClassifier, XGBRegressor

        return XGBClassifier, XGBRegressor
    except ImportError:
        return None, None


def model_family_name() -> str:
    xgb_classifier, _ = load_xgboost_classes()
    if xgb_classifier is None:
        return "sklearn_hist_gradient_boosting_fallback"
    return "xgboost"


def make_frequency_model() -> Pipeline:
    xgb_classifier, _ = load_xgboost_classes()
    if xgb_classifier is not None:
        estimator = xgb_classifier(**XGB_FREQUENCY_PARAMS)
    else:
        estimator = HistGradientBoostingClassifier(
            max_iter=250,
            learning_rate=0.05,
            max_leaf_nodes=31,
            l2_regularization=0.01,
            random_state=RANDOM_SEED,
        )

    return Pipeline(
        steps=[
            ("preprocess", make_preprocessor()),
            ("model", estimator),
        ]
    )


def make_severity_model() -> Pipeline:
    _, xgb_regressor = load_xgboost_classes()
    if xgb_regressor is not None:
        estimator = xgb_regressor(**XGB_SEVERITY_PARAMS)
    else:
        estimator = HistGradientBoostingRegressor(
            max_iter=250,
            learning_rate=0.05,
            max_leaf_nodes=31,
            l2_regularization=0.01,
            random_state=RANDOM_SEED,
        )

    return Pipeline(
        steps=[
            ("preprocess", make_preprocessor()),
            ("model", estimator),
        ]
    )


def predict_frequency(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(frame[MODEL_FEATURES])[:, 1]
    return np.clip(probabilities, 0.0, 1.0)


def predict_severity(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    log_prediction = model.predict(frame[MODEL_FEATURES])
    return np.maximum(np.expm1(log_prediction), 0.01)


def fit_challenger(train_eligible: pd.DataFrame) -> tuple[Pipeline, Pipeline]:
    train_claims = train_eligible[
        (train_eligible["covered_claim_flag"] == 1) & (train_eligible["net_loss"] > 0)
    ].copy()
    if train_claims.empty:
        raise ValueError("Cannot fit severity model because there are no covered claims in training data.")

    frequency_model = make_frequency_model()
    severity_model = make_severity_model()

    frequency_model.fit(
        train_eligible[MODEL_FEATURES],
        train_eligible["covered_claim_flag"].astype(int),
    )
    severity_model.fit(
        train_claims[MODEL_FEATURES],
        np.log1p(train_claims["net_loss"]),
    )
    return frequency_model, severity_model


def score_challenger(
    frame: pd.DataFrame,
    frequency_model: Pipeline,
    severity_model: Pipeline,
    *,
    prefix: str,
) -> pd.DataFrame:
    scored = frame.copy()
    scored[f"{prefix}_frequency"] = predict_frequency(frequency_model, scored)
    scored[f"{prefix}_severity"] = predict_severity(severity_model, scored)
    scored[f"{prefix}_expected_loss_raw"] = (
        scored[f"{prefix}_frequency"] * scored[f"{prefix}_severity"]
    )
    return scored


def add_glm_validation_predictions(
    train_eligible_raw: pd.DataFrame,
    test_eligible_raw: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    category_levels = glm_pricing.selected_levels(
        train_eligible_raw,
        "product_category_name_english",
        CATEGORY_MIN_EXPOSURE,
    )
    route_levels = glm_pricing.selected_levels(
        train_eligible_raw,
        "route_state",
        ROUTE_MIN_EXPOSURE,
    )
    train_eligible = glm_pricing.prepare_features(
        train_eligible_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    test_eligible = glm_pricing.prepare_features(
        test_eligible_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )

    train_claims = train_eligible[
        (train_eligible["covered_claim_flag"] == 1) & (train_eligible["net_loss"] > 0)
    ].copy()
    if train_claims.empty:
        raise ValueError("Cannot fit GLM severity model because there are no covered claims in training data.")

    frequency_model = glm_pricing.fit_frequency_model(train_eligible)
    severity_model = glm_pricing.fit_severity_model(train_claims)

    for scored in [train_eligible, test_eligible]:
        scored["glm_validation_frequency"] = frequency_model.predict(scored)
        scored["glm_validation_severity"] = severity_model.predict(scored)
        scored["glm_validation_expected_loss"] = (
            scored["glm_validation_frequency"] * scored["glm_validation_severity"]
        )

    return train_eligible, test_eligible


def add_prediction_deciles(
    frame: pd.DataFrame,
    prediction_column: str,
    output_column: str,
) -> pd.Series:
    try:
        return (
            pd.qcut(
                frame[prediction_column].rank(method="first"),
                q=10,
                labels=False,
                duplicates="drop",
            )
            + 1
        )
    except ValueError:
        return pd.Series(1, index=frame.index)


def metric_record(
    frame: pd.DataFrame,
    *,
    model_name: str,
    model_role: str,
    model_family: str,
    split: str,
    frequency_column: str,
    severity_column: str,
    expected_loss_column: str,
) -> dict[str, float | int | str]:
    claims = frame[(frame["covered_claim_flag"] == 1) & (frame["net_loss"] > 0)].copy()
    actual_total_loss = float(frame["net_loss"].sum())
    predicted_total_loss = float(frame[expected_loss_column].sum())
    commercial_premium = predicted_total_loss / TARGET_LOSS_RATIO

    return {
        "model_name": model_name,
        "model_role": model_role,
        "model_family": model_family,
        "split": split,
        "exposures": int(len(frame)),
        "actual_claims": int(frame["covered_claim_flag"].sum()),
        "actual_frequency": float(frame["covered_claim_flag"].mean()),
        "predicted_frequency": float(frame[frequency_column].mean()),
        "frequency_actual_to_expected": safe_divide(
            float(frame["covered_claim_flag"].sum()),
            float(frame[frequency_column].sum()),
        ),
        "frequency_auc": float(roc_auc_score(frame["covered_claim_flag"], frame[frequency_column])),
        "frequency_brier_score": float(
            brier_score_loss(frame["covered_claim_flag"], frame[frequency_column])
        ),
        "claims_for_severity": int(len(claims)),
        "actual_severity": float(claims["net_loss"].mean()),
        "predicted_severity": float(claims[severity_column].mean()),
        "severity_actual_to_expected": safe_divide(
            float(claims["net_loss"].sum()),
            float(claims[severity_column].sum()),
        ),
        "severity_mae": float(mean_absolute_error(claims["net_loss"], claims[severity_column])),
        "severity_rmse": float(np.sqrt(mean_squared_error(claims["net_loss"], claims[severity_column]))),
        "actual_total_loss": actual_total_loss,
        "predicted_total_loss": predicted_total_loss,
        "pure_premium_actual_to_expected": safe_divide(actual_total_loss, predicted_total_loss),
        "actual_pure_premium": float(frame["net_loss"].mean()),
        "predicted_pure_premium": float(frame[expected_loss_column].mean()),
        "commercial_premium": commercial_premium,
        "loss_ratio": safe_divide(actual_total_loss, commercial_premium),
    }


def calibration_frame(
    frame: pd.DataFrame,
    *,
    model_name: str,
    model_family: str,
    split: str,
    frequency_column: str,
    expected_loss_column: str,
) -> pd.DataFrame:
    scored = frame.copy()
    scored["prediction_decile"] = add_prediction_deciles(
        scored,
        expected_loss_column,
        "prediction_decile",
    )
    grouped = (
        scored.groupby("prediction_decile", dropna=False)
        .agg(
            exposures=("covered_claim_flag", "size"),
            actual_claims=("covered_claim_flag", "sum"),
            predicted_claims=(frequency_column, "sum"),
            actual_total_loss=("net_loss", "sum"),
            predicted_total_loss=(expected_loss_column, "sum"),
            actual_frequency=("covered_claim_flag", "mean"),
            predicted_frequency=(frequency_column, "mean"),
            actual_pure_premium=("net_loss", "mean"),
            predicted_pure_premium=(expected_loss_column, "mean"),
        )
        .reset_index()
    )
    grouped["actual_to_expected"] = np.where(
        grouped["predicted_total_loss"] > 0,
        grouped["actual_total_loss"] / grouped["predicted_total_loss"],
        0.0,
    )
    grouped.insert(0, "split", split)
    grouped.insert(0, "model_family", model_family)
    grouped.insert(0, "model_name", model_name)
    return grouped


def build_validation_outputs(pricing: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    train_orders, test_orders = glm_pricing.make_order_split(pricing)
    eligible = pricing[pricing["claim_eligible_flag"] == 1].copy()
    train_eligible_raw = eligible[eligible["order_id"].isin(train_orders)].copy()
    test_eligible_raw = eligible[eligible["order_id"].isin(test_orders)].copy()

    glm_train, glm_test = add_glm_validation_predictions(train_eligible_raw, test_eligible_raw)

    category_levels = selected_levels(
        train_eligible_raw,
        "product_category_name_english",
        CATEGORY_MIN_EXPOSURE,
    )
    route_levels = selected_levels(train_eligible_raw, "route_state", ROUTE_MIN_EXPOSURE)
    train_eligible = prepare_challenger_features(
        train_eligible_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    test_eligible = prepare_challenger_features(
        test_eligible_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )

    frequency_model, severity_model = fit_challenger(train_eligible)
    train_scored = score_challenger(
        train_eligible,
        frequency_model,
        severity_model,
        prefix="challenger_validation",
    )
    test_scored = score_challenger(
        test_eligible,
        frequency_model,
        severity_model,
        prefix="challenger_validation",
    )

    train_raw_expected_loss = float(train_scored["challenger_validation_expected_loss_raw"].sum())
    train_actual_loss = float(train_scored["net_loss"].sum())
    calibration_factor = safe_divide(train_actual_loss, train_raw_expected_loss)

    for scored in [train_scored, test_scored]:
        scored["challenger_validation_expected_loss_calibrated"] = (
            scored["challenger_validation_expected_loss_raw"] * calibration_factor
        )

    model_family = model_family_name()
    records = []
    for split, frame in [("train", glm_train), ("test", glm_test)]:
        records.append(
            metric_record(
                frame,
                model_name="glm",
                model_role="current_pricing_model",
                model_family="statsmodels_binomial_gamma_glm",
                split=split,
                frequency_column="glm_validation_frequency",
                severity_column="glm_validation_severity",
                expected_loss_column="glm_validation_expected_loss",
            )
        )

    for split, frame in [("train", train_scored), ("test", test_scored)]:
        records.append(
            metric_record(
                frame,
                model_name="xgboost_challenger_raw",
                model_role="challenger_risk_score_uncalibrated",
                model_family=model_family,
                split=split,
                frequency_column="challenger_validation_frequency",
                severity_column="challenger_validation_severity",
                expected_loss_column="challenger_validation_expected_loss_raw",
            )
        )
        records.append(
            metric_record(
                frame,
                model_name="xgboost_challenger_calibrated",
                model_role="challenger_pricing_diagnostic",
                model_family=model_family,
                split=split,
                frequency_column="challenger_validation_frequency",
                severity_column="challenger_validation_severity",
                expected_loss_column="challenger_validation_expected_loss_calibrated",
            )
        )

    comparison = pd.DataFrame(records)
    calibration = pd.concat(
        [
            calibration_frame(
                glm_test,
                model_name="glm",
                model_family="statsmodels_binomial_gamma_glm",
                split="test",
                frequency_column="glm_validation_frequency",
                expected_loss_column="glm_validation_expected_loss",
            ),
            calibration_frame(
                test_scored,
                model_name="xgboost_challenger_raw",
                model_family=model_family,
                split="test",
                frequency_column="challenger_validation_frequency",
                expected_loss_column="challenger_validation_expected_loss_raw",
            ),
            calibration_frame(
                test_scored,
                model_name="xgboost_challenger_calibrated",
                model_family=model_family,
                split="test",
                frequency_column="challenger_validation_frequency",
                expected_loss_column="challenger_validation_expected_loss_calibrated",
            ),
        ],
        ignore_index=True,
    )

    validation_context = {
        "train_orders": int(len(train_orders)),
        "test_orders": int(len(test_orders)),
        "train_eligible_exposures": int(len(train_eligible)),
        "test_eligible_exposures": int(len(test_eligible)),
        "category_levels_plus_other": int(len(category_levels) + 1),
        "route_levels_plus_other": int(len(route_levels) + 1),
        "train_raw_expected_loss": train_raw_expected_loss,
        "train_actual_loss": train_actual_loss,
        "validation_calibration_factor": calibration_factor,
    }
    return comparison, calibration, validation_context


def build_final_pricing(pricing: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    eligible = pricing[pricing["claim_eligible_flag"] == 1].copy()
    category_levels = selected_levels(
        eligible,
        "product_category_name_english",
        CATEGORY_MIN_EXPOSURE,
    )
    route_levels = selected_levels(eligible, "route_state", ROUTE_MIN_EXPOSURE)

    eligible_features = prepare_challenger_features(
        eligible,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    frequency_model, severity_model = fit_challenger(eligible_features)

    all_features = prepare_challenger_features(
        pricing,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    scored = score_challenger(
        all_features,
        frequency_model,
        severity_model,
        prefix="challenger",
    )

    is_eligible = scored["claim_eligible_flag"] == 1
    scored.loc[~is_eligible, "challenger_frequency"] = 0.0
    scored.loc[~is_eligible, "challenger_severity"] = 0.0
    scored.loc[~is_eligible, "challenger_expected_loss_raw"] = 0.0

    raw_total_expected_loss = float(scored.loc[is_eligible, "challenger_expected_loss_raw"].sum())
    actual_total_loss = float(scored.loc[is_eligible, "net_loss"].sum())
    calibration_factor = safe_divide(actual_total_loss, raw_total_expected_loss)

    scored["challenger_calibration_factor"] = np.where(is_eligible, calibration_factor, 0.0)
    scored["challenger_expected_loss"] = np.where(
        is_eligible,
        scored["challenger_expected_loss_raw"] * calibration_factor,
        0.0,
    )
    scored["challenger_commercial_premium"] = scored["challenger_expected_loss"] / TARGET_LOSS_RATIO
    scored["challenger_expected_loss_ratio_to_glm"] = np.where(
        scored["glm_expected_loss"] > 0,
        scored["challenger_expected_loss"] / scored["glm_expected_loss"],
        0.0,
    )
    scored["challenger_risk_score_decile"] = 0
    scored.loc[is_eligible, "challenger_risk_score_decile"] = add_prediction_deciles(
        scored.loc[is_eligible],
        "challenger_expected_loss",
        "challenger_risk_score_decile",
    ).astype(int)
    scored["target_loss_ratio"] = TARGET_LOSS_RATIO
    scored["challenger_model_family"] = model_family_name()

    pricing_output = scored[OUTPUT_COLUMNS].copy()

    final_context = {
        "eligible_exposures": int(is_eligible.sum()),
        "category_levels_plus_other": int(len(category_levels) + 1),
        "route_levels_plus_other": int(len(route_levels) + 1),
        "raw_expected_total_loss": raw_total_expected_loss,
        "actual_total_loss": actual_total_loss,
        "final_calibration_factor": calibration_factor,
        "calibrated_expected_total_loss": float(
            pricing_output.loc[
                pricing_output["claim_eligible_flag"] == 1,
                "challenger_expected_loss",
            ].sum()
        ),
        "challenger_total_commercial_premium": float(
            pricing_output.loc[
                pricing_output["claim_eligible_flag"] == 1,
                "challenger_commercial_premium",
            ].sum()
        ),
    }
    final_context["challenger_actual_to_expected"] = safe_divide(
        final_context["actual_total_loss"],
        final_context["calibrated_expected_total_loss"],
    )
    final_context["challenger_loss_ratio"] = safe_divide(
        final_context["actual_total_loss"],
        final_context["challenger_total_commercial_premium"],
    )

    return pricing_output, final_context


def make_summary(
    pricing: pd.DataFrame,
    comparison: pd.DataFrame,
    validation_context: dict,
    final_context: dict,
) -> dict:
    model_family = model_family_name()
    test_rows = comparison[comparison["split"] == "test"].copy()
    best_auc_row = test_rows.sort_values("frequency_auc", ascending=False).iloc[0].to_dict()
    calibrated_test = test_rows[
        test_rows["model_name"] == "xgboost_challenger_calibrated"
    ].iloc[0].to_dict()
    glm_test = test_rows[test_rows["model_name"] == "glm"].iloc[0].to_dict()

    return {
        "parameters": {
            "target_loss_ratio": TARGET_LOSS_RATIO,
            "random_seed": RANDOM_SEED,
            "test_size": TEST_SIZE,
            "pricing_unit": "order_id + order_item_id + seller_id + product_id",
            "requested_model": "xgboost challenger",
            "actual_model_family": model_family,
            "xgboost_installed": model_family == "xgboost",
            "frequency_target": "covered_claim_flag",
            "severity_target": "net_loss on covered claims only",
            "calibration": "raw challenger expected loss multiplied by train-set A/E for validation and portfolio A/E for final full-data output",
            "xgboost_frequency_params": XGB_FREQUENCY_PARAMS if model_family == "xgboost" else None,
            "xgboost_severity_params": XGB_SEVERITY_PARAMS if model_family == "xgboost" else None,
        },
        "input": {
            "source": str(GLM_PRICING_PATH.relative_to(PROJECT_ROOT)),
            "rows": int(len(pricing)),
            "eligible_exposures": int((pricing["claim_eligible_flag"] == 1).sum()),
            "unique_exposure_keys": int(
                pricing[["order_id", "order_item_id", "seller_id", "product_id"]]
                .drop_duplicates()
                .shape[0]
            ),
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
            "model_features_after_preprocessing": MODEL_FEATURES,
            "seller_id_used_as_feature": False,
            "excluded_leakage_fields": LEAKAGE_FIELDS,
        },
        "validation": {
            "context": validation_context,
            "test_glm": glm_test,
            "test_challenger_calibrated": calibrated_test,
            "best_test_frequency_auc": best_auc_row,
        },
        "final_portfolio_pricing": final_context,
        "interpretation": {
            "challenger_frequency_auc_minus_glm": float(
                calibrated_test["frequency_auc"] - glm_test["frequency_auc"]
            ),
            "challenger_test_ae_minus_glm": float(
                calibrated_test["pure_premium_actual_to_expected"]
                - glm_test["pure_premium_actual_to_expected"]
            ),
            "note": "A better AUC means better ranking, not automatic pricing superiority. A/E and loss ratio show rate-level calibration.",
        },
        "output": {
            "pricing_xgboost_challenger": str(PRICING_OUTPUT_PATH.relative_to(PROJECT_ROOT)),
            "xgboost_challenger_summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT)),
            "model_comparison_glm_vs_xgboost": str(COMPARISON_PATH.relative_to(PROJECT_ROOT)),
            "xgboost_challenger_pure_premium_calibration": str(
                CALIBRATION_PATH.relative_to(PROJECT_ROOT)
            ),
        },
    }


def main() -> None:
    pricing = read_glm_pricing()
    comparison, calibration, validation_context = build_validation_outputs(pricing)
    pricing_output, final_context = build_final_pricing(pricing)

    pricing_output.to_csv(PRICING_OUTPUT_PATH, index=False)
    comparison.to_csv(COMPARISON_PATH, index=False)
    calibration.to_csv(CALIBRATION_PATH, index=False)

    summary = make_summary(pricing, comparison, validation_context, final_context)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {PRICING_OUTPUT_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {COMPARISON_PATH}")
    print(f"Wrote {CALIBRATION_PATH}")
    print(json.dumps(summary["validation"]["test_challenger_calibrated"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
