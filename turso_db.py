import os
from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone

import libsql
from dotenv import load_dotenv

from upsert_db import UPSERT_SQL

# 從這個模組所在目錄定位 .env，避免受執行位置影響。
ENV_PATH = Path(__file__).resolve().with_name(".env")

OBSERVATION_FIELDS = (
    "station_id",
    "station_name",
    "observed_at",
    "county_name",
    "town_name",
    "altitude",
    "latitude",
    "longitude",
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_direction",
    "wind_direction_variable",
    "precipitation",
    "precipitation_status",
    "fetched_at",
)

def connect_turso():
    """讀取環境設定，建立 Turso 連線。"""

    # 已經存在的環境變數優先；本機缺少時才從 .env 載入。
    load_dotenv(ENV_PATH, override=False)

    database_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not database_url or not auth_token:
        raise ValueError("缺少 Turso 連線設定")

    return libsql.connect(
        database=database_url,
        auth_token=auth_token,
    )


def get_observation_count():
    """唯讀查詢雲端觀測資料總筆數。"""

    with closing(connect_turso()) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM weather_observations"
        ).fetchone()

    return row[0]


def get_refresh_status():
    """查詢最近一次更新結果；尚無紀錄時回傳 None。"""

    with closing(connect_turso()) as connection:
        row = connection.execute(
            """
            SELECT
                last_attempt_at,
                last_attempt_status,
                last_success_at,
                error_code
            FROM weather_refresh_status
            WHERE id = 1
            """
        ).fetchone()

    if row is None:
        return None

    return {
        "attempted_at": row[0],
        "status": row[1],
        "last_success_at": row[2],
        "error_code": row[3],
    }


def _write_refresh_status(connection, status, error_code=None):
    """使用既有連線寫入狀態，由呼叫者負責交易。"""

    attempted_at = datetime.now(timezone.utc).isoformat(
        timespec="microseconds"
    )
    last_success_at = attempted_at if status == "succeeded" else None

    connection.execute(
        """
        INSERT INTO weather_refresh_status (
            id, last_attempt_at, last_attempt_status,
            last_success_at, error_code
        )
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            last_attempt_at = excluded.last_attempt_at,
            last_attempt_status = excluded.last_attempt_status,
            last_success_at = CASE
                WHEN excluded.last_attempt_status = 'succeeded'
                THEN excluded.last_success_at
                ELSE weather_refresh_status.last_success_at
            END,
            error_code = excluded.error_code
        """,
        (attempted_at, status, last_success_at, error_code),
    )


def record_refresh_failure(error_code="CWA_UNAVAILABLE"):
    """保存失敗結果，保留上一次成功時間及既有觀測資料。"""

    if error_code not in {"CWA_UNAVAILABLE", "DATABASE_UNAVAILABLE"}:
        raise ValueError("不支援的更新錯誤碼")

    with closing(connect_turso()) as connection:
        connection.execute("BEGIN")

        try:
            _write_refresh_status(connection, "failed", error_code)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def save_observations(stations, *, record_refresh_success=False):
    """以多列 UPSERT 保存整批資料，觀測與成功狀態使用同一交易。"""

    if not stations:
        raise ValueError("沒有測站資料可寫入")

    parameters = [
        tuple(station[field] for field in OBSERVATION_FIELDS)
        for station in stations
    ]

    # 沿用共用 SQL 的欄位與衝突更新規則，改成每次寫入最多 50 列。
    insert_part, conflict_part = UPSERT_SQL.split("ON CONFLICT", 1)
    insert_prefix = insert_part.split("VALUES", 1)[0]
    row_placeholders = "(" + ", ".join(["?"] * len(OBSERVATION_FIELDS)) + ")"
    batch_size = 50

    with closing(connect_turso()) as connection:
        connection.execute("BEGIN")

        try:
            for offset in range(0, len(parameters), batch_size):
                batch = parameters[offset:offset + batch_size]
                placeholders = ", ".join([row_placeholders] * len(batch))
                batch_sql = (
                    f"{insert_prefix}VALUES {placeholders}\n"
                    f"ON CONFLICT {conflict_part}"
                )
                batch_parameters = tuple(value for row in batch for value in row)
                connection.execute(batch_sql, batch_parameters)

            if record_refresh_success:
                _write_refresh_status(connection, "succeeded")

            connection.commit()
        except Exception:
            connection.rollback()
            raise

        count = connection.execute(
            "SELECT COUNT(*) FROM weather_observations"
        ).fetchone()[0]

    return count


def get_latest_observations(county_name=None, station_id=None):
    """取得各測站最新觀測，可依縣市或測站篩選。"""

    columns = ", ".join(
        f"observation.{field}"
        for field in OBSERVATION_FIELDS
    )

    sql = f"""
    WITH latest AS (
        SELECT station_id, MAX(observed_at) AS observed_at
        FROM weather_observations
        GROUP BY station_id
    )
    SELECT {columns}
    FROM weather_observations AS observation
    JOIN latest
      ON observation.station_id = latest.station_id
     AND observation.observed_at = latest.observed_at
    """

    conditions = []
    parameters = []

    if county_name is not None:
        conditions.append("observation.county_name = ?")
        parameters.append(county_name)

    if station_id is not None:
        conditions.append("observation.station_id = ?")
        parameters.append(station_id)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY observation.station_id ASC"

    with closing(connect_turso()) as connection:
        rows = connection.execute(
            sql,
            tuple(parameters),
        ).fetchall()

    observations = []

    for row in rows:
        observation = dict(zip(OBSERVATION_FIELDS, row))

        # SQLite 的 0／1 轉回 Python bool，供 JSON 回傳。
        observation["wind_direction_variable"] = bool(
            observation["wind_direction_variable"]
        )

        observations.append(observation)

    return observations


def main():
    try:
        count = get_observation_count()
        observations = get_latest_observations()
    except Exception as error:
        print("Turso 查詢失敗：", type(error).__name__)
        return 1

    print("Turso 連線：PASS")
    print("雲端資料總筆數：", count)
    print("最新測站筆數：", len(observations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
