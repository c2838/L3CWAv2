from http.server import HTTPServer
from urllib.parse import parse_qs, urlsplit

from api.health import handler as HealthHandler
from weather_service import get_observations_payload


class handler(HealthHandler):
    def log_request(self, code="-", size="-"):
        # 只記錄狀態碼，避免記錄完整 query string。
        print("HTTP status:", code)

    def do_GET(self):
        url = urlsplit(self.path)

        if url.path != "/api/observations":
            super().do_GET()
            return

        query = parse_qs(
            url.query,
            keep_blank_values=True,
        )

        allowed_parameters = {"county_name", "station_id"}

        # 只接受已定義、單一且非空白的篩選值。
        invalid_query = any(
            name not in allowed_parameters
            or len(values) != 1
            or not values[0].strip()
            for name, values in query.items()
        )

        if invalid_query:
            self.send_json(
                400,
                {
                    "error": {
                        "code": "INVALID_QUERY",
                        "message": "請提供有效的 county_name 或 station_id",
                    }
                },
            )
            return

        filters = {
            name: values[0].strip()
            for name, values in query.items()
        }

        try:
            payload = get_observations_payload(**filters)
        except Exception as error:
            print("資料查詢失敗：", type(error).__name__)

            self.send_json(
                503,
                {
                    "error": {
                        "code": "DATABASE_UNAVAILABLE",
                        "message": "資料暫時無法讀取，請稍後再試",
                    }
                },
            )
            return

        self.send_json(
            200,
            payload,
            cache_control="public, max-age=0, must-revalidate",
            extra_headers={
                "Vercel-CDN-Cache-Control": "max-age=60",
            },
        )


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8000), handler) as server:
        print("API 已啟動：http://127.0.0.1:8000/api/observations")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
