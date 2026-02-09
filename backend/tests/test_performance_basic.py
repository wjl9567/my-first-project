"""基础性能：核心接口单次请求响应时间在合理范围内（如 2s 内）。"""
import time
import pytest
from fastapi.testclient import TestClient


def _elapsed(client: TestClient, method: str, url: str, **kwargs) -> float:
    start = time.perf_counter()
    if method == "GET":
        client.get(url, **kwargs)
    else:
        client.post(url, **kwargs)
    return time.perf_counter() - start


@pytest.mark.skip(reason="可选执行，用于观察响应时间趋势")
def test_health_latency(client: TestClient):
    """GET /health 应在 0.5s 内。"""
    t = _elapsed(client, "GET", "/health")
    assert t < 0.5, f"/health 耗时 {t:.3f}s"


def test_health_fast(client: TestClient):
    """GET /health 单次请求在 2s 内（宽松阈值，保证无卡死）。"""
    t = _elapsed(client, "GET", "/health")
    assert t < 2.0, f"/health 耗时 {t:.3f}s，超过 2s"


def test_root_fast(client: TestClient):
    """GET / 单次请求在 2s 内。"""
    t = _elapsed(client, "GET", "/")
    assert t < 2.0, f"/ 耗时 {t:.3f}s"
