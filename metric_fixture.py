"""Fictional SOP records for validating the two metric endpoints."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP


AS_OF = datetime(2026, 11, 15, 12, tzinfo=timezone(timedelta(hours=8)))
PERIOD = AS_OF.replace(day=1, hour=0)
SITE = 'sample-site'


@dataclass(frozen=True)
class Todo:
    id: str
    created_at: datetime
    due_at: datetime
    completed_at: datetime | None
    site: str = SITE
    deleted_at: datetime | None = None


def sample_records() -> list[Todo]:
    due = AS_OF - timedelta(days=1)
    groups = [
        ('on-time', 12, due, due - timedelta(hours=1)),
        ('late-done', 4, due, due + timedelta(hours=1)),
        ('late-open', 2, due, None),
        ('not-due', 2, AS_OF + timedelta(days=1), None),
    ]
    records = [Todo(f'{group}-{index}', PERIOD, deadline, completed)
               for group, count, deadline, completed in groups for index in range(count)]
    return records + [Todo('excluded-from-start', PERIOD, due, due, deleted_at=AS_OF - timedelta(hours=1))]


def delete_on_time_record(records: list[Todo]) -> list[Todo]:
    return [replace(row, deleted_at=AS_OF) if row.id == 'on-time-0' else row for row in records]


def _percentage(numerator: int, denominator: int) -> str | None:
    if denominator == 0:
        return None
    return str((Decimal(numerator) * 100 / denominator).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def expected_mock_metrics(records: list[Todo]) -> dict:
    eligible = [row for row in records if row.site == SITE and PERIOD <= row.created_at <= AS_OF and row.deleted_at is None]
    on_time = sum(row.completed_at is not None and row.completed_at <= row.due_at for row in eligible)
    overdue = sum((row.completed_at > row.due_at if row.completed_at is not None else AS_OF > row.due_at)
                  for row in eligible)
    return {key: {'numerator': count, 'denominator': len(eligible), 'percent': _percentage(count, len(eligible))}
            for key, count in (('sop_on_time_rate', on_time), ('sop_overdue_rate', overdue))}


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after-delete', action='store_true', help='Include the second soft deletion.')
    args = parser.parse_args()
    records = sample_records()
    if args.after_delete:
        records = delete_on_time_record(records)
    print(json.dumps([asdict(record) for record in records], default=datetime.isoformat, indent=2))
