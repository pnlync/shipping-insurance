from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def read_raw_csv(file_name: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / file_name)


def build_exposure_table() -> pd.DataFrame:
    items = read_raw_csv("olist_order_items_dataset.csv")
    orders = read_raw_csv("olist_orders_dataset.csv")
    products = read_raw_csv("olist_products_dataset.csv")
    translations = read_raw_csv("product_category_name_translation.csv")
    customers = read_raw_csv("olist_customers_dataset.csv")
    sellers = read_raw_csv("olist_sellers_dataset.csv")

    orders = orders[
        [
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_estimated_delivery_date",
        ]
    ]

    products = products[
        [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ]
    ]

    customers = customers[
        [
            "customer_id",
            "customer_city",
            "customer_state",
            "customer_zip_code_prefix",
        ]
    ]

    sellers = sellers[
        [
            "seller_id",
            "seller_city",
            "seller_state",
            "seller_zip_code_prefix",
        ]
    ]

    exposure = (
        items.merge(orders, on="order_id", how="left", validate="many_to_one")
        .merge(products, on="product_id", how="left", validate="many_to_one")
        .merge(translations, on="product_category_name", how="left", validate="many_to_one")
        .merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(sellers, on="seller_id", how="left", validate="many_to_one")
    )

    exposure["product_category_name_english"] = exposure[
        "product_category_name_english"
    ].fillna("unknown")
    exposure["product_category_name"] = exposure["product_category_name"].fillna("unknown")

    exposure["product_volume_cm3"] = (
        exposure["product_length_cm"]
        * exposure["product_height_cm"]
        * exposure["product_width_cm"]
    )
    exposure["freight_to_price_ratio"] = exposure["freight_value"] / exposure["price"]
    exposure["route_state"] = exposure["seller_state"] + "_to_" + exposure["customer_state"]
    exposure["cross_state_flag"] = (exposure["seller_state"] != exposure["customer_state"]).astype(
        int
    )

    exposure["order_purchase_timestamp"] = pd.to_datetime(
        exposure["order_purchase_timestamp"], errors="coerce"
    )
    exposure["order_estimated_delivery_date"] = pd.to_datetime(
        exposure["order_estimated_delivery_date"], errors="coerce"
    )
    exposure["purchase_month"] = exposure["order_purchase_timestamp"].dt.month
    exposure["purchase_weekday"] = exposure["order_purchase_timestamp"].dt.dayofweek
    exposure["estimated_delivery_days"] = (
        exposure["order_estimated_delivery_date"] - exposure["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    output_columns = [
        "order_id",
        "order_item_id",
        "seller_id",
        "product_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
        "product_category_name",
        "product_category_name_english",
        "price",
        "freight_value",
        "freight_to_price_ratio",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
        "product_volume_cm3",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
        "route_state",
        "cross_state_flag",
        "purchase_month",
        "purchase_weekday",
        "estimated_delivery_days",
    ]

    return exposure[output_columns]


def make_summary(exposure: pd.DataFrame) -> dict:
    exposure_key = ["order_id", "order_item_id", "seller_id", "product_id"]
    missing_rates = exposure.isna().mean()
    return {
        "rows": int(len(exposure)),
        "columns": int(len(exposure.columns)),
        "unique_exposure_key": int(exposure.drop_duplicates(exposure_key).shape[0]),
        "unique_order_id": int(exposure["order_id"].nunique()),
        "unique_seller_id": int(exposure["seller_id"].nunique()),
        "unique_product_id": int(exposure["product_id"].nunique()),
        "orders_with_multiple_exposures": int((exposure.groupby("order_id").size() > 1).sum()),
        "orders_with_multiple_sellers": int(
            (exposure.groupby("order_id")["seller_id"].nunique() > 1).sum()
        ),
        "max_exposures_per_order": int(exposure.groupby("order_id").size().max()),
        "missing_rates": {
            column: float(rate)
            for column, rate in missing_rates[missing_rates > 0].sort_values(ascending=False).items()
        },
        "top_categories": exposure["product_category_name_english"]
        .value_counts()
        .head(10)
        .to_dict(),
        "top_routes": exposure["route_state"].value_counts().head(10).to_dict(),
        "freight_value": {
            "min": float(exposure["freight_value"].min()),
            "median": float(exposure["freight_value"].median()),
            "mean": float(exposure["freight_value"].mean()),
            "max": float(exposure["freight_value"].max()),
        },
        "freight_to_price_ratio": {
            "min": float(exposure["freight_to_price_ratio"].min()),
            "median": float(exposure["freight_to_price_ratio"].median()),
            "mean": float(exposure["freight_to_price_ratio"].mean()),
            "max": float(exposure["freight_to_price_ratio"].max()),
        },
    }


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    exposure = build_exposure_table()
    exposure_path = PROCESSED_DIR / "exposure_table.csv"
    summary_path = PROCESSED_DIR / "exposure_table_summary.json"

    exposure.to_csv(exposure_path, index=False)
    summary = make_summary(exposure)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {exposure_path}")
    print(f"Wrote {summary_path}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

