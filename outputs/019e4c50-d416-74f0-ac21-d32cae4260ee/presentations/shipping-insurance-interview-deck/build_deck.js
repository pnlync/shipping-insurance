const fs = require("fs");
const path = require("path");
const {
  Presentation,
  PresentationFile,
  layers,
  shape,
  text,
} = require("@oai/artifact-tool");

const ROOT = "/Users/peterlynch/Documents/actuarial-projects/shipping-insurance";
const WORKSPACE = path.join(
  ROOT,
  "outputs/019e4c50-d416-74f0-ac21-d32cae4260ee/presentations/shipping-insurance-interview-deck",
);
const PREVIEW_DIR = path.join(WORKSPACE, "preview");
const QA_DIR = path.join(WORKSPACE, "qa");
const OUTPUT_DIR = path.join(WORKSPACE, "output");
const FINAL_PPTX = path.join(OUTPUT_DIR, "return-shipping-insurance-pricing-engine-revised.pptx");

const W = 1280;
const H = 720;

const C = {
  bg: "#F8F7F2",
  panel: "#EFEEE7",
  panel2: "#F3F2ED",
  text: "#171716",
  muted: "#6F6E67",
  quiet: "#9C9990",
  hair: "#D9D6CC",
  accent: "#66766A",
  accent2: "#77828B",
  amber: "#9A8364",
  pressure: "#9A6A62",
  white: "#FFFFFF",
};

const font = "Work Sans";

function pct(x, decimals = 1) {
  return `${(x * 100).toFixed(decimals)}%`;
}

function n(x, decimals = 0) {
  return Number(x).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function t(value, left, top, width, height, style = {}) {
  return text(value, {
    position: { left, top },
    width,
    height,
    style: {
      typeface: font,
      color: C.text,
      fontSize: 24,
      ...style,
    },
  });
}

function r(left, top, width, height, fill = C.panel, line = undefined, borderRadius = 0) {
  const cfg = {
    position: { left, top },
    width,
    height,
    fill,
  };
  if (line) cfg.line = line;
  if (borderRadius) cfg.borderRadius = borderRadius;
  return shape(cfg);
}

function hair(left, top, width, height = 1, fill = C.hair) {
  return r(left, top, width, height, fill);
}

function base(slide, slideNo, section, children, source = "Source: project processed outputs; synthetic claim layer for demonstration.") {
  slide.compose(
    layers({ width: W, height: H }, [
      r(0, 0, W, H, C.bg),
      t(section, 72, 38, 760, 18, { fontSize: 11, color: C.quiet }),
      t(String(slideNo).padStart(2, "0"), 1155, 36, 56, 20, {
        fontSize: 12,
        color: C.quiet,
        alignment: "right",
      }),
      hair(72, 658, 1040, 1, C.hair),
      t(source, 72, 673, 920, 18, { fontSize: 10, color: C.quiet }),
      ...children,
    ]),
  );
}

function titleSlide(p) {
  const slide = p.slides.add();
  slide.compose(
    layers({ width: W, height: H }, [
      r(0, 0, W, H, C.bg),
      t("Return-Shipping Insurance\nPricing Engine", 72, 96, 810, 152, {
        fontSize: 46,
        color: C.text,
      }),
      t(
        "Exposure-level actuarial pricing workflow with GLM, seller credibility, monitoring, stress testing, and XGBoost challenger.",
        75,
        274,
        690,
        78,
        { fontSize: 20, color: C.muted },
      ),
      hair(75, 396, 760, 1, C.hair),
      ...workflow(82, 452, [
        "Exposure",
        "Claims",
        "GLM",
        "Credibility",
        "Monitoring",
        "Stress",
        "XGBoost",
      ]),
      t("Tom Zhang", 75, 630, 260, 28, {
        fontSize: 16,
        color: C.text,
      }),
      t("May 2026", 1060, 632, 150, 24, {
        fontSize: 14,
        color: C.quiet,
        alignment: "right",
      }),
    ]),
  );
  slide.speakerNotes.setText(
    "Position the project as an actuarial pricing workflow, not a generic machine learning exercise. The core question is expected insurance loss per exposure.",
  );
  return slide;
}

function workflow(left, top, labels) {
  const gap = 16;
  const boxW = 132;
  const boxH = 42;
  const out = [];
  labels.forEach((label, i) => {
    const x = left + i * (boxW + gap);
    out.push(r(x, top, boxW, boxH, i === 6 ? "#E4E9E3" : C.panel, { color: C.hair, width: 1 }, 6));
    out.push(t(label, x + 10, top + 12, boxW - 20, 18, {
      fontSize: 13,
      color: i === 6 ? C.accent : C.text,
      alignment: "center",
    }));
    if (i < labels.length - 1) out.push(hair(x + boxW + 2, top + 21, gap - 4, 1, C.quiet));
  });
  return out;
}

function metric(label, value, x, y, w = 180) {
  return [
    t(label, x, y, w, 18, { fontSize: 11, color: C.quiet }),
    t(value, x, y + 20, w, 34, { fontSize: 28, color: C.text }),
  ];
}

function bulletLines(lines, x, y, w, size = 18, color = C.text) {
  const out = [];
  lines.forEach((line, i) => {
    out.push(r(x, y + i * (size + 15) + 8, 4, 4, color, undefined, 2));
    out.push(t(line, x + 18, y + i * (size + 15), w - 18, size + 10, {
      fontSize: size,
      color,
    }));
  });
  return out;
}

function slide2(p) {
  const slide = p.slides.add();
  base(slide, 2, "Product Boundary", [
    t("The product prices return-shipping loss,\nnot generic refund behavior.", 72, 96, 720, 104, {
      fontSize: 34,
    }),
    t("Coverage A", 77, 236, 190, 24, { fontSize: 13, color: C.accent }),
    t("Return Shipping", 77, 266, 330, 38, { fontSize: 28 }),
    t("Covered loss = compliant buyer return shipping cost.", 77, 316, 470, 56, {
      fontSize: 18,
      color: C.muted,
    }),
    r(632, 222, 1, 310, C.hair),
    t("Explicitly not covered", 688, 236, 330, 24, { fontSize: 13, color: C.quiet }),
    ...bulletLines(
      [
        "Product refund itself",
        "Fraud or refund without return",
        "Failed delivery / replacement shipping",
        "Non-delivered exposure",
      ],
      688,
      270,
      450,
      18,
      C.text,
    ),
    t(
      "A return event is not automatically an insurance claim. The claim layer only pays covered return-shipping cost.",
      77,
      560,
      800,
      58,
      { fontSize: 18, color: C.muted },
    ),
  ]);
  slide.speakerNotes.setText(
    "Explain that the first version keeps the product scope clean: return shipping only, not product refund or other logistics events.",
  );
  return slide;
}

function slide3(p) {
  const slide = p.slides.add();
  base(slide, 3, "Exposure Definition", [
    t("Correct exposure definition is the foundation of pricing.", 72, 92, 820, 52, {
      fontSize: 33,
    }),
    r(76, 182, 760, 76, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("order_id + order_item_id + seller_id + product_id", 104, 207, 710, 30, {
      fontSize: 25,
      color: C.text,
    }),
    ...hierarchy(130, 322),
    ...metric("Total rows", "112,650", 904, 184),
    ...metric("Eligible exposures", "110,197", 904, 268),
    ...metric("Ineligible exposures", "2,453", 904, 352),
    t(
      "Why not order_id alone? One order can contain multiple products and sellers, while freight_value is recorded at item level.",
      74,
      548,
      840,
      56,
      { fontSize: 18, color: C.muted },
    ),
  ]);
  slide.speakerNotes.setText(
    "This is the most important actuarial decision in the project. Pricing at order level would misattribute freight cost and seller risk.",
  );
  return slide;
}

function hierarchy(left, top) {
  const labels = ["Portfolio", "Seller", "Order", "Order-item exposure"];
  const widths = [150, 130, 130, 230];
  const out = [];
  let x = left;
  labels.forEach((label, i) => {
    out.push(r(x, top + i * 38, widths[i], 36, i === 3 ? "#E4E9E3" : C.panel2, { color: C.hair, width: 1 }, 5));
    out.push(t(label, x + 14, top + i * 38 + 9, widths[i] - 28, 18, {
      fontSize: 14,
      color: i === 3 ? C.accent : C.text,
    }));
    if (i < labels.length - 1) out.push(hair(x + widths[i] + 10, top + i * 38 + 18, 80, 1, C.hair));
    x += widths[i] + 90;
  });
  return out;
}

function slide4(p) {
  const slide = p.slides.add();
  base(slide, 4, "Synthetic Claims Layer", [
    t("Olist has real commerce logistics data,\nbut no insurance claim history.", 72, 90, 760, 96, {
      fontSize: 32,
    }),
    r(80, 232, 430, 102, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Returns layer", 106, 252, 180, 24, { fontSize: 15, color: C.accent }),
    t("return_requested, return_approved,\nrefund_without_return, return_reason", 106, 283, 360, 40, {
      fontSize: 17,
      color: C.muted,
    }),
    r(80, 366, 430, 118, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Claims layer", 106, 386, 180, 24, { fontSize: 15, color: C.accent }),
    t("covered_claim_flag, claim_type,\ngross_loss, paid_loss, net_loss", 106, 417, 360, 46, {
      fontSize: 17,
      color: C.muted,
    }),
    ...metric("Eligible exposures", "110,197", 622, 224),
    ...metric("Covered claims", "8,485", 622, 310),
    ...metric("Frequency", "7.70%", 622, 396),
    ...metric("Avg severity", "19.22", 872, 310),
    ...metric("Total net loss", "163,112.68", 872, 396, 230),
    t(
      "Frequency target = covered_claim_flag. Severity target = net_loss on covered claims only.",
      80,
      558,
      900,
      44,
      { fontSize: 18, color: C.muted },
    ),
  ], "Source: data/processed/synthetic_claims_summary.json; claim data is synthetic.");
  slide.speakerNotes.setText(
    "The project creates an insurance-style claim layer, not only a return flag. This is why frequency and severity targets are explicitly separated.",
  );
  return slide;
}

function slide5(p) {
  const slide = p.slides.add();
  base(slide, 5, "Baseline Pricing", [
    t("Start with a simple actuarial benchmark before modelling.", 72, 92, 840, 50, {
      fontSize: 32,
    }),
    t("Portfolio pure premium", 90, 216, 310, 24, { fontSize: 15, color: C.quiet }),
    t("total net loss / eligible exposures", 90, 248, 440, 30, { fontSize: 25 }),
    hair(90, 300, 500, 1, C.hair),
    t("Commercial premium", 90, 336, 310, 24, { fontSize: 15, color: C.quiet }),
    t("pure premium / target loss ratio", 90, 368, 440, 30, { fontSize: 25 }),
    r(720, 188, 330, 298, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    ...metric("Target loss ratio", "60.00%", 752, 224, 230),
    ...metric("Portfolio pure premium", "1.4802", 752, 314, 230),
    ...metric("Commercial premium", "2.4670", 752, 404, 230),
    t(
      "Baseline is the control model: everyone gets the same price, so it cannot differentiate category, route, freight, or seller risk.",
      90,
      566,
      920,
      46,
      { fontSize: 18, color: C.muted },
    ),
  ], "Source: data/processed/pricing_baseline_summary.json; target loss ratio = 60%.");
  slide.speakerNotes.setText(
    "Use the baseline as a benchmark. It proves the rate level but does not segment risk.",
  );
  return slide;
}

function slide6(p) {
  const slide = p.slides.add();
  base(slide, 6, "Champion Pricing Model", [
    t("GLM is the current champion because it is explainable and calibrated.", 72, 90, 940, 52, {
      fontSize: 31,
    }),
    r(76, 190, 420, 106, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Frequency", 104, 211, 170, 24, { fontSize: 14, color: C.accent }),
    t("Binomial GLM\ncovered_claim_flag", 104, 245, 330, 54, { fontSize: 18 }),
    r(76, 324, 420, 108, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Severity", 104, 345, 170, 24, { fontSize: 14, color: C.accent }),
    t("Gamma GLM\nnet_loss on covered claims", 104, 379, 350, 54, { fontSize: 18 }),
    r(76, 460, 420, 82, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Expected loss = frequency x severity", 104, 486, 350, 34, { fontSize: 18, color: C.accent }),
    ...miniTable(
      610,
      196,
      [
        ["Metric", "Test result"],
        ["Frequency AUC", "0.560"],
        ["Pure premium A/E", "1.003"],
        ["Predicted pure premium", "1.503"],
        ["Actual pure premium", "1.508"],
      ],
      [270, 190],
    ),
    t(
      "Feature rule: quote-time-known only. Outcome, post-bind, and synthetic generation fields are excluded.",
      76,
      574,
      920,
      54,
      { fontSize: 17, color: C.muted },
    ),
  ], "Source: data/processed/glm_pricing_summary.json.");
  slide.speakerNotes.setText(
    "AUC is only the frequency ranking metric. For pricing, pure premium A/E and loss ratio calibration matter more.",
  );
  return slide;
}

function miniTable(left, top, rows, colWidths) {
  const rowH = 48;
  const width = colWidths.reduce((a, b) => a + b, 0);
  const out = [r(left, top, width, rowH * rows.length, "#F1F0EA", { color: C.hair, width: 1 }, 6)];
  rows.forEach((row, i) => {
    if (i > 0) out.push(hair(left, top + i * rowH, width, 1, C.hair));
    let x = left;
    row.forEach((cell, j) => {
      const isFirst = j === 0;
      const isHeader = i === 0;
      const padLeft = isFirst ? 20 : 8;
      const padRight = isFirst ? 14 : 18;
      out.push(t(cell, x + padLeft, top + i * rowH + 14, colWidths[j] - padLeft - padRight, 24, {
        fontSize: isHeader ? 12 : 16,
        color: isHeader ? C.quiet : C.text,
        alignment: isFirst ? "left" : "right",
      }));
      x += colWidths[j];
    });
  });
  return out;
}

function slide7(p) {
  const slide = p.slides.add();
  base(slide, 7, "Seller Credibility", [
    t("Seller experience matters, but direct seller_id modelling is unstable.", 72, 92, 930, 52, {
      fontSize: 31,
    }),
    r(76, 182, 514, 210, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Credibility formula", 106, 207, 230, 24, { fontSize: 14, color: C.accent }),
    t("Z = n / (n + 500)", 106, 248, 360, 34, { fontSize: 23 }),
    t("seller relativity = Z x observed A/E + (1 - Z) x 1.0", 106, 304, 420, 34, {
      fontSize: 15,
      color: C.muted,
    }),
    t("Shrink target = seller's GLM base expected loss,\nnot portfolio average price.", 106, 350, 410, 38, {
      fontSize: 11,
      color: C.quiet,
    }),
    ...metric("Sellers", "2,970", 700, 184),
    ...metric("Median exposures", "8", 700, 268),
    ...metric("Sellers >= 500 exposures", "29", 700, 352, 240),
    r(80, 450, 900, 74, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Portfolio normalization preserves total GLM expected loss after seller relativities.", 106, 473, 790, 38, {
      fontSize: 17,
      color: C.accent,
    }),
    t(
      "This lets large sellers carry more of their own experience while small sellers remain close to their GLM risk mix.",
      80,
      560,
      900,
      58,
      { fontSize: 17, color: C.muted },
    ),
  ], "Source: data/processed/seller_credibility_summary.json.");
  slide.speakerNotes.setText(
    "Do not let a model memorize seller_id. Credibility is a controlled actuarial way to use seller experience.",
  );
  return slide;
}

function slide8(p) {
  const slide = p.slides.add();
  base(slide, 8, "Loss Ratio Monitoring", [
    t("Portfolio A/E close to 1 is not enough; monitor by segment.", 72, 92, 920, 52, {
      fontSize: 31,
    }),
    ...barChart(126, 210, 780, [
      { label: "Near GLM", value: 0.5831, color: C.accent },
      { label: "Elevated", value: 0.8153, color: C.pressure },
      { label: "Lower than GLM", value: 0.4373, color: C.accent2 },
    ], 0.9),
    t("Target loss ratio", 930, 208, 190, 18, { fontSize: 12, color: C.quiet }),
    t("60.00%", 930, 232, 190, 36, { fontSize: 31 }),
    hair(930, 292, 156, 1, C.hair),
    t("Elevated sellers remain above target after credibility and form a practical underwriting watchlist.", 930, 320, 218, 114, {
      fontSize: 18,
      color: C.muted,
    }),
    t("Portfolio GLM + credibility loss ratio = 59.37%", 126, 560, 580, 28, {
      fontSize: 20,
      color: C.text,
    }),
  ], "Source: data/processed/backtest_by_seller_tier.csv.");
  slide.speakerNotes.setText(
    "Use this slide to show monitoring discipline. The portfolio is near target but the elevated seller tier is still above target.",
  );
  return slide;
}

function barChart(left, top, width, data, maxValue) {
  const out = [];
  const labelW = 160;
  const chartW = width - labelW - 90;
  const rowH = 78;
  out.push(hair(left + labelW, top - 22, chartW, 1, C.hair));
  data.forEach((d, i) => {
    const y = top + i * rowH;
    const barW = Math.max(4, chartW * (d.value / maxValue));
    out.push(t(d.label, left, y + 8, labelW - 20, 24, { fontSize: 18, color: C.text }));
    out.push(r(left + labelW, y + 8, chartW, 26, "#ECEBE4", undefined, 4));
    out.push(r(left + labelW, y + 8, barW, 26, d.color, undefined, 4));
    out.push(t(pct(d.value, 1), left + labelW + chartW + 18, y + 7, 90, 24, {
      fontSize: 18,
      color: C.text,
    }));
  });
  return out;
}

function slide9(p) {
  const slide = p.slides.add();
  base(slide, 9, "Stress Testing", [
    t("A calibrated model can still be fragile under adverse scenarios.", 72, 92, 930, 52, {
      fontSize: 31,
    }),
    ...stressBars(126, 202, 800, [
      { label: "Base", value: 0.5937, color: C.accent },
      { label: "Frequency +20%", value: 0.7125, color: C.amber },
      { label: "Severity +20%", value: 0.7125, color: C.amber },
      { label: "Freq +10% / Sev +10%", value: 0.7184, color: C.amber },
      { label: "Freq +20% / Sev +20%", value: 0.8550, color: C.pressure },
    ]),
    t("Base conditions are close to target, but simultaneous frequency and severity deterioration creates high pressure.", 126, 568, 820, 40, {
      fontSize: 18,
      color: C.muted,
    }),
  ], "Source: data/processed/stress_test_portfolio.csv; GLM + credibility premium basis.");
  slide.speakerNotes.setText(
    "Stress testing is a governance layer. The base loss ratio is acceptable, but combined adverse scenarios create large pressure.",
  );
  return slide;
}

function stressBars(left, top, width, data) {
  const out = [];
  const chartW = 640;
  const maxValue = 0.9;
  data.forEach((d, i) => {
    const y = top + i * 60;
    out.push(t(d.label, left, y + 8, 230, 20, { fontSize: 16, color: C.text }));
    out.push(r(left + 250, y + 8, chartW, 22, "#ECEBE4", undefined, 4));
    out.push(r(left + 250, y + 8, chartW * (d.value / maxValue), 22, d.color, undefined, 4));
    out.push(t(pct(d.value, 1), left + 250 + chartW + 20, y + 6, 90, 22, {
      fontSize: 16,
      color: C.text,
    }));
  });
  return out;
}

function slide10(p) {
  const slide = p.slides.add();
  base(slide, 10, "XGBoost Challenger", [
    t("XGBoost is tested as challenger, not assumed to be the final rate basis.", 72, 90, 990, 58, {
      fontSize: 31,
    }),
    r(76, 176, 458, 114, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Parameter sweep insight", 106, 200, 260, 20, { fontSize: 14, color: C.accent }),
    t("First run: train AUC 0.635, test AUC 0.555\nRegularized: train AUC 0.589, test AUC 0.561", 106, 234, 374, 42, {
      fontSize: 17,
      color: C.muted,
    }),
    ...miniTable(
      610,
      182,
      [
        ["Test metric", "GLM", "XGBoost"],
        ["Frequency AUC", "0.5598", "0.5609"],
        ["Pure premium A/E", "1.0030", "1.0145"],
        ["Predicted pure premium", "1.503", "1.486"],
        ["Loss ratio", "60.18%", "60.87%"],
      ],
      [220, 120, 140],
    ),
    r(82, 440, 930, 102, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Conclusion", 112, 464, 130, 22, { fontSize: 13, color: C.accent }),
    t("Slightly better frequency ranking, but weaker pure premium A/E\nand loss-ratio calibration.", 112, 494, 790, 48, {
      fontSize: 17,
      color: C.text,
    }),
    t(
      "Therefore XGBoost remains a challenger risk score and monitoring benchmark, not the champion pricing formula.",
      82,
      580,
      900,
      50,
      { fontSize: 17, color: C.muted },
    ),
  ], "Source: data/processed/model_comparison_glm_vs_xgboost.csv.");
  slide.speakerNotes.setText(
    "AUC improved only marginally. GLM remains better for rate-level calibration, so the model governance answer is not to replace GLM yet.",
  );
  return slide;
}

function slide11(p) {
  const slide = p.slides.add();
  base(slide, 11, "XGBoost Interpretability", [
    t("The challenger uses plausible signals, but interpretation does not override calibration.", 72, 90, 980, 58, {
      fontSize: 31,
    }),
    t("Frequency: top base features by native SHAP-style mean absolute contribution", 84, 176, 740, 24, {
      fontSize: 15,
      color: C.quiet,
    }),
    ...contribBars(84, 222, 560, [
      ["category_group", 0.2574],
      ["cross_state_flag", 0.1682],
      ["purchase_month", 0.1010],
      ["freight_to_price_ratio", 0.1006],
      ["product_weight", 0.0798],
      ["route_group", 0.0768],
    ], 0.28),
    r(754, 240, 360, 148, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Severity", 784, 266, 140, 24, { fontSize: 13, color: C.accent }),
    t("freight_value_capped", 784, 306, 260, 34, { fontSize: 20 }),
    t("80.69% contribution share", 784, 354, 270, 28, { fontSize: 15, color: C.muted }),
    t(
      "Method note: these are XGBoost native contribution summaries using pred_contribs=True, not external shap package visualizations.",
      754,
      442,
      390,
      112,
      { fontSize: 15, color: C.muted },
    ),
  ], "Source: data/processed/xgboost_*_base_feature_summary.csv.");
  slide.speakerNotes.setText(
    "Frequency signals are category, route, seasonality, freight ratio, and weight. Severity is mostly freight value, which matches return-shipping coverage.",
  );
  return slide;
}

function contribBars(left, top, width, rows, maxValue) {
  const out = [];
  rows.forEach(([label, value], i) => {
    const y = top + i * 47;
    out.push(t(label, left, y, 190, 20, { fontSize: 14, color: C.text }));
    out.push(r(left + 220, y + 3, width - 300, 16, "#ECEBE4", undefined, 3));
    out.push(r(left + 220, y + 3, (width - 300) * (value / maxValue), 16, C.accent, undefined, 3));
    out.push(t(pct(value, 2), left + width - 68, y - 1, 70, 20, {
      fontSize: 14,
      color: C.text,
      alignment: "right",
    }));
  });
  return out;
}

function slide12(p) {
  const slide = p.slides.add();
  base(slide, 12, "Recommendation", [
    t("Keep GLM + seller credibility as champion pricing.", 72, 88, 900, 52, {
      fontSize: 34,
    }),
    t("Use XGBoost as challenger risk score and monitoring layer.", 75, 148, 760, 30, {
      fontSize: 22,
      color: C.muted,
    }),
    r(80, 230, 440, 122, "#E8ECE6", { color: C.hair, width: 1 }, 6),
    t("Why", 108, 254, 90, 22, { fontSize: 14, color: C.accent }),
    t("GLM is explainable and better calibrated.\nCredibility handles seller experience in a controlled actuarial way.", 108, 288, 360, 42, {
      fontSize: 17,
      color: C.text,
    }),
    r(620, 230, 440, 122, "#ECEBE4", { color: C.hair, width: 1 }, 6),
    t("Do not overclaim", 648, 254, 170, 22, { fontSize: 14, color: C.accent }),
    t("XGBoost adds a nonlinear benchmark but does not yet justify production replacement.", 648, 288, 360, 44, {
      fontSize: 17,
      color: C.text,
    }),
    t("Production roadmap", 84, 424, 280, 26, { fontSize: 21, color: C.text }),
    ...roadmap(84, 468, [
      "Real order / return / claim data",
      "Historical train + future validation",
      "Claim development / IBNR",
      "Expense, commission, capital loads",
      "Underwriting rules for elevated sellers",
      "Drift, A/E, LR, stress monitoring",
    ]),
    t(
      "The value is not one model score. The value is a pricing workflow connecting exposure definition, expected loss, credibility, monitoring, stress testing, and governance.",
      76,
      594,
      980,
      48,
      { fontSize: 16, color: C.muted },
    ),
  ], "Source: project_docs/29_model_selection_and_governance.md and Phase 4 outputs.");
  slide.speakerNotes.setText(
    "Close with the recommendation: champion GLM plus credibility, challenger XGBoost retained for risk scoring and governance.",
  );
  return slide;
}

function roadmap(left, top, items) {
  const out = [];
  const w = 168;
  items.forEach((item, i) => {
    const x = left + i * 174;
    out.push(r(x, top, w, 54, i === 0 ? "#E8ECE6" : "#ECEBE4", { color: C.hair, width: 1 }, 6));
    out.push(t(item, x + 12, top + 10, w - 24, 34, {
      fontSize: 12,
      color: i === 0 ? C.accent : C.text,
      alignment: "center",
    }));
  });
  return out;
}

async function exportPreview(presentation, slide, idx) {
  const name = String(idx).padStart(2, "0");
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  fs.writeFileSync(path.join(PREVIEW_DIR, `slide-${name}.png`), Buffer.from(await png.arrayBuffer()));
  const layout = await presentation.export({ slide, format: "layout" });
  fs.writeFileSync(path.join(QA_DIR, `slide-${name}.layout.json`), await layout.text(), "utf8");
}

async function main() {
  fs.mkdirSync(PREVIEW_DIR, { recursive: true });
  fs.mkdirSync(QA_DIR, { recursive: true });
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  const slides = [
    titleSlide,
    slide2,
    slide3,
    slide4,
    slide5,
    slide6,
    slide7,
    slide8,
    slide9,
    slide10,
    slide11,
    slide12,
  ].map((fn) => fn(presentation));

  for (let i = 0; i < slides.length; i += 1) {
    await exportPreview(presentation, slides[i], i + 1);
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(FINAL_PPTX);

  const manifest = {
    output: FINAL_PPTX,
    slideCount: slides.length,
    slideSize: { width: W, height: H },
    previewDir: PREVIEW_DIR,
    qaDir: QA_DIR,
    font: font,
    generatedAt: new Date().toISOString(),
  };
  fs.writeFileSync(path.join(WORKSPACE, "artifact-build-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify(manifest, null, 2));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error.stack || error.message || String(error));
    process.exit(1);
  });
