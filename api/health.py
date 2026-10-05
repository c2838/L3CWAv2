import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

class handler(BaseHTTPRequestHandler):
    def send_json(self, status_code, payload, extra_headers=None):
        """將 python data 轉 json，送出 HTTP 回應"""
        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")

        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)

        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """ 處理 GET 請求 """
        path = urlsplit(self.path).path

        if path != "/api/health":
            self.send_json(
                404,
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Not Found Api",
                    }
                }
            )
            return

        self.send_json(
            200,
            {"status": "ok"}
        )


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8000), handler) as server:
        print("API 已啟動：http://127.0.0.1:8000/api/health")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
