from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EDA_DIR = PROCESSED_DIR / "eda"
EXPOSURE_PATH = PROCESSED_DIR / "exposure_table.csv"

NUMERIC_COLUMNS = [
    "price",
    "freight_value",
    "freight_to_price_ratio",
    "product_weight_g",
    "product_volume_cm3",
    "estimated_delivery_days",
]

QUANTILES = [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.995, 1.0]
CAP_QUANTILES = [0.95, 0.99, 0.995]


def read_exposure_table() -> pd.DataFrame:
    return pd.read_csv(EXPOSURE_PATH, parse_dates=["order_purchase_timestamp"])


def format_quantile_column(q: float) -> str:
    if q == 0:
        return "min"
    if q == 1:
        return "max"
    return f"p{q * 100:g}"


def numeric_quantiles(exposure: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in NUMERIC_COLUMNS:
        quantiles = exposure[column].quantile(QUANTILES)
        row = {
            "field": column,
            "count": int(exposure[column].notna().sum()),
            "missing": int(exposure[column].isna().sum()),
            "mean": exposure[column].mean(),
            "std": exposure[column].std(),
        }
        row.update(
            {
                format_quantile_column(q): value
                for q, value in zip(QUANTILES, quantiles)
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def missing_summary(exposure: pd.DataFrame) -> pd.DataFrame:
    missing = exposure.isna().sum().reset_index()
    missing.columns = ["field", "missing_count"]
    missing["missing_rate"] = missing["missing_count"] / len(exposure)
    return missing[missing["missing_count"] > 0].sort_values(
        ["missing_rate", "field"], ascending=[False, True]
    )


def status_summary(exposure: pd.DataFrame) -> pd.DataFrame:
    summary = (
        exposure.groupby("order_status", dropna=False)
        .agg(
            exposures=("order_id", "size"),
            unique_orders=("order_id", "nunique"),
            freight_median=("freight_value", "median"),
            freight_mean=("freight_value", "mean"),
            freight_to_price_ratio_median=("freight_to_price_ratio", "median"),
            estimated_delivery_days_median=("estimated_delivery_days", "median"),
        )
        .reset_index()
        .sort_values("exposures", ascending=False)
    )
    summary["exposure_share"] = summary["exposures"] / len(exposure)
    return summary


def grouped_freight_summary(
    exposure: pd.DataFrame,
    group_column: str,
    *,
    min_exposures: int = 50,
) -> pd.DataFrame:
    summary = (
        exposure.groupby(group_column, dropna=False)
        .agg(
            exposures=("order_id", "size"),
            unique_orders=("order_id", "nunique"),
            unique_sellers=("seller_id", "nunique"),
            unique_products=("product_id", "nunique"),
            price_median=("price", "median"),
            freight_median=("freight_value", "median"),
            freight_mean=("freight_value", "mean"),
            freight_p95=("freight_value", lambda x: x.quantile(0.95)),
            freight_max=("freight_value", "max"),
            freight_to_price_ratio_median=("freight_to_price_ratio", "median"),
            freight_to_price_ratio_p95=("freight_to_price_ratio", lambda x: x.quantile(0.95)),
            freight_to_price_ratio_max=("freight_to_price_ratio", "max"),
            product_weight_g_median=("product_weight_g", "median"),
            product_volume_cm3_median=("product_volume_cm3", "median"),
            cross_state_rate=("cross_state_flag", "mean"),
            delivered_rate=("order_status", lambda x: (x == "delivered").mean()),
        )
        .reset_index()
    )
    summary["exposure_share"] = summary["exposures"] / len(exposure)
    summary = summary[summary["exposures"] >= min_exposures]
    return summary.sort_values(["exposures", group_column], ascending=[False, True])


def cap_diagnostics(exposure: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    rows = []
    for column in columns:
        series = exposure[column].dropna()
        for q in CAP_QUANTILES:
            cap = series.quantile(q)
            above_cap = int((series > cap).sum())
            capped_amount = (series - cap).clip(lower=0).sum()
            rows.append(
                {
                    "field": column,
                    "cap_quantile": format_quantile_column(q),
                    "cap_value": cap,
                    "rows_above_cap": above_cap,
                    "share_above_cap": above_cap / len(exposure),
                    "total_value_above_cap": capped_amount,
                }
            )
    return pd.DataFrame(rows)


def anomaly_diagnostics(exposure: pd.DataFrame) -> pd.DataFrame:
    checks = [
        ("freight_value_eq_0", exposure["freight_value"] == 0),
        ("freight_to_price_ratio_gt_1", exposure["freight_to_price_ratio"] > 1),
        ("freight_to_price_ratio_gt_2", exposure["freight_to_price_ratio"] > 2),
        ("product_weight_g_eq_0", exposure["product_weight_g"] == 0),
        ("product_weight_g_gt_30000", exposure["product_weight_g"] > 30000),
        ("product_volume_cm3_gt_200000", exposure["product_volume_cm3"] > 200000),
        ("estimated_delivery_days_gt_60", exposure["estimated_delivery_days"] > 60),
    ]
    rows = []
    for check_name, mask in checks:
        count = int(mask.sum())
        rows.append(
            {
                "check": check_name,
                "rows": count,
                "row_share": count / len(exposure),
            }
        )
    return pd.DataFrame(rows)


def top_extreme_rows(exposure: pd.DataFrame, column: str, n: int = 25) -> pd.DataFrame:
    columns = [
        "order_id",
        "order_item_id",
        "seller_id",
        "product_id",
        "product_category_name_english",
        "route_state",
        "order_status",
        "price",
        "freight_value",
        "freight_to_price_ratio",
        "product_weight_g",
        "product_volume_cm3",
    ]
    return exposure.sort_values(column, ascending=False).head(n)[columns]


def make_json_summary(
    exposure: pd.DataFrame,
    quantiles: pd.DataFrame,
    status: pd.DataFrame,
    missing: pd.DataFrame,
    caps: pd.DataFrame,
    anomalies: pd.DataFrame,
) -> dict:
    delivered = exposure[exposure["order_status"] == "delivered"]
    cross_state = exposure[exposure["cross_state_flag"] == 1]
    same_state = exposure[exposure["cross_state_flag"] == 0]

    def metric(column: str, frame: pd.DataFrame = exposure) -> dict:
        return {
            "median": float(frame[column].median()),
            "mean": float(frame[column].mean()),
            "p95": float(frame[column].quantile(0.95)),
            "p99": float(frame[column].quantile(0.99)),
            "max": float(frame[column].max()),
        }

    return {
        "rows": int(len(exposure)),
        "unique_orders": int(exposure["order_id"].nunique()),
        "delivered_rows": int(len(delivered)),
        "delivered_share": float(len(delivered) / len(exposure)),
        "non_delivered_rows": int(len(exposure) - len(delivered)),
        "cross_state_share": float(exposure["cross_state_flag"].mean()),
        "same_state_freight_value": metric("freight_value", same_state),
        "cross_state_freight_value": metric("freight_value", cross_state),
        "freight_value": metric("freight_value"),
        "freight_to_price_ratio": metric("freight_to_price_ratio"),
        "price": metric("price"),
        "product_weight_g": metric("product_weight_g"),
        "product_volume_cm3": metric("product_volume_cm3"),
        "missing_fields": missing.to_dict(orient="records"),
        "order_status": status.to_dict(orient="records"),
        "numeric_quantiles": quantiles.to_dict(orient="records"),
        "cap_diagnostics": caps.to_dict(orient="records"),
        "anomaly_diagnostics": anomalies.to_dict(orient="records"),
        "recommendations": {
            "first_claim_simulation_population": "Use delivered exposures only for the first version.",
            "freight_value_treatment": "Keep raw value for diagnostics; use p99 cap or log1p transform in modeling.",
            "freight_to_price_ratio_treatment": "Cap at p99 or bin before modeling because the right tail is dominated by low-price items.",
            "size_missing_handling": "Missing product size fields are rare; use category median imputation or drop for Phase 1.",
        },
    }


def main() -> None:
    EDA_DIR.mkdir(parents=True, exist_ok=True)
    exposure = read_exposure_table()

    quantiles = numeric_quantiles(exposure)
    missing = missing_summary(exposure)
    status = status_summary(exposure)
    category = grouped_freight_summary(exposure, "product_category_name_english")
    route = grouped_freight_summary(exposure, "route_state")
    caps = cap_diagnostics(
        exposure,
        ["freight_value", "freight_to_price_ratio", "product_weight_g", "product_volume_cm3"],
    )
    anomalies = anomaly_diagnostics(exposure)

    outputs = {
        "numeric_quantiles.csv": quantiles,
        "missing_summary.csv": missing,
        "order_status_summary.csv": status,
        "category_freight_summary.csv": category,
        "route_freight_summary.csv": route,
        "cap_diagnostics.csv": caps,
        "anomaly_diagnostics.csv": anomalies,
        "top_freight_value_rows.csv": top_extreme_rows(exposure, "freight_value"),
        "top_freight_to_price_ratio_rows.csv": top_extreme_rows(
            exposure, "freight_to_price_ratio"
        ),
        "top_product_weight_rows.csv": top_extreme_rows(exposure, "product_weight_g"),
        "top_product_volume_rows.csv": top_extreme_rows(exposure, "product_volume_cm3"),
    }

    for file_name, frame in outputs.items():
        frame.to_csv(EDA_DIR / file_name, index=False)

    summary = make_json_summary(exposure, quantiles, status, missing, caps, anomalies)
    (EDA_DIR / "exposure_eda_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Wrote EDA outputs to {EDA_DIR}")
    print(json.dumps(summary["recommendations"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
