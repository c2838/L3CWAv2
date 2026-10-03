from contextlib import closing
from pathlib import Path
import sqlite3


# 使用 insert_db.py 所在目錄定位資料庫，避免從其他目錄執行時找錯檔案。
DB_PATH = Path(__file__).resolve().with_name("weather_observations.db")

# """ 使字串可以跨行
UPSERT_SQL = """
INSERT INTO weather_observations (
    station_id, station_name, observed_at, county_name, town_name,
    altitude, latitude, longitude, temperature, humidity, pressure,
    wind_speed, wind_direction, wind_direction_variable,
    precipitation, precipitation_status, fetched_at
) VALUES (
    :station_id, :station_name, :observed_at, :county_name, :town_name,
    :altitude, :latitude, :longitude, :temperature, :humidity, :pressure,
    :wind_speed, :wind_direction, :wind_direction_variable,
    :precipitation, :precipitation_status, :fetched_at
)
ON CONFLICT (station_id, observed_at) DO UPDATE SET
    station_name = excluded.station_name,
    county_name = excluded.county_name,
    town_name = excluded.town_name,
    altitude = excluded.altitude,
    latitude = excluded.latitude,
    longitude = excluded.longitude,
    temperature = excluded.temperature,
    humidity = excluded.humidity,
    pressure = excluded.pressure,
    wind_speed = excluded.wind_speed,
    wind_direction = excluded.wind_direction,
    wind_direction_variable = excluded.wind_direction_variable,
    precipitation = excluded.precipitation,
    precipitation_status = excluded.precipitation_status,
    fetched_at = excluded.fetched_at
"""


def save_observations(stations):
    """將一批標準化測站資料寫入本機 SQLite，回傳資料庫總筆數。"""
    if not stations:
        raise ValueError("沒有測站資料可寫入")

    # connect() 遇到不存在的檔案會建立新資料庫；先檢查以免寫錯位置。
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"找不到資料庫：{DB_PATH}")

    with closing(sqlite3.connect(DB_PATH)) as connection:
        # 成功時提交整批寫入；發生錯誤時回滾整批寫入。
        with connection:
            # 每個 dict 對應執行一次 SQL；欄位值由具名參數帶入。
            connection.executemany(UPSERT_SQL, stations)

        # 寫入完成後確認目前資料表的總筆數。
        count = connection.execute(
            "SELECT COUNT(*) FROM weather_observations"
        ).fetchone()[0]

    return count
