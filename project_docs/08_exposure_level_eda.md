# 08 Exposure-Level EDA

本文档记录 `data/processed/exposure_table.csv` 的第一版 exposure-level EDA。

脚本：

```text
src/eda_exposure_table.py
```

输出目录：

```text
data/processed/eda/
```

## 1. EDA Outputs

本次生成的主要输出：

```text
data/processed/eda/exposure_eda_summary.json
data/processed/eda/numeric_quantiles.csv
data/processed/eda/missing_summary.csv
data/processed/eda/order_status_summary.csv
data/processed/eda/category_freight_summary.csv
data/processed/eda/route_freight_summary.csv
data/processed/eda/cap_diagnostics.csv
data/processed/eda/anomaly_diagnostics.csv
data/processed/eda/top_freight_value_rows.csv
data/processed/eda/top_freight_to_price_ratio_rows.csv
data/processed/eda/top_product_weight_rows.csv
data/processed/eda/top_product_volume_rows.csv
```

## 2. Population Summary

| Metric | Value |
|---|---:|
| exposure rows | 112,650 |
| unique orders | 98,666 |
| delivered exposure rows | 110,197 |
| delivered share | 97.82% |
| non-delivered exposure rows | 2,453 |
| cross-state exposure share | 63.82% |

结论：

```text
第一版 claim simulation 建议只保留 delivered exposure。
```

原因：

```text
退货运费险的可观察风险应发生在订单完成交付之后。
shipped / canceled / invoiced / processing 等状态混入第一版理赔模拟，
会把未完全 earned 的 exposure 和完整 exposure 放在一起。
```

## 3. Numeric Distribution

| Field | Median | Mean | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|
| price | 74.99 | 120.65 | 349.90 | 890.00 | 6,735.00 |
| freight_value | 16.26 | 19.99 | 45.12 | 84.52 | 409.68 |
| freight_to_price_ratio | 0.231 | 0.321 | 0.875 | 1.549 | 26.235 |
| product_weight_g | 700 | 2,094 | 9,750 | 18,250 | 40,425 |
| product_volume_cm3 | 6,480 | 15,244 | 57,732 | 112,284 | 296,208 |
| estimated_delivery_days | 23.26 | 23.84 | 38.60 | 51.06 | 155.14 |

结论：

```text
freight_value、freight_to_price_ratio、重量和体积都有明显右尾。
第一版定价特征不应直接用原始连续值进入模型。
```

建议：

```text
freight_value: 保留原始值用于诊断；建模时考虑 log1p 或 P99 cap。
freight_to_price_ratio: 建模前 P99 cap 或分箱。
product_weight_g / product_volume_cm3: 建模前 log1p、分箱，或高分位 cap。
estimated_delivery_days: 暂时不作为第一版报价变量，后续可用于运营解释。
```

## 4. Category Findings

Top exposure categories:

| Category | Exposures | Share | Freight Median | Freight P95 | Ratio Median |
|---|---:|---:|---:|---:|---:|
| bed_bath_table | 11,115 | 9.87% | 16.19 | 34.68 | 0.219 |
| health_beauty | 9,670 | 8.58% | 15.79 | 38.21 | 0.210 |
| sports_leisure | 8,641 | 7.67% | 16.27 | 39.65 | 0.218 |
| furniture_decor | 8,334 | 7.40% | 16.39 | 47.80 | 0.270 |
| computers_accessories | 7,827 | 6.95% | 16.00 | 40.59 | 0.209 |
| housewares | 6,964 | 6.18% | 16.74 | 49.00 | 0.290 |
| watches_gifts | 5,991 | 5.32% | 15.82 | 34.47 | 0.115 |
| telephony | 4,545 | 4.03% | 15.10 | 27.88 | 0.432 |
| garden_tools | 4,347 | 3.86% | 17.67 | 50.99 | 0.295 |
| auto | 4,235 | 3.76% | 17.62 | 51.11 | 0.220 |

High freight categories with at least 500 exposures:

| Category | Exposures | Freight Median | Freight P95 | Weight Median | Volume Median |
|---|---:|---:|---:|---:|---:|
| office_furniture | 1,691 | 34.18 | 88.40 | 10,975 | 70,224 |
| furniture_living_room | 503 | 26.72 | 88.02 | 7,500 | 36,190 |
| musical_instruments | 680 | 18.23 | 82.36 | 800 | 8,649 |
| luggage_accessories | 1,092 | 18.43 | 75.47 | 1,250 | 26,400 |
| home_construction | 604 | 17.15 | 60.78 | 900 | 9,600 |

High freight-to-price ratio categories with at least 500 exposures:

| Category | Exposures | Price Median | Freight Median | Ratio Median | Ratio P95 |
|---|---:|---:|---:|---:|---:|
| electronics | 2,767 | 21.90 | 15.10 | 0.623 | 1.587 |
| telephony | 4,545 | 29.99 | 15.10 | 0.432 | 1.224 |
| home_appliances | 771 | 47.59 | 16.11 | 0.308 | 0.954 |
| garden_tools | 4,347 | 59.90 | 17.67 | 0.295 | 0.779 |
| housewares | 6,964 | 59.80 | 16.74 | 0.290 | 1.057 |

结论：

```text
品类既影响运费水平，也影响运费占商品价格的比例。
低价小件品类的 freight_to_price_ratio 可能高于大件品类。
第一版合成理赔层可以把 category 作为 frequency 或 severity factor。
```

## 5. Route Findings

Top routes:

| Route | Exposures | Share | Freight Median | Freight P95 | Ratio Median |
|---|---:|---:|---:|---:|---:|
| SP_to_SP | 36,192 | 32.13% | 11.85 | 25.69 | 0.188 |
| SP_to_RJ | 9,688 | 8.60% | 17.19 | 44.25 | 0.257 |
| SP_to_MG | 8,703 | 7.73% | 17.60 | 38.06 | 0.272 |
| SP_to_RS | 4,194 | 3.72% | 17.67 | 41.46 | 0.280 |
| SP_to_PR | 3,667 | 3.26% | 17.67 | 41.33 | 0.284 |
| PR_to_SP | 3,410 | 3.03% | 15.59 | 39.21 | 0.178 |
| MG_to_SP | 2,964 | 2.63% | 16.74 | 45.66 | 0.254 |
| SP_to_SC | 2,749 | 2.44% | 17.67 | 41.31 | 0.280 |
| SP_to_BA | 2,708 | 2.40% | 19.94 | 50.51 | 0.306 |
| MG_to_MG | 1,709 | 1.52% | 14.21 | 29.50 | 0.198 |

High freight routes with at least 500 exposures:

| Route | Exposures | Freight Median | Freight P95 | Ratio Median |
|---|---:|---:|---:|---:|
| SP_to_MA | 566 | 34.43 | 71.04 | 0.437 |
| SP_to_PA | 785 | 26.09 | 65.50 | 0.354 |
| RS_to_SP | 762 | 18.26 | 60.30 | 0.225 |
| SP_to_CE | 1,134 | 26.75 | 59.72 | 0.333 |
| SP_to_PE | 1,289 | 26.33 | 56.77 | 0.340 |

Same-state vs cross-state freight:

| Segment | Median | Mean | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|
| same-state | 11.99 | 13.46 | 26.68 | 51.18 | 174.45 |
| cross-state | 18.25 | 23.69 | 52.74 | 97.04 | 409.68 |

结论：

```text
route_state 和 cross_state_flag 是第一版 pricing factor 的强候选字段。
SP_to_SP exposure 极大且运费显著低于跨州路线。
```

## 6. Cap and Outlier Diagnostics

Cap diagnostics:

| Field | P99 Cap | Rows Above P99 | Share Above P99 | Max |
|---|---:|---:|---:|---:|
| freight_value | 84.52 | 1,124 | 1.00% | 409.68 |
| freight_to_price_ratio | 1.549 | 1,125 | 1.00% | 26.235 |
| product_weight_g | 18,250 | 1,117 | 0.99% | 40,425 |
| product_volume_cm3 | 112,284 | 1,127 | 1.00% | 296,208 |

Additional anomaly checks:

| Check | Rows | Share |
|---|---:|---:|
| freight_value = 0 | 383 | 0.34% |
| freight_to_price_ratio > 1 | 4,124 | 3.66% |
| freight_to_price_ratio > 2 | 531 | 0.47% |
| product_weight_g = 0 | 8 | 0.01% |
| product_weight_g > 30,000 | 3 | 0.00% |
| product_volume_cm3 > 200,000 | 237 | 0.21% |
| estimated_delivery_days > 60 | 316 | 0.28% |

Top `freight_to_price_ratio` rows show the main issue:

```text
The largest ratios are driven by very low price rows, e.g. price = 0.85 and freight_value = 22.30.
```

结论：

```text
freight_to_price_ratio 必须处理右尾。
P99 cap 是第一版最简单、可解释的选择。
```

## 7. Missing Value Handling

只有商品尺寸相关字段有缺失：

| Field | Missing Rows | Missing Rate |
|---|---:|---:|
| product_height_cm | 18 | 0.016% |
| product_length_cm | 18 | 0.016% |
| product_volume_cm3 | 18 | 0.016% |
| product_weight_g | 18 | 0.016% |
| product_width_cm | 18 | 0.016% |

建议：

```text
Phase 1 可直接删除这 18 行，或用 product_category_name_english 的中位数填充。
如果后续要保持行数完全一致，优先使用品类中位数填充，再 fallback 到全局中位数。
```

## 8. Decisions for Next Step

进入 synthetic claims 前，建议采用以下口径：

```text
1. 第一版 claim simulation population = order_status == delivered。
2. 保留 category、route_state、cross_state_flag 作为主要风险因子。
3. freight_value 使用原始值作为 paid_loss 基础，但定价特征使用 capped/log value。
4. freight_to_price_ratio 使用 P99 cap 或分箱，不直接用 raw ratio。
5. product_weight_g 和 product_volume_cm3 使用 log1p 或分箱，并处理 18 行缺失。
6. 暂不使用后验履约字段；estimated_delivery_days 只作为 EDA/解释字段。
```

下一步：

```text
构建第一版 synthetic returns + claims layer。
```
