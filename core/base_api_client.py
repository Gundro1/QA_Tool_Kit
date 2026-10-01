"""
Generic Base API Client — reusable for ANY REST API.

Usage:
    class MyApiClient(BaseApiClient):
        def __init__(self):
            super().__init__("https://api.example.com")

        def get_users(self, limit=10):
            return self.get("/users", params={"limit": limit})

        def create_user(self, data):
            return self.post("/users", json_body=data)

    client = MyApiClient()
    response = client.get_users(limit=5)
    print(response.status, response.json)
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ApiResponse:
    """Typed API response — no raw dicts floating around."""
    status: int
    json: Any = None
    text: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    url: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def __repr__(self):
        return f"ApiResponse(status={self.status}, ok={self.ok}, url='{self.url}')"


class BaseApiClient:
    """
    Abstract base API client using only stdlib (no requests dependency).
    Extend this for any API you need to test against.

    Features:
    - Typed responses (ApiResponse)
    - Automatic JSON parsing
    - Timing (elapsed_ms)
    - Retries with backoff
    - Custom headers per instance
    - No external dependencies
    """

    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30, retries: int = 0):
        self.base_url = base_url.rstrip("/")
        self.default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **(headers or {})
        }
        self.timeout = timeout
        self.retries = retries

    def _request(self, method: str, path: str, params: Optional[Dict] = None,
                 json_body: Any = None, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """Core request method with retries and timing."""
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{query}"

        req_headers = {**self.default_headers, **(headers or {})}
        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
                start = time.perf_counter()
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    elapsed = (time.perf_counter() - start) * 1000
                    text = resp.read().decode("utf-8", errors="replace")
                    resp_headers = {k: v for k, v in resp.getheaders()}
                    try:
                        parsed = json.loads(text) if text.strip() else None
                    except json.JSONDecodeError:
                        parsed = None
                    return ApiResponse(
                        status=resp.status,
                        json=parsed,
                        text=text,
                        headers=resp_headers,
                        elapsed_ms=round(elapsed, 2),
                        url=url,
                    )
            except urllib.error.HTTPError as e:
                elapsed = (time.perf_counter() - start) * 1000 if 'start' in dir() else 0
                text = e.read().decode("utf-8", errors="replace") if e.fp else ""
                try:
                    parsed = json.loads(text) if text.strip() else None
                except json.JSONDecodeError:
                    parsed = None
                last_error = ApiResponse(
                    status=e.code,
                    json=parsed,
                    text=text,
                    headers={},
                    elapsed_ms=round(elapsed, 2),
                    url=url,
                    error=str(e),
                )
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                return last_error
            except Exception as e:
                last_error = ApiResponse(status=0, url=url, error=str(e))
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
                    continue
                return last_error

        return last_error or ApiResponse(status=0, url=url, error="Max retries exceeded")

    # ── Convenience methods ───────────────────────────────────────────

    def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> ApiResponse:
        return self._request("GET", path, params=params, **kwargs)

    def post(self, path: str, json_body: Any = None, **kwargs) -> ApiResponse:
        return self._request("POST", path, json_body=json_body, **kwargs)

    def put(self, path: str, json_body: Any = None, **kwargs) -> ApiResponse:
        return self._request("PUT", path, json_body=json_body, **kwargs)

    def patch(self, path: str, json_body: Any = None, **kwargs) -> ApiResponse:
        return self._request("PATCH", path, json_body=json_body, **kwargs)

    def delete(self, path: str, **kwargs) -> ApiResponse:
        return self._request("DELETE", path, **kwargs)

    # ── Health check ──────────────────────────────────────────────────

    def health(self, path: str = "/") -> bool:
        """Quick health check — returns True if status is 2xx."""
        return self.get(path).ok
