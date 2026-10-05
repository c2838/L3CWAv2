import os
from contextlib import closing
from pathlib import Path

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


def save_observations(stations):
    """將一批標準化測站資料 UPSERT 至 Turso，回傳總筆數。"""

    if not stations:
        raise ValueError("沒有測站資料可寫入")

    # 按 SQL 參數順序取值；缺少欄位時會在連線前發生 KeyError。
    parameters = [
        tuple(station[field] for field in OBSERVATION_FIELDS)
        for station in stations
    ]

    with closing(connect_turso()) as connection:
        # 整批資料使用同一個交易。
        connection.execute("BEGIN")

        try:
            connection.executemany(UPSERT_SQL, parameters)
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
