"""Read SOP metrics over HTTP and compare counts and presentation values."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import httpx


KEYS = ('sop_on_time_rate', 'sop_overdue_rate')


@dataclass(frozen=True)
class Metric:
    numerator: int
    denominator: int
    percent: Decimal


def _read_metrics(response: httpx.Response, section: str) -> dict[str, Metric]:
    response.raise_for_status()
    try:
        payload = response.json()[section]
        metrics = {}
        for key in KEYS:
            entry = payload[key]
            numerator, denominator = entry['numerator'], entry['denominator']
            percent = Decimal(str(entry['percent']).removesuffix('%'))
            if (type(numerator) is not int or type(denominator) is not int
                    or not 0 <= numerator <= denominator or not percent.is_finite()
                    or not 0 <= percent <= 100):
                raise ValueError(f'Invalid values for {key}.')
            metrics[key] = Metric(numerator, denominator, percent)
        return metrics
    except (TypeError, KeyError, InvalidOperation, ValueError) as exc:
        raise ValueError(f'Invalid {section} metrics from {response.request.url.path}.') from exc


def compare_endpoints(
    client: httpx.Client,
    *,
    sop_section: str = 'stats',
    dashboard_section: str = 'metrics',
    params: dict[str, str] | None = None,
) -> tuple[dict[str, Metric], dict[str, Metric]]:
    """Return the two validated samples, or raise with the fields that disagree."""
    filters = params or {}
    sop = _read_metrics(client.get('/api/sop/stats', params=filters), sop_section)
    dashboard_params = filters | {'keys': ','.join(KEYS)}
    dashboard = _read_metrics(client.get('/api/dashboard/metrics', params=dashboard_params), dashboard_section)
    differences = [f'{key}: {sop[key]} != {dashboard[key]}' for key in KEYS if sop[key] != dashboard[key]]
    if differences:
        raise AssertionError('SOP and dashboard disagree: ' + '; '.join(differences))
    return sop, dashboard
