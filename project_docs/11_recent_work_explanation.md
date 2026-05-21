# 11 Recent Work Explanation

本文档用快速回顾的方式解释最近完成的两步：

```text
1. exposure-level EDA
2. synthetic returns + claims layer
```

目的是方便之后快速看懂：我们做了什么、为什么做、得到了什么结果、下一步能用这些结果做什么。

## 1. Exposure-Level EDA

目标是检查 `exposure_table.csv` 能不能支持后续理赔模拟。

输入：

```text
data/processed/exposure_table.csv
```

新增脚本：

```text
src/eda_exposure_table.py
```

输出目录：

```text
data/processed/eda/
```

主要发现：

```text
总 exposure: 112,650
delivered exposure: 110,197，占 97.82%
非 delivered exposure: 2,453
跨州 exposure: 63.82%
```

因此决定：

```text
第一版只对 delivered exposure 模拟理赔。
```

原因：

```text
退货运费险通常要在订单交付后才可能发生。
```

EDA 还发现几个数据问题：

```text
freight_value 右尾很长，P99 = 84.52，max = 409.68
freight_to_price_ratio 右尾很长，P99 = 1.549，max = 26.235
重量/体积缺失 18 行
product_weight_g = 0 有 8 行
freight_value = 0 有 383 行
```

这些问题不是简单删掉，而是告诉下一步 synthetic claims 怎么处理。

## 2. Synthetic Claims Layer

Olist 没有真实理赔数据，所以我们生成了一层 synthetic returns + claims labels。

这里不是简单生成：

```text
claim_flag
paid_loss
```

而是按保险口径拆成两层。

第一层是 returns layer：

```text
return_requested
return_approved
refund_without_return
partial_refund
return_reason
request_days_after_delivery
```

它回答：

```text
有没有发生退货/售后行为？
```

第二层是 claims layer：

```text
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

它回答：

```text
这次售后是否触发保险责任？
保险实际赔了多少钱？
```

这个拆分很重要：

```text
退货不等于保险赔付。
```

举例：

```text
买家申请退货，但没通过审核:
return_requested = 1
covered_claim_flag = 0

买家退款不退货:
return_approved = 1
refund_without_return = 1
covered_claim_flag = 0

合规退货且产生回仓运费:
covered_claim_flag = 1
paid_loss > 0
```

本次只做第一版保障责任：

```text
Coverage A: Return Shipping
买家合规退货产生的回仓运费
```

暂时没有做：

```text
Coverage B: Failed Delivery / Logistics Exception
Coverage C: Replacement / Reshipment Shipping
```

## 3. Actual Outputs

新增脚本：

```text
src/build_synthetic_claims.py
```

输入：

```text
data/processed/exposure_table.csv
```

输出：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/synthetic_claims_summary.json
```

生成后的主表仍然是 exposure 级。

每一行仍代表：

```text
order_id + order_item_id + seller_id + product_id
```

但现在多了 return 和 claim 字段。

## 4. How EDA Issues Were Handled

| EDA Issue | Treatment |
|---|---|
| 非 delivered exposure | `claim_eligible_flag = 0`，return 和 claim 全部置 0 |
| `freight_value` 右尾 | 生成 `freight_value_capped`，最大不超过 84.52 |
| `freight_to_price_ratio` 右尾 | 生成 `freight_to_price_ratio_capped`，最大不超过 1.549 |
| 重量/体积缺失 | 用品类中位数填充，品类不够时用全局中位数 |
| `product_weight_g = 0` | 当异常值处理，重新填充 |
| `freight_value = 0` | 不能成为 covered return shipping claim |

## 5. Final Results

Population:

```text
总 exposure: 112,650
eligible exposure: 110,197
ineligible exposure: 2,453
```

Returns:

```text
return_requested_count: 9,338
return requested rate among eligible: 8.47%
```

Claims:

```text
covered_claim_count: 8,485
covered claim frequency among eligible: 7.70%
```

Loss:

```text
total gross loss: 164,736.00
total recovery from carrier: 1,623.32
total paid loss: 163,112.68
total net loss: 163,112.68

average paid loss among claims: 19.22
pure premium per eligible exposure: 1.48
```

其中：

```text
pure premium per eligible exposure = 1.48
```

含义：

```text
在当前合成理赔假设下，每个 eligible exposure 平均需要收约 1.48 的纯风险保费，
才刚好覆盖预期赔款。
```

这个金额不含：

```text
费用
利润
风险边际
资本成本
```

## 6. Why This Matters

项目已经从：

```text
只有 exposure table
```

推进到：

```text
exposure table + synthetic returns + synthetic insurance claims
```

现在已经有了后续定价所需的目标变量：

```text
covered_claim_flag
```

用于 frequency model。

```text
paid_loss / net_loss
```

用于 severity model 和 pure premium。

## 7. Next Step

下一步 baseline pricing 可以基于这些字段计算：

```text
pure premium
commercial premium
loss ratio target
category / route simple relativities
```
