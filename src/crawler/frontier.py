# src/crawler/frontier.py
import json
import time
import redis
import urllib.parse
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)
FRONTIER_KEY = "rfp_frontier"
SEEN_KEY = "rfp_seen"

class Frontier:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        # decode_responses=True makes client return strings instead of bytes
        self.client = redis.from_url(redis_url, decode_responses=True)

    def add(self, url: str, priority: int = 5, depth: int = 0, meta: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a URL to the frontier if not already seen.
        Returns True if added, False if skipped.
        Raises ValueError for invalid URLs.
        """
        if isinstance(url, dict):
            # try to extract correct fields and continue
            seed = url
            # if seed has a nested 'url' take it; else error below
            url = seed.get("url")
            # merge meta/depth/priority if provided in seed
            if meta is None:
                meta = seed.get("meta", {}) or {}
            priority = seed.get("priority", priority)
            depth = seed.get("depth", depth)
        # Defensive type checks
        if url is None:
            raise ValueError("None passed as url to Frontier.add")
        if not isinstance(url, str):
            raise ValueError(f"Expected url to be str, got {type(url)!r}: {url}")

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL passed to Frontier.add: {url}")

        # Already seen?
        try:
            if self.client.sismember(SEEN_KEY, url):
                return False
        except Exception as e:
            logger.exception("Redis sismember failed for url %s: %s", url, e)
            # fall through; we may still try to add

        # build payload as a JSON string — member must be a string (not a dict)
        payload_obj = {"url": url, "priority": priority, "depth": depth, "meta": meta or {}, "ts": time.time()}
        payload = json.dumps(payload_obj, ensure_ascii=False)

        # debug log
        logger.debug("Frontier.add payload length=%d, priority=%s for %s", len(payload), priority, url)

        # zadd: mapping {member: score}. Member must be a string (or bytes)
        try:
            # Use float(priority) as score; in case of older redis client that expects bytes,
            # decode_responses=True will return strings and this should be fine.
            mapping = {payload: float(priority)}
            self.client.zadd(FRONTIER_KEY, mapping)
            return True
        except Exception as e:
            logger.exception("Redis zadd failed for payload (type=%s): %s", type(payload), e)
            raise

    def pop(self) -> Optional[Dict]:
        items = self.client.zrevrange(FRONTIER_KEY, 0, 0)
        if not items:
            return None
        raw = items[0]
        removed = self.client.zrem(FRONTIER_KEY, raw)
        if removed:
            try:
                return json.loads(raw)
            except Exception:
                logger.exception("Failed to json.loads frontier raw item: %s", raw[:200])
                return None
        return None

    def mark_seen(self, url: str):
        if url:
            try:
                self.client.sadd(SEEN_KEY, url)
            except Exception:
                logger.exception("Failed to mark seen for %s", url)

    def size(self) -> int:
        try:
            return self.client.zcard(FRONTIER_KEY)
        except Exception:
            logger.exception("Failed to get frontier size")
            return 0
