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

Phase 1 已完成。Phase 2 第一版 GLM Pricing 已完成。

暂时不要提前做 XGBoost、SHAP、Dashboard 或 PDF 报告。

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
seller credibility: next
```
