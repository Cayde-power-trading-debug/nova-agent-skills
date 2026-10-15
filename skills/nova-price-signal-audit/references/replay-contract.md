# 价格信号可复算快照合同

## 构造

从**同一份已保存分析**导出 `as_of`、`weather_heatmap`、`weather_signal.reference`、`threshold.value`、`marker_probability`、`signals`；再按该分析引用的因子版本，从运行时因子库导出 `gx_calibration_d1` 与 `gx_calibration_d3` 为 `calibration_d1`、`calibration_d3`。不要从今天的因子库给历史分析补新系数。来源文件、哈希、分析 ID、导出时间写在旁边的审计记录，输入 JSON 不放账号、企业原始价格或密钥。

最小结构：

```json
{
  "as_of": "2026-09-20",
  "threshold": {"value": 50},
  "marker_probability": 0.6,
  "weather_heatmap": [
    {"date": "2026-09-20", "values": {"wind": {"value": 4}}},
    {"date": "2026-09-21", "values": {"wind": {"value": 6}}}
  ],
  "weather_signal": {"reference": {"wind": {"std": 2}}},
  "calibration_d1": {
    "version": "example-only", "label_cutoff": "2026-09-19",
    "intercept": 2, "coefficients": {"wind": 10},
    "calibration_residuals": [-3, 0, 3]
  },
  "calibration_d3": {
    "version": "example-only", "label_cutoff": "2026-09-19",
    "intercept": 2, "coefficients": {"wind": 10},
    "calibration_residuals": [-3, 0, 3]
  },
  "signals": []
}
```

示例只是结构示意，缺少 D+3–7 天气，运行时这些日期会标为 `missing_weather`。完整运行：

```powershell
python scripts/replay_snapshot.py saved_analysis.json --out replay.json
```

脚本按 `price_signal_logic.attach_signals` 重放 D+1 与 D+3–7 的基准日、线性项、经验残差平滑概率和双门槛信号；若与 `signals` 的数值差超过 `1e-8`，退出码为 2。若日期、版本、天气或残差不一致，先查快照完整性，不能直接宣布线上逻辑错误。概率并非实际命中率；台账累计命中需另按 `signal_ledger.select_review_records` 从事前记录和完整实际日前价格重算。

## 源码层次

1. `price_data.py`：日期、市场和 24 小时价格清洗，隔离冲突，产生实际标签。
2. `price_model.py`：30 天历史天气参照及日均价；正式预测与天气输入。
3. `factor_library.py`：运行时因子版本、哈希、标签截止日和发布绑定。
4. `price_signal_logic.py`：`μ=β₀+Σβⱼ·ΔWⱼ/σⱼ`；残差经验概率；金额与概率门槛。
5. `signal_ledger.py`：按目标日选择 D−3 原预测的台账累计情景准确率。
6. `price_signal_review.py`：事前有效首份提示的严格复核。

所有脚本仅对副本运行；生产源码和因子库不随此 Skill 打包上传。

