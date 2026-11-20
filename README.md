# SOP 两个统计接口的口径对账

对应工单 S4-E2E-015。本文中的“执行率”即按时完成率。

| 口径库条目（占位） | 指标库查询键 | 分子 | 分母 |
| --- | --- | --- | --- |
| `PLACEHOLDER-SOP-ON-TIME-RATE` | `sop_on_time_rate` | 截止时间内完成的有效待办 | 同站点同月、统计时点前已创建且有效的全部待办 |
| `PLACEHOLDER-SOP-OVERDUE-RATE` | `sop_overdue_rate` | 超时完成及统计时点已超时仍未完成的有效待办 | 同上 |

联调时在客户口径库按查询键分别找到对应条目，核对分子、分母、软删除和舍入规则后，将表中的占位编号替换为正式条目编号。原始计数先除后乘 100，展示值四舍五入保留一位小数。运行证据见 [执行报告](execution-report.md)。

用 Python 3.11+、pytest 和 httpx 运行。

```shell
python -m pip install -r requirements.txt
python -m pytest -q
```

使用 `python -m pytest -q -s` 可查看两个阶段每项指标的预期值、SOP 实测值和驾驶舱实测值。仅在已获授权的测试环境中运行下例。先经客户测试夹具载入初始数据，再软删除 `on-time-0` 后复跑。通过环境变量传入站点、地址和测试凭据。

```python
import os
import httpx
from reconcile_endpoints import compare_endpoints

with httpx.Client(base_url=os.environ["SOP_TEST_URL"],
                  headers={"Authorization": "Bearer " + os.environ["SOP_TEST_TOKEN"]},
                  timeout=15) as client:
    sop, dashboard = compare_endpoints(
        client, params={"site_id": os.environ["SOP_TEST_SITE"], "month": "2026-11"}
    )
    print(sop, dashboard)
```

用 `python metric_fixture.py` 导出初始 JSON，或用 `python metric_fixture.py --after-delete` 导出再软删除一条后的 JSON。时间字段使用带时区偏移的 ISO 8601 格式。

样例固定在上海时间 2026 年 11 月 15 日 12:00，构造同月同站点的 21 条虚构待办，其中 1 条一开始已软删除。超时包括逾期完成和到期未完成。截止时间前完成或正好到截止时间完成计为准时。准时率和超时率都用有效待办总数做分母。

| 阶段 | 准时率 | 超时率 |
| --- | --- | --- |
| 仅存在原软删除记录 | 12 / 20，60.0% | 6 / 20，30.0% |
| 再软删除一条准时记录 | 11 / 19，57.9% | 6 / 19，31.6% |

`reconcile_endpoints.compare_endpoints` 使用传入的 `httpx.Client` 分别请求 `/api/sop/stats` 和 `/api/dashboard/metrics`，比较两个响应的分子、分母和展示值。测试检查结果是否符合上表，还在同一客户端和筛选条件下先确认两接口一致，再软删除记录并检测看板仍返回旧值的故障。当前验收用例使用 `httpx.MockTransport`。接入真实系统时可通过客户端设置测试环境和身份，并按实际筛选参数和响应结构对接，随后核对指标定义库中的条目编号。
