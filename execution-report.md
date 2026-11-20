# SOP 指标对账执行报告

被测公开源码提交：5c9fcad20df249f95d9305542bb9588ce68e481c

运行环境：Windows，Python 3.12.1, httpx 0.28.1, pytest 9.2.0。

通过匿名克隆获取源码。两条 API 路径均使用 httpx.MockTransport 和虚构数据验证。联调时需接入客户测试站点、测试数据写入和软删除方式，并核对 README 中的口径库占位编号。

~~~text
python -B -m pytest -v -s --no-header -p no:cacheprovider
============================= test session starts =============================
collecting ... collected 5 items

test_reconciliation.py::test_both_endpoints_update_after_soft_deletion initial sop_on_time_rate: expected=Metric(numerator=12, denominator=20, percent=Decimal('60.0')) SOP=Metric(numerator=12, denominator=20, percent=Decimal('60.0')) dashboard=Metric(numerator=12, denominator=20, percent=Decimal('60.0'))
initial sop_overdue_rate: expected=Metric(numerator=6, denominator=20, percent=Decimal('30.0')) SOP=Metric(numerator=6, denominator=20, percent=Decimal('30.0')) dashboard=Metric(numerator=6, denominator=20, percent=Decimal('30.0'))
after-delete sop_on_time_rate: expected=Metric(numerator=11, denominator=19, percent=Decimal('57.9')) SOP=Metric(numerator=11, denominator=19, percent=Decimal('57.9')) dashboard=Metric(numerator=11, denominator=19, percent=Decimal('57.9'))
after-delete sop_overdue_rate: expected=Metric(numerator=6, denominator=19, percent=Decimal('31.6')) SOP=Metric(numerator=6, denominator=19, percent=Decimal('31.6')) dashboard=Metric(numerator=6, denominator=19, percent=Decimal('31.6'))
PASSED
test_reconciliation.py::test_comparison_catches_a_dashboard_that_still_counts_the_deleted_record PASSED
test_reconciliation.py::test_mock_uses_the_reporting_month_and_site_for_its_denominator PASSED
test_reconciliation.py::test_comparison_rejects_incomplete_metrics_from_either_endpoint[stats] PASSED
test_reconciliation.py::test_comparison_rejects_incomplete_metrics_from_either_endpoint[metrics] PASSED

============================== 5 passed in 0.11s ==============================
~~~

