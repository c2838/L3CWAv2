import os
import secrets
from http.server import HTTPServer
from urllib.parse import urlsplit

from dotenv import load_dotenv

from api.observations import handler as ObservationsHandler
from fetch_cwa import CWAError, ENV_PATH
from weather_service import refresh_and_get_observations_payload


class handler(ObservationsHandler):
    def send_api_error(
        self,
        status_code,
        code,
        message,
        extra_headers=None,
    ):
        self.send_json(
            status_code,
            {
                "error": {
                    "code": code,
                    "message": message,
                }
            },
            extra_headers=extra_headers,
        )

    def do_GET(self):
        if urlsplit(self.path).path == "/api/refresh":
            self.send_api_error(
                405,
                "METHOD_NOT_ALLOWED",
                "請使用 POST 執行更新",
                extra_headers={"Allow": "POST"},
            )
            return

        super().do_GET()

    def do_POST(self):
        # 回應後關閉連線，不繼續處理未讀取的 request body。
        self.close_connection = True

        url = urlsplit(self.path)

        if url.path != "/api/refresh":
            self.send_api_error(
                404,
                "NOT_FOUND",
                "找不到此 API",
            )
            return

        load_dotenv(ENV_PATH, override=False)

        expected_token = os.getenv("REFRESH_API_TOKEN")

        if not expected_token or not expected_token.strip():
            self.send_api_error(
                503,
                "REFRESH_DISABLED",
                "更新功能尚未設定",
            )
            return

        authorization_headers = self.headers.get_all(
            "Authorization", []
        )

        authorized = (
            len(authorization_headers) == 1
            and secrets.compare_digest(
                authorization_headers[0].encode("utf-8"),
                f"Bearer {expected_token}".encode("utf-8"),
            )
        )

        if not authorized:
            self.send_api_error(
                401,
                "UNAUTHORIZED",
                "更新授權失敗",
                extra_headers={
                    "WWW-Authenticate": 'Bearer realm="weather-refresh"',
                },
            )
            return

        # 更新整批測站資料，不接受 query 或 request body。
        content_lengths = self.headers.get_all("Content-Length", [])

        if (
            url.query
            or self.headers.get("Transfer-Encoding") is not None
            or len(content_lengths) > 1
            or (content_lengths and content_lengths[0] != "0")
        ):
            self.send_api_error(
                400,
                "INVALID_REQUEST",
                "此更新 API 不接受參數或內容",
            )
            return

        try:
            payload = refresh_and_get_observations_payload()
        except CWAError:
            self.send_api_error(
                503,
                "CWA_UNAVAILABLE",
                "更新失敗，目前沒有可用的既有資料",
            )
            return
        except Exception as error:
            print("資料更新失敗：", type(error).__name__)

            self.send_api_error(
                503,
                "DATABASE_UNAVAILABLE",
                "資料庫操作失敗，請稍後再試",
            )
            return

        self.send_json(200, payload)


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8000), handler) as server:
        print("API 已啟動：http://127.0.0.1:8000")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
