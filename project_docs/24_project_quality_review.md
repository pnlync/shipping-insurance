# 24 Project Quality Review

本文档记录一次项目级质量检查。

检查目标：

```text
1. 回顾当前项目逻辑是否连贯。
2. 检查代码和输出字段是否容易误解。
3. 检查文档入口、roadmap、guide 是否反映当前状态。
4. 修复明显不清楚或不一致的地方。
```

## 1. Review Scope

重点阅读和检查：

```text
Project designing and implementation/project_guide.md
README.md
project_docs/README.md
project_docs/01_project_roadmap.md
project_docs/07_daily_log_2026_05_21.md
project_docs/17_seller_credibility_design.md
project_docs/18_seller_credibility_build.md
project_docs/19_loss_ratio_backtesting_design.md
project_docs/20_loss_ratio_backtesting_build.md
project_docs/21_stress_testing_design.md
project_docs/22_stress_testing_build.md
project_docs/23_pricing_memo.md
src/build_stress_testing.py
main.py
```

也用搜索检查了旧状态词和容易混淆的字段表述。

## 2. Key Findings

### Finding 1: Root Project Entry Point Was Weak

原来的 `main.py` 仍是 PyCharm sample script。

问题：

```text
它不能说明项目如何运行。
也不能帮助复现 pipeline。
```

处理：

```text
将 main.py 改成轻量 pipeline entry point。
```

现在支持：

```text
python main.py --list
python main.py --run phase1
python main.py --run phase2
python main.py --run phase3
python main.py --run all
python main.py --run stress
```

### Finding 2: Root README Was Missing

项目之前只有：

```text
project_docs/README.md
```

但仓库根目录没有 README。

问题：

```text
从仓库入口看，不清楚当前项目状态、核心 exposure key、主要输出和运行方式。
```

处理：

```text
新增 README.md。
```

内容包括：

```text
current status
core pricing unit
main outputs
how to run pipeline
important limitations
```

### Finding 3: Stress Testing Segment Fields Could Be Misread

原 stress testing 输出中：

```text
base_actual_loss
stressed_actual_loss
```

在 segment stress 场景下实际表示组合层总损失。

问题：

```text
同一行里 eligible_exposures 是 segment exposure，
但 stressed_actual_loss 是 portfolio stressed loss。
这容易让读者误以为 stressed_actual_loss 只是 segment loss。
```

处理：

```text
修改 src/build_stress_testing.py，显式拆成：

portfolio_base_actual_loss
portfolio_stressed_actual_loss
segment_base_actual_loss
segment_stressed_actual_loss
```

stressed loss ratio 仍使用：

```text
portfolio_stressed_actual_loss / commercial_premium
```

原因：

```text
stress testing 的核心问题是局部或整体不利情景传导后，
整个组合的商业保费是否还能承受。
```

### Finding 4: Project Guide Needed Current Implementation Status

`project_guide.md` 是总体设计文件，但顶部主要是原始规划。

问题：

```text
读者从 project_guide.md 开始读时，
不容易知道当前已经完成到哪个阶段。
```

处理：

```text
在 project_guide.md 顶部补充当前实现状态：
Phase 1 completed
Phase 2 completed
Phase 3 completed for first-version actuarial workflow
Phase 4 not started
```

### Finding 5: Roadmap Needed Final Phase 3 Status

`01_project_roadmap.md` 之前还写着 Phase 3 review in progress。

处理：

```text
更新为：
Phase 3 documentation review: done
XGBoost challenger: not started
dashboard: not started
interview deck: not started
```

## 3. What Was Not Changed

没有大规模重写历史过程文档。

原因：

```text
07_daily_log_2026_05_21.md 和早期 Phase 1 / Phase 2 文档中的“下一步”
是当时的历史记录，不应全部改成当前状态。
```

没有改变核心项目口径：

```text
exposure level = order_id + order_item_id + seller_id + product_id
frequency target = covered_claim_flag
severity target = net_loss on covered claims only
pricing features = quote-time-known variables only
seller credibility shrink target = GLM base expected loss
```

没有进入 Phase 4：

```text
XGBoost
SHAP
dashboard
presentation
interview deck
```

## 4. Verification Performed

语法检查：

```text
python -m py_compile main.py \
  src/build_stress_testing.py \
  src/build_loss_ratio_backtesting.py \
  src/build_seller_credibility.py \
  src/build_glm_pricing.py \
  src/build_baseline_pricing.py \
  src/build_synthetic_claims.py \
  src/build_exposure_table.py \
  src/eda_exposure_table.py
```

Pipeline entry point：

```text
python main.py --list
python main.py --run phase3
```

Stress testing was rerun after field-name cleanup:

```text
python src/build_stress_testing.py
```

Key validation result:

```text
base_credibility_loss_ratio = 0.5937448096616371
base_loss_ratio_matches_backtesting = true
combined_20_20_multiplier = 1.44
```

## 5. Current Clean Project State

Current status at the time of this review:

```text
Phase 1: completed
Phase 2: completed
Phase 3: first-version actuarial workflow completed
Phase 4: not started
```

Recommended next choices:

```text
Option A:
Stay in Phase 3 and add pricing action rules / underwriting rules.

Option B:
Move to Phase 4 and build XGBoost challenger.

Option C:
Prepare interview materials based on project_docs/23_pricing_memo.md.
```

Residual limitations:

```text
1. Claims are synthetic, not real insurance claims.
2. No true out-of-time backtesting.
3. No explicit expense model beyond target loss ratio.
4. No claim development / IBNR.
5. No production-grade underwriting rules yet.
```

## 6. Phase 4 Update

After this review, Phase 4 started with the challenger model layer.

Current update:

```text
XGBoost challenger design: done
challenger build: done with xgboost 3.2.0 after installing Homebrew libomp
GLM vs challenger comparison: done
SHAP/dashboard/interview deck: not started
```

See:

```text
25_xgboost_challenger_design.md
26_xgboost_challenger_build.md
```
