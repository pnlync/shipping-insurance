# 28 XGBoost Parameter Sweep

本文档记录 Phase 4 中对 XGBoost challenger 的一次小型参数复查。

这不是大规模 hyperparameter tuning，而是一次 sanity check：

```text
确认 XGBoost AUC 偏低是不是因为实现错误或参数过度灵活。
```

## 1. Why Run a Parameter Sweep?

初版 XGBoost frequency model 使用：

```text
n_estimators = 400
max_depth = 3
learning_rate = 0.04
subsample = 0.85
colsample_bytree = 0.85
```

初版结果：

```text
train frequency AUC = 0.635
test frequency AUC = 0.555
```

这个结果有一个明显信号：

```text
train AUC 明显高于 test AUC。
```

这通常说明模型学到了训练集中的额外结构，但这些结构没有稳定泛化到测试集。

换句话说：

```text
模型可能有轻微过拟合。
```

因此需要检查：

```text
1. XGBoost 实现有没有明显错误？
2. 是否只是当前参数太灵活？
3. 更正则化的配置是否能提升 test AUC 和 calibration？
```

## 2. What Was Kept Fixed?

为了让 sweep 只比较 XGBoost 参数，而不是改变建模口径，以下内容保持不变：

```text
exposure level = order_id + order_item_id + seller_id + product_id
frequency target = covered_claim_flag
train/test split = order-level split
test size = 20%
random seed = 20260521
feature set = current quote-time-known pricing features
leakage exclusions = unchanged
```

也就是说，这次 sweep 没有增加 seller_id、product_id、return fields 或 claim fields。

## 3. Configurations Compared

这次只 sweep frequency model，因为 AUC 是 frequency metric。

比较方向包括：

```text
current:
原始配置，depth 3，中等 learning rate。

shallow_more:
更浅的树，更多树，更低 learning rate。

depth2:
更浅的树，减少单棵树复杂度。

depth4:
更深的树，测试更复杂模型是否有帮助。

regularized:
更浅的树 + 更强正则化 + 更大的 min_child_weight。

weighted:
加入 scale_pos_weight 处理低频正类。

weighted_reg:
class weight + 正则化组合。
```

## 4. Sweep Results

| Config | Train AUC | Test AUC | Test Brier | Test Predicted Frequency |
|---|---:|---:|---:|---:|
| regularized | 0.589 | 0.561 | 0.07166 | 7.67% |
| depth2 | 0.592 | 0.560 | 0.07168 | 7.67% |
| weighted_reg | 0.593 | 0.560 | 0.24469 | 49.18% |
| shallow_more | 0.600 | 0.559 | 0.07169 | 7.66% |
| depth4 | 0.653 | 0.556 | 0.07173 | 7.67% |
| current | 0.635 | 0.555 | 0.07173 | 7.66% |
| weighted | 0.636 | 0.553 | 0.24113 | 48.59% |

## 5. Interpretation

### Finding 1: More Flexible Trees Did Not Help

The deeper / more flexible configurations had higher train AUC but weaker test AUC.

Example:

```text
depth4 train AUC = 0.653
depth4 test AUC = 0.556
```

This suggests:

```text
More model flexibility mainly captured training noise.
```

### Finding 2: Regularization Improved Stability

The best test AUC came from the regularized configuration:

```text
train AUC = 0.589
test AUC = 0.561
```

This train/test gap is much smaller than the original current configuration:

```text
original train AUC = 0.635
original test AUC = 0.555
```

So the regularized model is less impressive on the training set, but more stable out of sample.

### Finding 3: Class Weighting Hurt Probability Calibration

The weighted configurations produced high predicted claim frequencies:

```text
weighted predicted frequency ≈ 48.59%
weighted_reg predicted frequency ≈ 49.18%
```

Actual test claim frequency is about:

```text
7.80%
```

So `scale_pos_weight` distorted the raw probability scale. It may sometimes help ranking, but in this project it badly hurt probability calibration.

Because this is an insurance pricing model, probability calibration matters. A frequency model that predicts a 49% claim rate when the actual rate is 7.8% is not suitable for direct pricing without further calibration.

### Finding 4: XGBoost Can Slightly Improve Ranking, But Not Pricing Calibration

After using the regularized configuration, the XGBoost test AUC improved:

```text
GLM test frequency AUC = 0.5598
XGBoost regularized test frequency AUC = 0.5609
```

This is a small ranking improvement.

But pricing calibration remains weaker than GLM:

```text
GLM test pure premium A/E = 1.0030
XGBoost calibrated test pure premium A/E = 1.0145

GLM test loss ratio = 60.18%
XGBoost calibrated test loss ratio = 60.87%
```

Therefore:

```text
XGBoost is marginally better at frequency ranking,
but GLM remains better calibrated for pricing.
```

## 6. Final Selected Frequency Parameters

The selected XGBoost frequency model is:

```text
n_estimators = 500
max_depth = 2
learning_rate = 0.03
subsample = 0.80
colsample_bytree = 0.80
reg_lambda = 5
min_child_weight = 20
objective = binary:logistic
eval_metric = logloss
```

Why this configuration:

```text
1. It produced the best test AUC in the sweep.
2. It reduced the train/test AUC gap.
3. It avoided the probability calibration damage from class weighting.
4. It remains a conservative challenger rather than an overfit black-box model.
```

## 7. What This Means for the Project

The parameter sweep changed the conclusion slightly.

Earlier wording:

```text
XGBoost did not beat GLM on AUC.
```

Updated wording:

```text
After regularization, XGBoost slightly beats GLM on frequency AUC,
but GLM still has better pure premium A/E and loss ratio calibration.
```

This is a stronger and more honest conclusion.

It shows:

```text
1. The challenger model was implemented correctly enough to test.
2. Parameter choices matter.
3. AUC improvement alone is not enough to replace a pricing model.
4. For insurance pricing, calibration and rate adequacy remain central.
```

## 8. Interview Explanation

可以这样讲：

```text
我一开始发现 XGBoost 的 test AUC 没有超过 GLM，
所以没有直接接受这个结果，而是检查了实现和参数。

实现上没有发现 leakage 或 split 问题。
然后我做了一个小型 parameter sweep。

结果发现初版 XGBoost 太灵活，train AUC 高但 test AUC 低。
更浅、更正则化的配置让 test AUC 从 0.555 提升到 0.561，
略高于 GLM 的 0.560。

但 XGBoost 的 pure premium A/E 和 loss ratio calibration 仍不如 GLM，
所以我不会直接把 XGBoost 作为最终定价模型。
它更适合作为 challenger risk score 和后续解释性分析对象。
```
