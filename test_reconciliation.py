from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from metric_fixture import AS_OF, PERIOD, delete_on_time_record, expected_mock_metrics, sample_records
from reconcile_endpoints import KEYS, Metric, compare_endpoints


def test_both_endpoints_update_after_soft_deletion():
    rows = sample_records()
    assert len(rows) == 21
    assert {row.id for row in rows if row.deleted_at is not None} == {'excluded-from-start'}

    def handler(request):
        if request.url.path == '/api/sop/stats':
            return httpx.Response(200, json={'stats': expected_mock_metrics(rows)})
        if request.url.path == '/api/dashboard/metrics':
            assert request.url.params['keys'] == 'sop_on_time_rate,sop_overdue_rate'
            return httpx.Response(200, json={'metrics': expected_mock_metrics(rows)})
        return httpx.Response(404)

    def assert_metrics(client, stage, on_time, overdue):
        golden = {KEYS[0]: Metric(*on_time), KEYS[1]: Metric(*overdue)}
        sop, dashboard = compare_endpoints(client)
        assert sop == dashboard == golden
        for key in KEYS:
            print(f'{stage} {key}: expected={golden[key]} SOP={sop[key]} dashboard={dashboard[key]}')

    with httpx.Client(base_url='https://sop-fixture.invalid', transport=httpx.MockTransport(handler)) as client:
        assert_metrics(client, 'initial', (12, 20, Decimal('60.0')), (6, 20, Decimal('30.0')))
        rows = delete_on_time_record(rows)
        assert len(rows) == 21
        assert {row.id for row in rows if row.deleted_at is not None} == {'excluded-from-start', 'on-time-0'}
        assert_metrics(client, 'after-delete', (11, 19, Decimal('57.9')), (6, 19, Decimal('31.6')))


def test_comparison_catches_a_dashboard_that_still_counts_the_deleted_record():
    original = sample_records()
    current = original
    filters = {'site_id': 'sample-site', 'month': '2026-11'}

    def stale_dashboard(request):
        assert all(request.url.params[name] == value for name, value in filters.items())
        if request.url.path == '/api/sop/stats':
            return httpx.Response(200, json={'stats': expected_mock_metrics(current)})
        return httpx.Response(200, json={'metrics': expected_mock_metrics(original)})

    with httpx.Client(base_url='https://sop-fixture.invalid', transport=httpx.MockTransport(stale_dashboard)) as client:
        compare_endpoints(client, params=filters)
        current = delete_on_time_record(original)
        with pytest.raises(AssertionError, match='sop_on_time_rate.*sop_overdue_rate'):
            compare_endpoints(client, params=filters)


def test_mock_uses_the_reporting_month_and_site_for_its_denominator():
    rows = sample_records()
    sample = rows[0]
    rows += [
        replace(sample, id='outside-month', created_at=PERIOD - timedelta(seconds=1)),
        replace(sample, id='after-cutoff', created_at=AS_OF + timedelta(seconds=1)),
        replace(sample, id='other-site', site='other-site'),
    ]

    assert expected_mock_metrics(rows) == {
        'sop_on_time_rate': {'numerator': 12, 'denominator': 20, 'percent': '60.0'},
        'sop_overdue_rate': {'numerator': 6, 'denominator': 20, 'percent': '30.0'},
    }


@pytest.mark.parametrize('incomplete_section', ['stats', 'metrics'])
def test_comparison_rejects_incomplete_metrics_from_either_endpoint(incomplete_section):
    metrics = expected_mock_metrics(sample_records())

    def handler(request):
        section = 'stats' if request.url.path == '/api/sop/stats' else 'metrics'
        payload = {KEYS[0]: metrics[KEYS[0]]} if section == incomplete_section else metrics
        return httpx.Response(200, json={section: payload})

    with httpx.Client(base_url='https://sop-fixture.invalid', transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match=f'Invalid {incomplete_section} metrics'):
            compare_endpoints(client)
