import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from upsert_db import save_observations as save_observations_to_sqlite

CWA_API_URL = (
    "https://opendata.cwa.gov.tw/"
    "api/v1/rest/datastore/O-A0003-001"
)
ENV_PATH = Path(__file__).resolve().with_name(".env")

class CWAError(Exception):
    """取得 CWA 資料時發生的可處理錯誤。"""
    pass


# 檢查 dict 型別，型別錯誤則回傳空值
def as_dict(value):
    """不是 dict 時回傳空 dict。"""

    if isinstance(value, dict):
        return value

    return {}


# 檢查 list 型別，型別錯誤則回傳空值
def as_list(value):
    """不是 list 時回傳空 list。"""

    if isinstance(value, list):
        return value

    return []


# 檢查 float 型別，型別錯誤則回傳空值
def to_float(value):
    """將一般氣象數值轉成 float，無效值轉成 None。"""

    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if value in {"", "X"}:
            return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    # 氣象署以 -99 表示缺值或資料異常。
    if number == -99:
        return None

    return number


# 格式化回傳特殊值
def parse_precipitation(value):
    """轉換降水量，並保留特殊狀態。"""

    raw_value = "" if value is None else str(value).strip()

    # T 代表雨跡：雨量小於可量測精度，但確實有降雨。
    if raw_value == "T":
        return 0.0, "trace"

    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError):
        return None, "missing"

    # -98 代表連續六小時無降水。
    if numeric_value == -98:
        return 0.0, "no_rain_6h"

    # -99 代表缺值或資料異常。
    if numeric_value == -99:
        return None, "missing"

    return numeric_value, "measured"


def parse_wind_direction(value):
    """轉換風向；990 代表風向不定。"""

    wind_direction = to_float(value)

    if wind_direction == 990:
        return None, True

    return wind_direction, False


def find_wgs84_coordinate(coordinates):
    """依名稱尋找 WGS84 座標，不依賴清單順序。"""

    for coordinate in coordinates:
        if not isinstance(coordinate, dict):
            continue

        if coordinate.get("CoordinateName") == "WGS84":
            return coordinate

    return None


# 格式化觀測資料格式
def normalize_station(station, fetched_at):
    """將一筆 CWA 測站資料轉成固定格式。"""

    obs_time = as_dict(station.get("ObsTime"))
    geo_info = as_dict(station.get("GeoInfo"))
    weather = as_dict(station.get("WeatherElement"))
    now = as_dict(weather.get("Now"))

    coordinates = as_list(geo_info.get("Coordinates"))
    wgs84 = find_wgs84_coordinate(coordinates) or {}

    precipitation, precipitation_status = parse_precipitation(
        now.get("Precipitation")
    )

    wind_direction, wind_direction_variable = parse_wind_direction(
        weather.get("WindDirection")
    )

    return {
        "station_id": station.get("StationId"),
        "station_name": station.get("StationName"),
        "observed_at": obs_time.get("DateTime"),
        "county_name": geo_info.get("CountyName"),
        "town_name": geo_info.get("TownName"),
        "altitude": to_float(
            geo_info.get("StationAltitude")
        ),
        "latitude": to_float(
            wgs84.get("StationLatitude")
        ),
        "longitude": to_float(
            wgs84.get("StationLongitude")
        ),
        "temperature": to_float(
            weather.get("AirTemperature")
        ),
        "humidity": to_float(
            weather.get("RelativeHumidity")
        ),
        "pressure": to_float(
            weather.get("AirPressure")
        ),
        "wind_speed": to_float(
            weather.get("WindSpeed")
        ),
        "wind_direction": wind_direction,
        "wind_direction_variable": wind_direction_variable,
        "precipitation": precipitation,
        "precipitation_status": precipitation_status,
        "fetched_at": fetched_at,
    }


# fetch api function
def fetch_stations(api_key):
    """向 CWA API 取得測站資料，失敗時拋出 CWAError。"""

    params = {
        "Authorization": api_key,
        "format": "JSON",
    }

    try:
        response = requests.get(
            CWA_API_URL,
            params=params,
            timeout=15,
        )
    except requests.RequestException:
        # 隱藏原始例外，避免其包含帶有金鑰的 URL。
        raise CWAError("無法連線至 CWA") from None

    if response.status_code != 200:
        raise CWAError(
            f"CWA HTTP 回應失敗：{response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError:
        raise CWAError(
            "CWA 回應不是有效的 JSON"
        ) from None

    if not isinstance(payload, dict):
        raise CWAError("CWA 回應不是預期的 dict")

    if payload.get("success") not in (True, "true"):
        raise CWAError("CWA 回報資料取得失敗")

    records = payload.get("records")

    if not isinstance(records, dict):
        raise CWAError("records 不是預期的 dict")

    stations = records.get("Station")

    if not isinstance(stations, list):
        raise CWAError("Station 不是預期的 list")

    if not stations:
        raise CWAError("Station 清單是空的")

    return stations


def fetch_normalized_observations():
    """取得並標準化 CWA 資料，不寫入資料庫。"""

    load_dotenv(ENV_PATH, override=False)

    api_key = os.getenv("CWA_API_KEY")

    if not api_key:
        raise CWAError("缺少 CWA_API_KEY 設定")

    stations = fetch_stations(api_key)

    # 整批資料共用同一個擷取時間。
    fetched_at = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    observations = []

    for station in stations:
        if not isinstance(station, dict):
            raise CWAError("測站資料不是預期的 dict")

        observation = normalize_station(station, fetched_at)

        # 這三個欄位是資料表要求的必要文字欄位。
        required_fields = (
            "station_id",
            "station_name",
            "observed_at",
        )

        for field in required_fields:
            value = observation[field]

            if not isinstance(value, str) or not value.strip():
                raise CWAError(
                    f"測站缺少有效的必要欄位：{field}"
                )

        observations.append(observation)

    if not observations:
        raise CWAError("沒有可用的標準化測站資料")

    return observations


def main():
    try:
        observations = fetch_normalized_observations()
    except CWAError as error:
        print("CWA 取得失敗：", error)
        raise SystemExit(1) from None

    database_count = save_observations_to_sqlite(observations)

    print("本機資料庫總筆數：", database_count)


if __name__ == "__main__":
    main()
