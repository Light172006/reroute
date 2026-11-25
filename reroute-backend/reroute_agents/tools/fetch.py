"""Web Page Fetcher tool with SSRF protection, size caps, and HTML text extraction."""

from __future__ import annotations

import html
import ipaddress
import logging
import re
import socket
import urllib.parse
from typing import Any

from langchain_core.tools import BaseTool, tool

from reroute_agents.config import settings

logger = logging.getLogger(__name__)

# Regex to strip control characters (except common whitespace \n, \r, \t)
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_BOILERPLATE_RE = re.compile(r"<(nav|header|footer|aside|form)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)


def is_ssrf_safe_url(url: str) -> tuple[bool, str]:
    """Validate that a URL does not target localhost, private IPs, or internal network ranges.

    Returns (is_safe, error_or_reason).
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported scheme: '{scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL contains no hostname."

    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "localhost.localdomain", "127.0.0.1", "::1", "0.0.0.0"):
        return False, f"SSRF Protection: Access to localhost ('{hostname}') is blocked."

    # Resolve IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        return False, f"DNS resolution failed for host '{hostname}': {e}"

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Invalid resolved IP '{ip_str}'"

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"SSRF Protection: Host '{hostname}' resolved to prohibited IP '{ip}'."

    return True, "OK"


def _strip_html_to_text(raw_html: str) -> str:
    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw_html)
    cleaned = _HTML_TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = _CONTROL_CHAR_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_extracted_text(raw_html: str, max_bytes: int = 51200) -> str:
    """Strip scripts, layout chrome, and HTML tags while preserving article text."""
    stripped_boilerplate = _BOILERPLATE_RE.sub(" ", _SCRIPT_STYLE_RE.sub(" ", raw_html))
    cleaned = _strip_html_to_text(stripped_boilerplate)
    # Fall back if stripping <header>/<nav>/<form> removed the main body on unusual layouts
    if len(cleaned) < 200:
        cleaned = _strip_html_to_text(raw_html)
    if len(cleaned.encode("utf-8")) > max_bytes:
        cleaned = cleaned[:max_bytes] + "... [Truncated at 50KB limit]"
    return cleaned


_MOCK_PAGE_CONTENTS: dict[str, str] = {
    "tawang": "Tawang Monastery is perched at 3,000 meters in the Eastern Himalayas. Open daily 7:00 AM to 5:00 PM. Entry fee is INR 50. Visitors must carry an Inner Line Permit (ILP). The monastery houses over 400 monks and sacred Tibetan scriptures. Key nearby sites include Urgelling Monastery and craft centres.",
    "sela": "Sela Pass stands at 4,170m above sea level connecting Tawang with Tezpur. Open 6:00 AM to 4:00 PM weather permitting. Heavy snowfall causes winter closures between December and February. Free public entry. Nearby is Sela Lake and the army war memorial.",
    "jaswant": "Jaswant Garh War Memorial honors Rifleman Jaswant Singh Rawat. Located at 3,000m along NH 13. Open 24 hours daily. Free entry. The Indian Army serves free hot tea to travelers passing through.",
    "sangetsar": "Sangetsar Lake (Madhuri Lake) sits at 3,700m near the China border. Open 8:00 AM to 3:00 PM. Entry fee INR 100 per vehicle. Requires special military permit obtained from the DC office in Tawang.",
    "ziro": "Ziro Valley is located in Lower Subansiri district at 1,500m altitude. Home to the Apatani community. Famous for Hong Village, Tarin fish farm, and pine groves. Open year-round. Average homestay cost INR 1,500 per night.",
    "mg-marg": "MG Marg in Gangtok is an open-air pedestrian shopping street open 9:00 AM to 9:00 PM. Free entry. Ideal for local food, momos, and traditional Sikkimese handicrafts.",
    "rumtek": "Rumtek Monastery is located 24 km from Gangtok at 1,500m. Open 8:00 AM to 6:00 PM. Entry fee INR 20. Houses sacred Buddhist relics and the Golden Stupa of the 16th Karmapa.",
    "gurudongmar": "Gurudongmar Lake in North Sikkim is situated at 5,430m. Open 6:00 AM to 1:00 PM due to severe afternoon winds. Restricted to Indian nationals with permit. Free entry.",
    "tiger-hill": "Tiger Hill Darjeeling stands at 2,590m. Open 4:00 AM to 6:00 PM for sunrise viewings. Observatory ticket is INR 100. Best sunrise view of Mount Kanchenjunga.",
    "living-root": "Nongriat Double Decker Living Root Bridge in Cherrapunji. Open 6:00 AM to 5:00 PM. Guide fee INR 500, community conservation fee INR 50. Involves 3,500 stone steps descent.",
}


class WebFetcher:
    """Safe page fetcher enforcing SSRF defense, timeouts, and text extraction."""

    def __init__(self, timeout_sec: float | None = None, max_bytes: int | None = None) -> None:
        self.timeout_sec = timeout_sec or settings.web_fetch_timeout_sec
        self.max_bytes = max_bytes or settings.web_max_text_bytes

    async def fetch(self, url: str) -> dict[str, Any]:
        # 1. SSRF check
        is_safe, reason = is_ssrf_safe_url(url)
        if not is_safe:
            logger.warning("Blocked unsafe URL '%s': %s", url, reason)
            return {
                "ok": False,
                "url": url,
                "error": reason,
                "status_code": 403,
                "text": "",
            }

        # 2. Mock fallback check
        if settings.mock_tools:
            url_lower = url.lower()
            for key, content in _MOCK_PAGE_CONTENTS.items():
                if key in url_lower:
                    return {
                        "ok": True,
                        "url": url,
                        "text": content,
                        "size_bytes": len(content),
                        "status_code": 200,
                    }
            default_content = f"Travel guide overview for {url}. Features scenic landscapes, cultural heritage, and traveler facilities."
            return {
                "ok": True,
                "url": url,
                "text": default_content,
                "size_bytes": len(default_content),
                "status_code": 200,
            }

        # 3. Live HTTP request
        import httpx

        headers = {
            "User-Agent": "RerouteAgent/1.0 (travel-planner; https://reroute.travel)"
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec, headers=headers) as client:
                res = await client.get(url, follow_redirects=True)
                res.raise_for_status()
                clean_text = sanitize_extracted_text(res.text, max_bytes=self.max_bytes)
                return {
                    "ok": True,
                    "url": str(res.url),
                    "text": clean_text,
                    "size_bytes": len(clean_text),
                    "status_code": res.status_code,
                }
        except Exception as exc:
            logger.warning("Fetch failed for '%s': %s", url, exc)
            return {
                "ok": False,
                "url": url,
                "error": str(exc),
                "text": "",
            }


def create_web_fetch_tool(fetcher: WebFetcher | None = None) -> BaseTool:
    """Create LangChain BaseTool for web page fetching."""
    active_fetcher = fetcher or WebFetcher()

    @tool
    async def web_fetch(url: str) -> dict[str, Any]:
        """Fetch content from a web page URL safely with SSRF defense and text extraction."""
        return await active_fetcher.fetch(url)

    return web_fetch
