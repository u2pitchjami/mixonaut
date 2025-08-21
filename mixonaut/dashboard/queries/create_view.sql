SELECT 'create_views: start';

CREATE TABLE IF NOT EXISTS torrent_decisions (
  torrent_hash TEXT PRIMARY KEY,
  decision TEXT NOT NULL,
  reason TEXT,
  decided_at TEXT DEFAULT (CURRENT_TIMESTAMP),
  decided_by TEXT
);
CREATE INDEX IF NOT EXISTS ix_tdec_decision ON torrent_decisions(decision);

CREATE VIEW IF NOT EXISTS v_torrent_base AS
SELECT
  ifs.torrent_hash,
  MAX(ifs.torrent_name) AS torrent_name,
  MAX(ifs.torrent_ratio) AS ratio,
  MAX(ifs.torrent_added_on) AS added_on,
  MAX(ifs.torrent_completion_on) AS completed_on,
  MAX(ifs.imported_in_beets_at) AS imported_at,
  MAX(ifs.auto_cleaned) AS any_cleaned
FROM imported_files ifs
GROUP BY ifs.torrent_hash;

CREATE VIEW IF NOT EXISTS v_torrent_status AS
SELECT
  b.torrent_hash,
  b.torrent_name,
  b.ratio,
  b.added_on,
  b.completed_on,
  b.imported_at,
  COALESCE(d.decision, 'PENDING') AS decision,
  d.reason,
  d.decided_at,
  (julianday('now') - julianday(datetime(b.added_on, 'unixepoch'))) AS age_days,
  CASE WHEN d.decided_at IS NOT NULL
       THEN (julianday('now') - julianday(d.decided_at)) ELSE NULL END AS since_decision_days
FROM v_torrent_base b
LEFT JOIN torrent_decisions d ON d.torrent_hash = b.torrent_hash;

CREATE VIEW IF NOT EXISTS v_ready_for_deletion AS
SELECT
  ts.torrent_hash,
  ts.torrent_name,
  ts.decision,
  ts.ratio,
  ts.age_days,
  ts.since_decision_days,
  datetime(ts.added_on, 'unixepoch') AS added_on_dt,
  datetime(ts.completed_on, 'unixepoch') AS completed_on_dt,
  ts.imported_at
FROM v_torrent_status ts
WHERE
  (ts.ratio >= 2.0 OR ts.age_days >= 30)
  AND (
    ts.imported_at IS NOT NULL
    OR ts.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
    OR (ts.decision IN ('NEEDS_MANUAL','DUPLICATE_SOFT') AND ts.since_decision_days >= 14)
  )
ORDER BY ts.completed_on DESC NULLS LAST, ts.torrent_name;

CREATE VIEW IF NOT EXISTS v_needs_manual AS
SELECT
  ts.torrent_hash,
  ts.torrent_name,
  ts.decision,
  ts.ratio,
  ts.age_days,
  ts.since_decision_days,
  datetime(ts.added_on, 'unixepoch') AS added_on_dt
FROM v_torrent_status ts
WHERE ts.imported_at IS NULL
  AND ts.decision IN ('NEEDS_MANUAL','DUPLICATE_SOFT')
ORDER BY ts.since_decision_days DESC NULLS LAST, ts.age_days DESC, ts.torrent_name;

CREATE VIEW IF NOT EXISTS v_rejected AS
SELECT
  ts.torrent_hash,
  ts.torrent_name,
  ts.decision,
  ts.ratio,
  ts.age_days,
  datetime(ts.added_on, 'unixepoch') AS added_on_dt,
  ts.decided_at
FROM v_torrent_status ts
WHERE ts.imported_at IS NULL
  AND ts.decision IN ('REJECT','DUPLICATE_HARD','REPLACED')
ORDER BY ts.age_days DESC, ts.torrent_name;

SELECT 'create_views: done';
