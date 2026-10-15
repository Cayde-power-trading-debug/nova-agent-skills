---
name: nova-price-signal-audit
description: Use when explaining, auditing, or reproducing NOVA Agent Guangxi price-data cleaning, day-ahead price-change signals, coefficients, calibrated probabilities, or their retrospective accuracy; not for changing live trading parameters.
---

# NOVA 价格信号溯源

本 Skill 输出一份能由源码、冻结系数和事前记录复核的价格信号说明。先确认当前安装程序的源码版本、数据根目录与目标省份；不要把旧发布包、源码默认常量或海报数字当成运行时事实。

## 业务口径

区分两种问题：**跨日日前均价变化** `P̄_DA(T)−P̄_DA(B)` 用于价格涨跌信号；**同小时日前－实时价差** `P_DA(T,h)−P_RT(T,h)` 用于申报方向。这两套系数、样本和准确率不能互换。只在完整 24 小时日前价格上计算日均价；缺失、冲突和日期恢复均须保留数据质量记录。

## 核验顺序

1. 从 `price_data.py` 核对 Excel 的日期、市场和 24 小时解析，以及冲突隔离；记录价格数据集 ID/哈希。
2. 从运行时 `FactorLibrary` 读取 `gx_calibration_d1` 和 `gx_calibration_d3`，记录 `version`、`label_cutoff`、系数和残差数。优先使用当前运行时因子版本，不能只引用 `price_signal_calibration.py` 模板。
3. 依据 `price_signal_logic.py` 重建目标日/基准日、天气标准化变化、线性价差、经验残差概率和提示门槛。历史复盘只使用起报前可得天气与标签。
4. 依据 `price_signal_review.py` 从保存的事前快照中挑选每日各提前期首份正式分析，对完整实际日前价格评估。输出命中数/提示数、无提示数、MAE、按提前期拆分，并列出排除原因。
5. 若还讨论日前申报，单独使用 `declaration_export.py` 和 `build_declaration_calendar`。理论价差机会不是成交人民币收益；需另找申报电量、成交和结算流水。

需要解释公式、核心代码和截至 2026-10-15 的已核验系数时，读 [公式与代码对照](references/formulas-and-code.md)。其中数字是带日期的运行时快照，下一次执行须重新读取。

需要独立复算一份**已保存分析**的系数贡献和概率时，使用 `scripts/replay_snapshot.py`；输入 JSON 格式与最小调用示例见 [可复算输入合同](references/replay-contract.md)。脚本只读本地快照并输出逐因子贡献、`μ`、上涨/下跌概率和与保存信号的差异；先核对版本和 `label_cutoff`，再讨论准确率。它不是生产价差引擎，也不发布信号。

报告里同时列出两套不能混称的准确率：价格信号台账的 **D−3 累计情景准确率**按 `signal_ledger.select_review_records` 选每个目标日的原预测，自动任务优先；研究审计的**事前有效首份提示准确率**按 `price_signal_review.review` 筛样。前者在 2026-10-15 快照为 12/15 = 80.0%，后者为 38/55 = 69.1%；两个分母都要随数据更新而重算。

## 输出合同

提供数据集/因子/信号版本、统计日期、样本筛选、公式、系数表、核心源码定位、准确率分子分母、排除数及结果边界。未经同口径基线验证，不写“提升”；未经交易结算，不写“实际套利利润”。研究或复核默认只读，不改历史信号、运行因子和正式报告。

