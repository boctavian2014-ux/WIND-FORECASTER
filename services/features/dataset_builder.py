from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.models.logreg_model import FEATURE_COLUMNS

_FEATURE_SQL = text(f'''
SELECT
    zone_id,
    target_time,
    {', '.join(FEATURE_COLUMNS)}
FROM features_15m
WHERE zone_id = :zone_id
  AND target_time BETWEEN :start_ts AND :end_ts
ORDER BY target_time
''')


def build_dataset(db: Session, zone_id: str, start_ts, end_ts) -> list[dict]:
    """Load ML feature rows; expects `features_15m` hypertable with FEATURE_COLUMNS."""
    rows = db.execute(
        _FEATURE_SQL,
        {'zone_id': zone_id, 'start_ts': start_ts, 'end_ts': end_ts},
    ).mappings().all()
    return [dict(r) for r in rows]
