# 29 Model Selection and Governance

本文档总结 Phase 4 后的模型选择结论。

重点不是证明某个模型“分数最高”，而是说明：

```text
在保险定价场景下，为什么当前保留 GLM 作为 champion，
并把 XGBoost 作为 challenger / risk score。
```

## 1. Current Model Roles

当前项目模型分工：

```text
Baseline:
portfolio average benchmark

GLM:
champion pricing model

GLM + seller credibility:
actuarial adjusted pricing layer

XGBoost:
challenger risk score / model comparison layer
```

也就是说，XGBoost 不是失败模型，而是 challenger。

它的任务是测试：

```text
更灵活的 nonlinear model 是否能在风险排序或 segment detection 上超过 GLM。
```

## 2. Why GLM Remains the Champion

GLM 当前仍作为主定价模型，原因不是因为它 AUC 最高，而是因为它更符合第一版保险定价模型的要求。

主要原因：

```text
1. 可解释性强
2. 定价口径稳定
3. 便于说明 rate factors
4. aggregate expected loss calibration 更好
5. 更容易和 seller credibility、loss ratio monitoring、stress testing 串起来
```

当前 test comparison：

| Model | Frequency AUC | Pure Premium A/E | Loss Ratio |
|---|---:|---:|---:|
| GLM | 0.5598 | 1.0030 | 60.18% |
| XGBoost calibrated | 0.5609 | 1.0145 | 60.87% |

解释：

```text
XGBoost frequency ranking 略高。
但 GLM pure premium A/E 更接近 1，loss ratio 更接近 target 60%。
```

因此当前选择：

```text
GLM remains champion.
XGBoost remains challenger.
```

## 3. Why Not Choose Model by AUC Alone?

AUC 只衡量 frequency ranking：

```text
模型能不能把 covered claim exposure 排在 non-claim exposure 前面。
```

但保险定价最终要回答的是：

```text
每个 exposure 收多少保费？
组合实际赔付率是否接近目标？
不同 segment 是否存在系统性低估？
```

所以模型选择不能只看：

```text
frequency AUC
```

还要看：

```text
frequency calibration
severity calibration
pure premium A/E
loss ratio
segment-level monitoring
stress testing behavior
business interpretability
```

在当前结果中，XGBoost 的 AUC 略高，但 pricing calibration 没有超过 GLM。

## 4. How Pure Premium A/E Drives the Pricing Decision

Pure premium 是：

```text
predicted frequency * predicted severity
```

Pure Premium A/E 是：

```text
actual net loss / predicted expected loss
```

解释：

```text
A/E = 1.00  expected loss level 准确
A/E > 1.00  模型低估风险
A/E < 1.00  模型高估风险
```

当前 test set：

```text
GLM pure premium A/E = 1.0030
XGBoost calibrated pure premium A/E = 1.0145
```

因此：

```text
GLM aggregate expected loss level 更准。
```

因为商业保费是：

```text
commercial premium = expected loss / target_loss_ratio
```

所以 A/E 会直接传导到 loss ratio：

```text
loss ratio = A/E * target_loss_ratio
```

当前 target loss ratio = 60%：

```text
GLM loss ratio = 60.18%
XGBoost calibrated loss ratio = 60.87%
```

这就是为什么 GLM 仍更适合作为当前主定价模型。

## 5. Governance View of XGBoost

XGBoost 在当前项目中的合理定位：

```text
1. challenger model
2. nonlinear risk ranking benchmark
3. potential risk score
4. future feature-importance / SHAP analysis candidate
```

当前不直接用它定价，原因：

```text
1. AUC improvement is very small.
2. Pure premium A/E is weaker than GLM.
3. Loss ratio calibration is weaker than GLM.
4. XGBoost is less directly interpretable.
5. Production pricing needs stable and explainable rate behavior.
```

这不是说 XGBoost 没价值。

它的价值是：

```text
1. 证明项目做了 champion-challenger testing。
2. 说明模型选择不是按算法流行度决定。
3. 发现 nonlinear model 是否能提供额外排序能力。
4. 为后续 SHAP、segment flagging、underwriting rules 提供基础。
```

## 6. When Would We Switch to XGBoost?

未来如果满足以下条件，可以考虑让 XGBoost 进入更核心的定价流程：

```text
1. Out-of-time validation 中 AUC 明显高于 GLM。
2. Pure premium A/E 接近或优于 GLM。
3. Loss ratio calibration 不弱于 GLM。
4. Decile-level calibration 稳定。
5. Segment-level underpricing 明显减少。
6. SHAP / feature importance 显示主要风险信号合理。
7. 模型输出可以被转化成可解释的 rating factor 或 risk tier。
8. 生产数据中 feature availability 稳定。
```

如果 XGBoost 只是：

```text
AUC 略高，但 loss ratio calibration 更差
```

那么它不应直接替代 GLM。

更合理的用法是：

```text
GLM 继续负责 base pricing。
XGBoost 用于 risk flag、manual review、underwriting action 或辅助分层。
```

## 7. Real Production Governance Requirements

当前项目基于 synthetic claims，因此还不能声称模型已经 production-ready。

真实生产上线前，还需要：

```text
1. 使用真实 return / claim data。
2. 做 historical train + future validation。
3. 做 claim development / IBNR adjustment。
4. 检查 feature availability at quote time。
5. 检查数据漂移和模型稳定性。
6. 检查 segment-level loss ratio。
7. 检查 pricing fairness / compliance。
8. 明确 expense、commission、capital、risk margin assumptions。
9. 建立定期 monitoring 和 recalibration process。
```

当前项目展示的是：

```text
transferable pricing framework
```

而不是：

```text
production TikTok Shop insurance rate filing
```

## 8. Recommended Final Story

面试时可以这样讲：

```text
我没有把项目做成单纯的 return prediction。
我先建立 exposure-level expected loss pricing framework，
然后用 GLM 做可解释的 champion pricing model。

在 Phase 4，我加入 XGBoost 作为 challenger。
XGBoost 经过正则化后 frequency AUC 略高于 GLM，
说明 nonlinear model 有一点额外排序能力。

但保险定价不能只看 AUC。
GLM 的 pure premium A/E 和 loss ratio calibration 更好，
所以当前我保留 GLM 作为主定价模型，
把 XGBoost 作为 challenger risk score 和后续 SHAP / governance 分析对象。
```

更短版本：

```text
XGBoost helps ranking slightly.
GLM prices better.
Therefore GLM remains champion, XGBoost remains challenger.
```
