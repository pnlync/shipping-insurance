from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import DMatrix


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import build_glm_pricing as glm_pricing  # noqa: E402
from src import build_xgboost_challenger as challenger  # noqa: E402


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GLM_PRICING_PATH = PROCESSED_DIR / "pricing_glm.csv"

SUMMARY_PATH = PROCESSED_DIR / "xgboost_interpretability_summary.json"
FREQUENCY_IMPORTANCE_PATH = PROCESSED_DIR / "xgboost_frequency_feature_importance.csv"
SEVERITY_IMPORTANCE_PATH = PROCESSED_DIR / "xgboost_severity_feature_importance.csv"
FREQUENCY_SHAP_PATH = PROCESSED_DIR / "xgboost_frequency_shap_summary.csv"
SEVERITY_SHAP_PATH = PROCESSED_DIR / "xgboost_severity_shap_summary.csv"
FREQUENCY_BASE_FEATURE_PATH = PROCESSED_DIR / "xgboost_frequency_base_feature_summary.csv"
SEVERITY_BASE_FEATURE_PATH = PROCESSED_DIR / "xgboost_severity_base_feature_summary.csv"


IMPORTANCE_TYPES = ["weight", "gain", "cover", "total_gain", "total_cover"]


def read_pricing() -> pd.DataFrame:
    return pd.read_csv(GLM_PRICING_PATH)


def transformed_features(model, frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    preprocessor = model.named_steps["preprocess"]
    matrix = preprocessor.transform(frame[challenger.MODEL_FEATURES])
    feature_names = list(preprocessor.get_feature_names_out())
    return matrix, feature_names


def xgboost_estimator(model):
    return model.named_steps["model"]


def booster_feature_importance(model, model_name: str, feature_names: list[str]) -> pd.DataFrame:
    booster = xgboost_estimator(model).get_booster()
    frames = []
    for importance_type in IMPORTANCE_TYPES:
        scores = booster.get_score(importance_type=importance_type)
        frame = pd.DataFrame(
            {
                "encoded_feature": feature_names,
                importance_type: [
                    float(scores.get(feature_name, scores.get(f"f{index}", 0.0)))
                    for index, feature_name in enumerate(feature_names)
                ],
            }
        )
        frames.append(frame)

    importance = frames[0]
    for frame in frames[1:]:
        importance = importance.merge(frame, on="encoded_feature", how="left")

    importance.insert(0, "model", model_name)
    importance["base_feature"] = importance["encoded_feature"].map(base_feature_name)
    total_gain = float(importance["gain"].sum())
    importance["gain_share"] = np.where(
        total_gain > 0,
        importance["gain"] / total_gain,
        0.0,
    )
    return importance.sort_values(["gain", "total_gain", "encoded_feature"], ascending=[False, False, True])


def base_feature_name(encoded_feature: str) -> str:
    categorical_prefixes = [
        "category_group",
        "route_group",
        "cross_state_flag_cat",
        "purchase_month_cat",
        "purchase_weekday_cat",
    ]
    for prefix in categorical_prefixes:
        if encoded_feature == prefix or encoded_feature.startswith(f"{prefix}_"):
            return prefix
    return encoded_feature


def shap_contribution_summary(
    model,
    frame: pd.DataFrame,
    *,
    model_name: str,
    model_scale: str,
) -> pd.DataFrame:
    matrix, feature_names = transformed_features(model, frame)
    booster = xgboost_estimator(model).get_booster()
    contributions = booster.predict(
        DMatrix(matrix, feature_names=feature_names),
        pred_contribs=True,
    )

    feature_contributions = contributions[:, :-1]
    bias = contributions[:, -1]
    summary = pd.DataFrame(
        {
            "encoded_feature": feature_names,
            "mean_abs_contribution": np.abs(feature_contributions).mean(axis=0),
            "mean_contribution": feature_contributions.mean(axis=0),
            "positive_share": (feature_contributions > 0).mean(axis=0),
            "p05_contribution": np.quantile(feature_contributions, 0.05, axis=0),
            "p50_contribution": np.quantile(feature_contributions, 0.50, axis=0),
            "p95_contribution": np.quantile(feature_contributions, 0.95, axis=0),
        }
    )
    summary.insert(0, "model_scale", model_scale)
    summary.insert(0, "model", model_name)
    summary["base_feature"] = summary["encoded_feature"].map(base_feature_name)
    summary["bias_mean"] = float(np.mean(bias))
    total_mean_abs = float(summary["mean_abs_contribution"].sum())
    summary["mean_abs_contribution_share"] = np.where(
        total_mean_abs > 0,
        summary["mean_abs_contribution"] / total_mean_abs,
        0.0,
    )
    return summary.sort_values(
        ["mean_abs_contribution", "encoded_feature"],
        ascending=[False, True],
    )


def base_feature_summary(shap_summary: pd.DataFrame, model_name: str) -> pd.DataFrame:
    grouped = (
        shap_summary.groupby("base_feature", dropna=False)
        .agg(
            encoded_feature_count=("encoded_feature", "size"),
            mean_abs_contribution=("mean_abs_contribution", "sum"),
            mean_abs_contribution_share=("mean_abs_contribution_share", "sum"),
            mean_contribution=("mean_contribution", "sum"),
            positive_share=("positive_share", "mean"),
        )
        .reset_index()
    )
    grouped.insert(0, "model", model_name)
    return grouped.sort_values(
        ["mean_abs_contribution", "base_feature"],
        ascending=[False, True],
    )


def top_records(frame: pd.DataFrame, columns: list[str], n: int = 10) -> list[dict]:
    return frame.head(n)[columns].to_dict(orient="records")


def make_summary(
    pricing: pd.DataFrame,
    train_eligible: pd.DataFrame,
    test_eligible: pd.DataFrame,
    test_claims: pd.DataFrame,
    frequency_importance: pd.DataFrame,
    severity_importance: pd.DataFrame,
    frequency_shap: pd.DataFrame,
    severity_shap: pd.DataFrame,
    frequency_base: pd.DataFrame,
    severity_base: pd.DataFrame,
) -> dict:
    return {
        "parameters": {
            "input": str(GLM_PRICING_PATH.relative_to(PROJECT_ROOT)),
            "pricing_unit": "order_id + order_item_id + seller_id + product_id",
            "frequency_target": "covered_claim_flag",
            "severity_target": "log1p(net_loss) on covered claims only",
            "xgboost_frequency_params": challenger.XGB_FREQUENCY_PARAMS,
            "xgboost_severity_params": challenger.XGB_SEVERITY_PARAMS,
            "contribution_method": "XGBoost native booster.predict(pred_contribs=True)",
            "external_shap_package_used": False,
            "frequency_contribution_scale": "model margin / log-odds",
            "severity_contribution_scale": "log1p(net_loss)",
        },
        "input": {
            "rows": int(len(pricing)),
            "eligible_exposures": int((pricing["claim_eligible_flag"] == 1).sum()),
            "train_eligible_exposures": int(len(train_eligible)),
            "test_eligible_exposures": int(len(test_eligible)),
            "test_claims_for_severity": int(len(test_claims)),
            "unique_exposure_keys": int(
                pricing[["order_id", "order_item_id", "seller_id", "product_id"]]
                .drop_duplicates()
                .shape[0]
            ),
        },
        "feature_controls": {
            "model_features": challenger.MODEL_FEATURES,
            "seller_id_used_as_feature": False,
            "excluded_leakage_fields": challenger.LEAKAGE_FIELDS,
        },
        "top_frequency_gain_features": top_records(
            frequency_importance,
            ["encoded_feature", "base_feature", "gain", "gain_share"],
        ),
        "top_severity_gain_features": top_records(
            severity_importance,
            ["encoded_feature", "base_feature", "gain", "gain_share"],
        ),
        "top_frequency_contribution_features": top_records(
            frequency_shap,
            [
                "encoded_feature",
                "base_feature",
                "mean_abs_contribution",
                "mean_abs_contribution_share",
                "mean_contribution",
            ],
        ),
        "top_severity_contribution_features": top_records(
            severity_shap,
            [
                "encoded_feature",
                "base_feature",
                "mean_abs_contribution",
                "mean_abs_contribution_share",
                "mean_contribution",
            ],
        ),
        "top_frequency_base_features": top_records(
            frequency_base,
            [
                "base_feature",
                "encoded_feature_count",
                "mean_abs_contribution",
                "mean_abs_contribution_share",
            ],
        ),
        "top_severity_base_features": top_records(
            severity_base,
            [
                "base_feature",
                "encoded_feature_count",
                "mean_abs_contribution",
                "mean_abs_contribution_share",
            ],
        ),
        "output": {
            "xgboost_interpretability_summary": str(SUMMARY_PATH.relative_to(PROJECT_ROOT)),
            "xgboost_frequency_feature_importance": str(
                FREQUENCY_IMPORTANCE_PATH.relative_to(PROJECT_ROOT)
            ),
            "xgboost_severity_feature_importance": str(
                SEVERITY_IMPORTANCE_PATH.relative_to(PROJECT_ROOT)
            ),
            "xgboost_frequency_shap_summary": str(FREQUENCY_SHAP_PATH.relative_to(PROJECT_ROOT)),
            "xgboost_severity_shap_summary": str(SEVERITY_SHAP_PATH.relative_to(PROJECT_ROOT)),
            "xgboost_frequency_base_feature_summary": str(
                FREQUENCY_BASE_FEATURE_PATH.relative_to(PROJECT_ROOT)
            ),
            "xgboost_severity_base_feature_summary": str(
                SEVERITY_BASE_FEATURE_PATH.relative_to(PROJECT_ROOT)
            ),
        },
    }


def main() -> None:
    pricing = read_pricing()
    train_orders, test_orders = glm_pricing.make_order_split(pricing)
    eligible = pricing[pricing["claim_eligible_flag"] == 1].copy()
    train_raw = eligible[eligible["order_id"].isin(train_orders)].copy()
    test_raw = eligible[eligible["order_id"].isin(test_orders)].copy()

    category_levels = challenger.selected_levels(
        train_raw,
        "product_category_name_english",
        challenger.CATEGORY_MIN_EXPOSURE,
    )
    route_levels = challenger.selected_levels(
        train_raw,
        "route_state",
        challenger.ROUTE_MIN_EXPOSURE,
    )
    train_eligible = challenger.prepare_challenger_features(
        train_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    test_eligible = challenger.prepare_challenger_features(
        test_raw,
        category_levels=category_levels,
        route_levels=route_levels,
    )
    test_claims = test_eligible[
        (test_eligible["covered_claim_flag"] == 1) & (test_eligible["net_loss"] > 0)
    ].copy()

    frequency_model, severity_model = challenger.fit_challenger(train_eligible)

    frequency_matrix, frequency_feature_names = transformed_features(frequency_model, test_eligible)
    severity_matrix, severity_feature_names = transformed_features(severity_model, test_claims)
    if frequency_matrix.shape[1] != len(frequency_feature_names):
        raise ValueError("Frequency transformed feature count does not match feature names.")
    if severity_matrix.shape[1] != len(severity_feature_names):
        raise ValueError("Severity transformed feature count does not match feature names.")

    frequency_importance = booster_feature_importance(
        frequency_model,
        "xgboost_frequency",
        frequency_feature_names,
    )
    severity_importance = booster_feature_importance(
        severity_model,
        "xgboost_severity",
        severity_feature_names,
    )
    frequency_shap = shap_contribution_summary(
        frequency_model,
        test_eligible,
        model_name="xgboost_frequency",
        model_scale="log_odds_margin",
    )
    severity_shap = shap_contribution_summary(
        severity_model,
        test_claims,
        model_name="xgboost_severity",
        model_scale="log1p_net_loss",
    )

    frequency_base = base_feature_summary(frequency_shap, "xgboost_frequency")
    severity_base = base_feature_summary(severity_shap, "xgboost_severity")

    frequency_importance.to_csv(FREQUENCY_IMPORTANCE_PATH, index=False)
    severity_importance.to_csv(SEVERITY_IMPORTANCE_PATH, index=False)
    frequency_shap.to_csv(FREQUENCY_SHAP_PATH, index=False)
    severity_shap.to_csv(SEVERITY_SHAP_PATH, index=False)
    frequency_base.to_csv(FREQUENCY_BASE_FEATURE_PATH, index=False)
    severity_base.to_csv(SEVERITY_BASE_FEATURE_PATH, index=False)

    summary = make_summary(
        pricing,
        train_eligible,
        test_eligible,
        test_claims,
        frequency_importance,
        severity_importance,
        frequency_shap,
        severity_shap,
        frequency_base,
        severity_base,
    )
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {FREQUENCY_IMPORTANCE_PATH}")
    print(f"Wrote {SEVERITY_IMPORTANCE_PATH}")
    print(f"Wrote {FREQUENCY_SHAP_PATH}")
    print(f"Wrote {SEVERITY_SHAP_PATH}")
    print(f"Wrote {FREQUENCY_BASE_FEATURE_PATH}")
    print(f"Wrote {SEVERITY_BASE_FEATURE_PATH}")
    print(json.dumps(summary["top_frequency_base_features"][:5], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
