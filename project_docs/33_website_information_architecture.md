# 33 Website Information Architecture

本文档定义项目展示网站的信息架构和首版范围。

目标是先把网页的职责边界设计清楚，暂不开始写前端代码。

## 1. Website Purpose

网站定位：

```text
multi-page actuarial pricing project website
for interview / portfolio review
```

它不是：

```text
dashboard
development log
notebook dump
model playground
```

它应该让读者快速理解：

```text
1. 项目解决什么保险定价问题
2. 为什么 exposure definition 是核心
3. synthetic claims layer 如何把电商数据转成保险定价数据
4. GLM + seller credibility 为什么是当前 champion pricing basis
5. XGBoost 为什么只是 challenger risk score
6. 项目的结果、限制和生产化下一步是什么
```

## 2. Target Reader

主要读者：

```text
interviewer
pricing manager
actuarial reviewer
data science reviewer
portfolio reviewer
```

读者可能不会完整阅读所有文档，所以每个页面都应该独立可读。

页面之间的关系应该是：

```text
Homepage:
quick entry and routing

Project Memo:
fast executive understanding

Project Docs:
technical confidence

Pricing Memo:
actuarial deliverable

Data and Result Display:
evidence and visual proof
```

## 3. Route Structure

首版网站建议只做 5 个主页面：

```text
/
/project-memo
/project-docs
/pricing-memo
/results
```

不要在第一版做很多深层子路由。原因：

```text
1. 项目展示的重点是清晰表达，不是文档系统复杂度
2. 5 个页面足够覆盖 portfolio review 场景
3. 后续如果 Project Docs 太长，再拆成子页面
```

## 4. Page Responsibilities

### 4.1 Homepage

页面职责：

```text
项目入口和导航。
```

不应该承担详细解释。

建议内容：

```text
Hero:
Return-Shipping Insurance Pricing Engine

One-line description:
Exposure-level actuarial pricing workflow for e-commerce return-shipping insurance.

Problem:
E-commerce sellers need a dynamic premium for return-shipping coverage,
but raw order data is not directly an insurance pricing dataset.

Core conclusion:
GLM + seller credibility is the current champion pricing basis.
XGBoost is retained as a challenger risk score, not the final pricing model.
```

首页推荐 KPI：

| Metric | Value |
|---|---:|
| Total rows | 112,650 |
| Eligible exposures | 110,197 |
| Covered claims | 8,485 |
| Target loss ratio | 60% |

导航入口：

```text
Project Memo
Project Docs
Pricing Memo
Data and Results
```

### 4.2 Project Memo / Executive Summary

页面职责：

```text
3-5 分钟读懂项目全貌。
```

建议 sections：

```text
1. Project objective
2. Business problem
3. Data limitation
4. Method overview
5. Core modelling approach
6. Key results
7. Final recommendation
8. Main limitation and production next steps
```

必须靠前说明：

```text
The recommended current pricing basis is GLM expected loss + seller credibility.
XGBoost is useful as a challenger score, but it does not replace GLM because calibration is weaker.
```

这页不应该太技术化。它的目标是让读者知道项目整体判断是成熟的。

### 4.3 Project Docs

页面职责：

```text
最终正式技术文档集合。
```

这页不是 implementation notes，也不是 daily logs。

建议同页分章节：

```text
1. Exposure Definition
2. Synthetic Claims Layer
3. Baseline Pricing
4. GLM Pricing
5. Seller Credibility
6. Loss Ratio Monitoring
7. Stress Testing
8. XGBoost Challenger
9. Interpretability
10. Model Governance
```

每个章节使用统一结构：

```text
Purpose
Method
Inputs
Outputs
Key decisions
Validation checks
Limitations
```

写作口径：

```text
正式说明项目最终方法，而不是记录过程。
```

避免：

```text
Phase 1 did...
I fixed...
Next I tried...
```

使用：

```text
The exposure unit is defined as...
The model excludes leakage fields...
The seller credibility adjustment uses...
```

### 4.4 Pricing Memo

页面职责：

```text
精算 / pricing committee 风格的正式交付物。
```

基础来源：

```text
project_docs/23_pricing_memo.md
```

建议网页结构：

```text
1. Pricing recommendation
2. Product and coverage scope
3. Exposure basis
4. Claim definition
5. Technical premium methodology
6. GLM pricing result
7. Seller credibility adjustment
8. Monitoring and stress testing
9. Model governance
10. Limitations
11. Production data requirements
```

必须保留的核心公式：

```text
pure premium = frequency x severity
commercial premium = pure premium / target loss ratio
target loss ratio = 60%
```

这页的语气应该比 Project Memo 更正式，也更接近 actuarial deliverable。

### 4.5 Data and Result Display

页面职责：

```text
展示关键证据和模型结果。
```

首版建议做静态结果页，不做复杂 dashboard。

推荐模块：

```text
1. Portfolio summary KPIs
2. Baseline / GLM / credibility premium summary
3. GLM vs XGBoost comparison table
4. Loss ratio by seller tier
5. Stress testing scenarios
6. XGBoost feature contribution summary
```

推荐 visual：

```text
KPI strip:
exposures, claims, claim frequency, total net loss, target loss ratio

Comparison table:
GLM vs XGBoost AUC, A/E, pure premium, loss ratio

Bar chart:
loss ratio by seller tier

Bar chart:
stress scenario loss ratios

Contribution bars:
XGBoost frequency top base features

Callout:
XGBoost severity dominated by freight_value_capped
```

第一版不建议做：

```text
complex filters
maps
drilldown tables
live model scoring
interactive parameter controls
```

原因：

```text
这个项目的核心价值是 pricing judgment 和 governance，
不是 BI 工具复杂度。
```

## 5. Source Documents

网页内容建议从以下文档整理：

| Website page | Primary sources |
|---|---|
| Homepage | `README.md`, `32_interview_deck_outline.md` |
| Project Memo | `32_interview_deck_outline.md`, `24_project_quality_review.md`, `29_model_selection_and_governance.md` |
| Project Docs | `03_exposure_definition.md`, `09_synthetic_claims_design.md`, `14_glm_pricing_design.md`, `17_seller_credibility_design.md`, `21_stress_testing_design.md`, `25_xgboost_challenger_design.md`, `30_xgboost_interpretability_design.md` |
| Pricing Memo | `23_pricing_memo.md` |
| Data and Results | `data/processed/*.json`, selected `data/processed/*.csv` |

Implementation logs should not be copied directly into the website.

## 6. Result Data Sources

Recommended result files:

```text
data/processed/synthetic_claims_summary.json
data/processed/pricing_baseline_summary.json
data/processed/glm_pricing_summary.json
data/processed/seller_credibility_summary.json
data/processed/backtest_by_seller_tier.csv
data/processed/stress_test_portfolio.csv
data/processed/model_comparison_glm_vs_xgboost.csv
data/processed/xgboost_frequency_base_feature_summary.csv
data/processed/xgboost_severity_base_feature_summary.csv
```

Key numbers to surface:

```text
total rows = 112,650
eligible exposures = 110,197
covered claims = 8,485
covered claim frequency = 7.70%
total net loss = 163,112.68
average severity = 19.22
target loss ratio = 60%

GLM test AUC = 0.5598
GLM pure premium A/E = 1.0030
GLM loss ratio = 60.18%

XGBoost test AUC = 0.5609
XGBoost pure premium A/E = 1.0145
XGBoost loss ratio = 60.87%
```

Important caveat:

```text
Claim outcomes are synthetic.
Numerical rates demonstrate the pricing workflow and are not production rates.
```

## 7. Visual Style Rules

The website should visually align with the interview deck:

```text
Work Sans
large whitespace
low saturation
soft gray backgrounds
restrained type weight
few borders
text-first layouts
simple geometric evidence objects
```

Avoid:

```text
overly decorative dashboards
heavy gradients
large marketing hero imagery
too many cards
chart clutter
animated gimmicks
```

Recommended layout style:

```text
quiet editorial / technical memo
with a small number of clean charts
```

## 8. First Implementation Scope

首版实现范围：

```text
1. Build multi-page static website.
2. Add top navigation across all pages.
3. Create homepage with project overview and links.
4. Write Project Memo page.
5. Convert Pricing Memo into webpage format.
6. Create Project Docs as one official documentation hub.
7. Create Results page with static charts/tables.
```

首版可以不做：

```text
search
authentication
database backend
interactive filters
PDF export
CMS editing
live Python model execution
```

## 9. Recommended Implementation Approach

Recommended stack:

```text
Vite React
Markdown/JSON-driven content
static CSV/JSON loading for results
simple chart components
```

Why:

```text
1. Fast to build and deploy
2. Easy to keep content close to project docs
3. Enough interactivity for charts without becoming a full dashboard
4. Suitable for portfolio presentation
```

Alternative:

```text
plain HTML/CSS
```

This is acceptable if the goal is maximum simplicity, but Vite React is preferable if the Results page uses reusable chart/table components.

## 10. Open Decisions Before Coding

Before writing website code, decide:

```text
1. Should the website live under a new folder such as web/ or site/?
2. Should content be copied into page components or loaded from Markdown files?
3. Should the Results page use chart library components or custom SVG/HTML charts?
4. Should the website include a link to the PPTX deck?
5. Should the final website be deployable to GitHub Pages, Netlify, or Vercel?
```

Recommended answers for first version:

```text
1. Use web/ or site/ to avoid mixing app code with actuarial scripts.
2. Use structured content files where practical.
3. Use simple custom chart components first.
4. Include a link to the final PPTX as supporting material.
5. Keep deployment target static-host friendly.
```

## 11. Success Criteria

The website is successful if a reviewer can answer these questions within 5 minutes:

```text
What insurance product is being priced?
What is the exposure unit?
What are the frequency and severity targets?
Why is GLM the champion model?
What role does seller credibility play?
What did XGBoost add, and why did it not replace GLM?
What are the main results?
What is the biggest limitation?
What would be needed for production?
```

If the website makes those answers obvious, it is doing its job.
