from urllib.parse import urlparse
import asyncio

import requests
import httpx

from prototype import worker_secure


def reset_worker_state() -> None:
    worker_secure.slices.clear()
    worker_secure.keys.clear()
    with worker_secure.metrics_lock:
        for key in worker_secure.metrics:
            worker_secure.metrics[key] = 0


def make_worker_client() -> httpx.Client:
    reset_worker_state()
    transport = httpx.ASGITransport(app=worker_secure.app)
    return httpx.Client(transport=transport, base_url="http://worker-inproc")


class _InProcessResponse:
    def __init__(self, response, url: str):
        self._response = response
        self.status_code = response.status_code
        self.text = response.text
        self.url = url

    def json(self):
        return self._response.json()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} error for {self.url}",
                response=self._response,
            )


class InProcessWorkerTransport:
    def __init__(self, client: httpx.Client):
        self.client = client

    def post(self, url, json=None, timeout=None, **kwargs):
        path = urlparse(url).path or "/"
        async def _post():
            async with httpx.AsyncClient(transport=self.client._transport, base_url=self.client.base_url) as async_client:
                return await async_client.post(path, json=json)

        response = asyncio.run(_post())
        return _InProcessResponse(response, url)