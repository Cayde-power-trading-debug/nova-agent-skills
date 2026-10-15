# 因子研究表与快速筛查合同

## 从生产链路构造一行

一行代表一个省份、目标日、起报时间和一个候选因子值。先从 `prediction_batches`/正式预测输出取负荷预测及其生成时间，从冻结价格分析取日前/实时预测，从当时天气预报快照取天气，从实际负荷或价格文件取事后标签；所有表以目标日和小时对齐。不同省份不合并估计；同一天的小时记录放在同一验证折。

CSV 至少包含 `province,target_date,issued_at,feature_available_at,label_available_at,factor,label`，可加 `scenario`。`issued_at`、两个可用时间统一为同一时区 ISO 时间；`factor` 的单位和标签定义另存一份研究说明。例：

```csv
province,target_date,issued_at,feature_available_at,label_available_at,factor,label,scenario
广西,2026-09-10,2026-09-07T09:00:00+08:00,2026-09-07T08:50:00+08:00,2026-09-11T09:00:00+08:00,1.2,22.4,常规日
```

本脚本对已准备的单因子表做第一轮筛查：

```powershell
python scripts/screen_factor.py factor_rows.csv --test-start 2026-10-01 --out screen.json
```

脚本拒绝未来因子、非数值和同目标日跨训练/测试，训练标签必须在测试起点前已经可用；用训练期均值作固定基线，用训练期一元线性拟合系数，在测试期比较 MAE。输出 `train_pearson`、`test_pearson`、`baseline_test_mae`、`factor_test_mae`、`mae_improvement`、分场景 MAE 与排除计数。它不会自动看全量库或修改因子库。

## 晋级前的必补证据

- 多个滚动起报窗、同目标日分组、各季度和节假日的样本外稳定性。
- 同省负荷与价格预测的条件分析，控制小时、星期、季节与共线天气；不要把云南负荷直接对齐广西价格。
- 与当前正式基线比较方向命中、覆盖率、概率可靠度、WAPE/MAE 及交易约束下的理论机会；多因子筛选时控制重复试验。
- 记录 `model_version`、`price_dataset_id`、`weather_snapshot_id`、`factor_hash`、来源哈希、起报时可用性和被排除行。
- 若声称真实收益，另关联申报量、成交、合同、考核与结算；`screen_factor.py` 的 MAE 改善不代表套利收益。

研究结论达到预先冻结门槛后，再通过 `factor_library.py` 的版本治理发布；脚本本身不会晋级或部署因子。

