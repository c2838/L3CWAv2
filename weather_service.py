from fetch_cwa import CWAError, fetch_normalized_observations
from turso_db import (
    get_latest_observations,
    get_refresh_status,
    record_refresh_failure,
    save_observations as save_observations_to_turso,
)


def get_observations_payload(county_name=None, station_id=None):
    """查詢 Turso，組成資料與最近一次更新狀態的回應。"""

    observations = get_latest_observations(
        county_name=county_name,
        station_id=station_id,
    )
    refresh_status = get_refresh_status()

    payload = {
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
            "refresh": refresh_status,
        },
    }

    if refresh_status is not None and refresh_status["status"] == "failed":
        messages = {
            "CWA_UNAVAILABLE": "CWA 更新失敗，目前顯示最後一次保存的資料",
            "DATABASE_UNAVAILABLE": "資料更新失敗，目前顯示最後一次保存的資料",
        }
        payload["warning"] = {
            "code": refresh_status["error_code"],
            "message": messages[refresh_status["error_code"]],
        }

    return payload


def refresh_turso_observations():
    """取得最新 CWA 資料，同時寫入觀測資料與成功狀態。"""

    observations = fetch_normalized_observations()

    database_count = save_observations_to_turso(
        observations,
        record_refresh_success=True,
    )

    return {
        "processed_count": len(observations),
        "database_count": database_count,
        "fetched_at": observations[0]["fetched_at"],
    }


def refresh_and_get_observations_payload(*, return_minimal=False):
    """更新資料；可選擇回傳簡短摘要或完整觀測資料。"""

    try:
        summary = refresh_turso_observations()
    except CWAError:
        record_refresh_failure("CWA_UNAVAILABLE")

        # 排程需要明確的失敗回應，讓 API 回傳 HTTP 503。
        if return_minimal:
            raise

        payload = get_observations_payload()

        # 沒有既有資料可回退時，將原本的 CWAError 往上傳遞。
        if not payload["data"]:
            raise

        return payload

    if return_minimal:
        return {
            "status": "succeeded",
            **summary,
        }

    payload = get_observations_payload()
    payload["meta"]["refresh"].update(summary)
    return payload
