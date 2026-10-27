"""Exact-allowlist fetcher. No recursive crawl, redirect expansion, or access bypass."""

import asyncio
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

from app.schemas import Source
from app.sources import require_allowed

USER_AGENT = (
    "PlacidWayAssessmentBot/1.0 (+https://github.com/syedowaisalishah/placidway-ai-knowledge-assistant)"
)
ROBOTS_URL = "https://www.placidway.com/robots.txt"


class CrawlError(RuntimeError):
    pass


class ControlledCrawler:
    def __init__(self, sources: list[Source], client: httpx.AsyncClient | None = None):
        self.sources = sources
        self.client = client or httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=False
        )
        self.owns_client = client is None
        self.robots: RobotFileParser | None = None
        self.delay = 1.1
        self.last_request = 0.0

    async def close(self):
        if self.owns_client:
            await self.client.aclose()

    async def _request(self, url: str) -> httpx.Response:
        await asyncio.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        async with self.client.stream(
            "GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=False
        ) as response:
            content = bytearray()
            async for part in response.aiter_bytes():
                content.extend(part)
                if len(content) > 8_000_000:
                    raise CrawlError("Source exceeds document size limit.")
            # aiter_bytes() has already decoded Content-Encoding. Reusing the
            # original encoding header would make the new Response decompress
            # the plain bytes a second time (observed on live robots.txt).
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(
                response.status_code,
                headers=headers,
                content=bytes(content),
                request=response.request,
            )

    async def read_robots(self):
        response = await self._request(ROBOTS_URL)
        # Fail closed on unavailable permissions. A 404 is an explicit absent policy.
        if response.status_code == 404:
            text = "User-agent: *\nAllow: /"
        elif response.status_code == 200:
            text = response.text
        else:
            raise CrawlError(f"robots.txt unavailable: HTTP {response.status_code}")
        self.robots = RobotFileParser(ROBOTS_URL)
        self.robots.parse(text.splitlines())
        self.delay = max(
            1.1,
            self.robots.crawl_delay(USER_AGENT) or self.robots.crawl_delay("*") or 0,
        )
        return text

    async def fetch(self, source: Source) -> str:
        require_allowed(source.url, self.sources)
        if self.robots is None:
            await self.read_robots()
        url = source.url
        for attempt in range(4):
            if not self.robots.can_fetch(USER_AGENT, url):
                raise CrawlError("Disallowed by robots.txt")
            response = await self._request(url)
            if response.is_redirect:
                target = urljoin(url, response.headers.get("location", ""))
                require_allowed(target, self.sources)
                # A source must not silently become a different approved page.
                if target != source.url:
                    raise CrawlError(
                        "Redirect changes source identity; verify configuration first."
                    )
                url = target
                continue
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                retry = response.headers.get("retry-after", str(2 ** (attempt + 1)))
                try:
                    wait = float(retry)
                except ValueError:
                    wait = (
                        parsedate_to_datetime(retry) - datetime.now(UTC)
                    ).total_seconds()
                if wait > 120:
                    raise CrawlError(
                        "Retry-After exceeds this crawl window; retry later."
                    )
                await asyncio.sleep(max(0, wait))
                continue
            if response.status_code != 200:
                raise CrawlError(f"HTTP {response.status_code}; no bypass attempted")
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise CrawlError("Source did not return HTML.")
            if len(response.content) > 8_000_000:
                raise CrawlError("Source exceeds document size limit.")
            return response.text
        raise CrawlError("Fetch retry limit reached.")
