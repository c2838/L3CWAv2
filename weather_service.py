from fetch_cwa import CWAError, fetch_normalized_observations
from turso_db import (
    get_latest_observations,
    save_observations as save_observations_to_turso,
)


def get_observations_payload(county_name=None, station_id=None):
    """查詢 Turso，組成共用的資料回應。"""

    observations = get_latest_observations(
        county_name=county_name,
        station_id=station_id,
    )

    return {
        "data": observations,
        "meta": {
            "count": len(observations),
            "latest_observed_at": max(
                (row["observed_at"] for row in observations),
                default=None,
            ),
            "latest_fetched_at": max(
                (row["fetched_at"] for row in observations),
                default=None,
            ),
        },
    }


def refresh_turso_observations():
    """取得最新 CWA 資料並寫入 Turso，回傳更新摘要。"""

    observations = fetch_normalized_observations()

    database_count = save_observations_to_turso(observations)

    return {
        "processed_count": len(observations),
        "database_count": database_count,
        "fetched_at": observations[0]["fetched_at"],
    }


def refresh_and_get_observations_payload():
    """更新後回傳資料；CWA 失敗時回傳 Turso 既有資料。"""

    try:
        summary = refresh_turso_observations()
    except CWAError:
        payload = get_observations_payload()

        # 沒有既有資料可回退時，將 CWAError 往上傳遞。
        if not payload["data"]:
            raise

        payload["meta"]["refresh"] = {
            "status": "failed",
        }

        payload["warning"] = {
            "code": "CWA_UNAVAILABLE",
            "message": "更新失敗，目前顯示最後一次成功取得的資料",
        }

        return payload

    payload = get_observations_payload()

    payload["meta"]["refresh"] = {
        "status": "succeeded",
        **summary,
    }

    return payload
