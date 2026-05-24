# 01 Project Roadmap

## Project Goal

构建一个面向 TikTok Shop 中小卖家的往返运费险动态定价项目。

项目重点不是单纯预测退货率，而是建立一个完整的保险定价闭环：

```text
数据口径 -> exposure table -> 合成理赔层 -> 纯保费 -> 商业保费
-> 赔付率监控 -> credibility -> stress testing -> pricing memo
```

## Execution Phases

### Phase 1: Exposure Table + Baseline Pricing

目标：

```text
生成 exposure 级建模表
模拟第一版 synthetic returns + insurance claims layer
计算 baseline pure premium 和 commercial premium
```

核心输出：

```text
data/processed/exposure_table.csv
data/processed/pricing_baseline.csv
```

### Phase 2: GLM Pricing

目标：

```text
建立 claim frequency model
建立 claim severity model
计算 exposure 级 expected loss
检查 A/E ratio 和 calibration
```

### Phase 3: Actuarial Enhancements

目标：

```text
seller credibility
loss ratio backtesting
stress testing
pricing memo
```

### Phase 4: Interview Presentation

目标：

```text
XGBoost challenger
Streamlit dashboard
interview deck
final README polish
```

## Current Priority

Phase 1、Phase 2 和 Phase 3 第一版已完成。

Phase 4 已开始，当前只完成 challenger model 和 GLM comparison。

暂时不要直接做 SHAP、Dashboard 或 PDF 报告，除非明确决定继续展示层。

当前进度：

```text
data understanding: done
field dictionary: done
data audit: done
exposure table build: done
exposure-level EDA: done
synthetic claims: done
baseline pricing: done
GLM pricing design: done
GLM pricing build: done
seller credibility design: done
seller credibility build: done
loss ratio backtesting design: done
loss ratio backtesting build: done
stress testing design: done
stress testing build: done
pricing memo: done
Phase 3 documentation review: done
XGBoost challenger: done with xgboost 3.2.0
GLM vs challenger comparison: done
XGBoost parameter sweep: done
model selection / governance note: done
XGBoost interpretability: done
interview deck outline: done
dashboard: not started
PPTX interview deck: not started
```

## Phase 4 Current Conclusion

当前已安装并使用：

```text
xgboost 3.2.0
```

验证结论：

```text
GLM test frequency AUC = 0.560
XGBoost challenger calibrated test frequency AUC = 0.561
GLM test loss ratio = 60.18%
XGBoost challenger calibrated test loss ratio = 60.87%
```

因此当前不应把 challenger 替换为最终定价模型。XGBoost 在 frequency ranking 上略高于 GLM，但 pricing calibration 仍较弱。

它的价值是：

```text
1. 证明项目做了 champion-challenger comparison。
2. 说明更复杂模型未必在定价校准上更好。
3. 为后续 SHAP / feature importance / model governance 提供基础。
```
