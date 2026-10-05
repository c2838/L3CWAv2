-- 保存最近一次更新結果，讓不同 API 執行個體都可讀取。
CREATE TABLE IF NOT EXISTS weather_refresh_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_attempt_at TEXT NOT NULL,
    last_attempt_status TEXT NOT NULL
        CHECK (last_attempt_status IN ('succeeded', 'failed')),
    last_success_at TEXT,
    error_code TEXT,
    CHECK (
        (last_attempt_status = 'succeeded'
            AND last_success_at IS NOT NULL
            AND error_code IS NULL)
        OR
        (last_attempt_status = 'failed'
            AND error_code IS NOT NULL
            AND error_code IN ('CWA_UNAVAILABLE', 'DATABASE_UNAVAILABLE'))
    )
);
