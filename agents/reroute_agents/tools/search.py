"""Web Search tool abstraction: Tavily, DuckDuckGo, and deterministic Mock."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import BaseTool, tool

from reroute_agents.config import settings

logger = logging.getLogger(__name__)

# Pre-recorded realistic search responses for Northeast India regions
_MOCK_SEARCH_DATA: dict[str, list[dict[str, str]]] = {
    "arunachal": [
        {
            "title": "Tawang Monastery - Galden Namgey Lhatse",
            "url": "https://arunachaltourism.com/destinations/tawang-monastery",
            "snippet": "Largest monastery in India and second largest in the world, founded by Merak Lama Lodre Gyamtso in 1680. Located at an altitude of 3,000m overlooking Tawang valley.",
        },
        {
            "title": "Sela Pass and Sela Lake - Gateway to Tawang",
            "url": "https://arunachaltourism.com/destinations/sela-pass",
            "snippet": "High-altitude mountain pass at 4,170m (13,700 ft) connecting Tawang to Tezpur. Known for dramatic snow landscapes and sacred paradise lake.",
        },
        {
            "title": "Jaswant Garh War Memorial",
            "url": "https://arunachaltourism.com/destinations/jaswant-garh",
            "snippet": "Memorial honoring Rifleman Jaswant Singh Rawat of the 4th Garhwal Rifles who fought during the 1962 Sino-Indian War. Located near Sela Pass.",
        },
        {
            "title": "Sangetsar Tso (Madhuri Lake)",
            "url": "https://arunachaltourism.com/destinations/sangetsar-lake",
            "snippet": "Scenic high-altitude lake formed by an earthquake in 1950, surrounded by snow-capped mountains and dead tree trunks standing in the water.",
        },
        {
            "title": "Ziro Valley - UNESCO World Heritage Tentative Site",
            "url": "https://arunachaltourism.com/destinations/ziro-valley",
            "snippet": "Picturesque valley home to the Apatani tribe, celebrated for sustainable wet-rice cultivation, fish farming, and unique pine groves.",
        },
        {
            "title": "Dirang Dzong & Heritage Monpa Settlement",
            "url": "https://arunachaltourism.com/destinations/dirang-dzong",
            "snippet": "Centuries-old tribal fortress settlement constructed in stone and wood along the Kameng River valley in West Kameng.",
        },
    ],
    "sikkim": [
        {
            "title": "MG Marg Gangtok - Pedestrian Promenade",
            "url": "https://sikkimtourism.gov.in/attractions/mg-marg",
            "snippet": "Lively vehicle-free pedestrian street and central gathering point of Gangtok, lined with cafes, local handicraft shops, and vibrant flowers.",
        },
        {
            "title": "Rumtek Monastery - Dharma Chakra Centre",
            "url": "https://sikkimtourism.gov.in/attractions/rumtek",
            "snippet": "Seat of the Karma Kagyu lineage in exile, perched on a hill facing Gangtok. Features intricate murals, golden stupas, and monastic chanting halls.",
        },
        {
            "title": "Gurudongmar Lake - Sacred High Altitude Lake",
            "url": "https://sikkimtourism.gov.in/attractions/gurudongmar",
            "snippet": "One of the highest lakes in the world at 5,430m (17,800 ft) in North Sikkim, sacred to Buddhists and Sikhs, offering breathtaking mountain vistas.",
        },
        {
            "title": "Yumthang Valley - Valley of Flowers",
            "url": "https://sikkimtourism.gov.in/attractions/yumthang",
            "snippet": "Alpine flower sanctuary in North Sikkim situated at 3,564m, featuring rhododendron sanctuaries, hot springs, and grazing yaks.",
        },
        {
            "title": "Nathula Pass - Historic Indo-China Border Post",
            "url": "https://sikkimtourism.gov.in/attractions/nathula",
            "snippet": "Historic mountain pass on the Old Silk Route at 4,310m connecting Sikkim to China's Tibet Autonomous Region. Special permits required.",
        },
        {
            "title": "Tsomgo Lake (Changu Lake)",
            "url": "https://sikkimtourism.gov.in/attractions/tsomgo",
            "snippet": "Glacial lake at 3,753m surrounded by rugged alpine slopes, known for reflection of changing seasons on its surface.",
        },
    ],
    "darjeeling": [
        {
            "title": "Tiger Hill Sunrise - Kanchenjunga Panorama",
            "url": "https://wbtourism.gov.in/attractions/tiger-hill",
            "snippet": "Renowned viewpoint situated at 2,590m offering iconic panoramic views of Mount Everest and Mount Kanchenjunga at sunrise.",
        },
        {
            "title": "Batasia Loop & Gorkha War Memorial",
            "url": "https://wbtourism.gov.in/attractions/batasia-loop",
            "snippet": "Famous spiral railway loop engineered for the Darjeeling Himalayan Railway toy train with manicured gardens and War Memorial.",
        },
        {
            "title": "Happy Valley Tea Estate",
            "url": "https://wbtourism.gov.in/attractions/happy-valley",
            "snippet": "Historic tea estate established in 1854 producing premier orthodox Darjeeling black and green teas overlooking the rolling hills.",
        },
        {
            "title": "Himalayan Mountaineering Institute & Padmaja Naidu Zoo",
            "url": "https://wbtourism.gov.in/attractions/hmi-zoo",
            "snippet": "Pioneering mountaineering training institute founded by Tenzing Norgay, co-located with high-altitude zoo breeding Red Pandas and Snow Leopards.",
        },
    ],
    "meghalaya": [
        {
            "title": "Double Decker Living Root Bridge - Nongriat",
            "url": "https://meghalayatourism.in/attractions/nongriat-root-bridge",
            "snippet": "Biological architecture marvel engineered by the indigenous Khasi tribe across centuries using Ficus elastica roots in the lush jungle.",
        },
        {
            "title": "Nohkalikai Falls - Tallest Plunge Waterfall in India",
            "url": "https://meghalayatourism.in/attractions/nohkalikai",
            "snippet": "Majestic waterfall plunging 340m from the forested plateau into a turquoise pool near Cherrapunji (Sohra).",
        },
        {
            "title": "Dawki River (Umngot) - Crystal Clear Boating",
            "url": "https://meghalayatourism.in/attractions/dawki-umngot",
            "snippet": "Pristine emerald river on the Indo-Bangladesh border famed for water so clear that wooden boats appear to float on air.",
        },
        {
            "title": "Mawlynnong - Cleanest Village in Asia",
            "url": "https://meghalayatourism.in/attractions/mawlynnong",
            "snippet": "Pristine community village celebrated for floral pathways, bamboo dustbins, sustainable living, and single living root bridge nearby.",
        },
    ],
}


class SearchProvider(ABC):
    """Abstract interface for web search providers."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        """Execute a search query and return a list of title/url/snippet dicts."""


class MockSearchProvider(SearchProvider):
    """Deterministic mock provider returning realistic regional travel search results."""

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        q_lower = query.lower()
        matched: list[dict[str, str]] = []

        # Check regional matches
        if any(w in q_lower for w in ["arunachal", "tawang", "bomdila", "ziro", "dirang"]):
            matched = _MOCK_SEARCH_DATA["arunachal"]
        elif any(w in q_lower for w in ["sikkim", "gangtok", "lachung", "lachen", "pelling"]):
            matched = _MOCK_SEARCH_DATA["sikkim"]
        elif any(w in q_lower for w in ["darjeeling", "kurseong", "kalimpong", "ghoom"]):
            matched = _MOCK_SEARCH_DATA["darjeeling"]
        elif any(w in q_lower for w in ["meghalaya", "shillong", "cherrapunji", "sohra", "dawki"]):
            matched = _MOCK_SEARCH_DATA["meghalaya"]
        else:
            # Generic deterministic results for any other query
            clean_term = query.replace("places to visit in", "").replace("attractions in", "").strip()
            matched = [
                {
                    "title": f"Top Places to Explore in {clean_term.title()}",
                    "url": f"https://travelwiki.org/{clean_term.lower().replace(' ', '-')}/top-attractions",
                    "snippet": f"Comprehensive guide to key cultural sights, nature spots, and scenic destinations across {clean_term.title()}.",
                },
                {
                    "title": f"Historical and Heritage Walk of {clean_term.title()}",
                    "url": f"https://heritagetravel.org/{clean_term.lower().replace(' ', '-')}/heritage-walk",
                    "snippet": f"Discover famous architectural landmarks, regional museums, and vibrant local markets in {clean_term.title()}.",
                },
                {
                    "title": f"Scenic Mountain and Nature Trails near {clean_term.title()}",
                    "url": f"https://natureexplore.org/{clean_term.lower().replace(' ', '-')}/nature-trails",
                    "snippet": f"A curated itinerary of outdoor viewpoints, tranquil lakes, and photography locations around {clean_term.title()}.",
                },
            ]

        return matched[:max_results]


class TavilySearchProvider(SearchProvider):
    """Live Tavily API search provider."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.tavily_api_key

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        if not self.api_key:
            logger.warning("No Tavily API key configured; falling back to MockSearchProvider")
            return await MockSearchProvider().search(query, max_results=max_results)

        import httpx

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_raw_content": False,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                results = []
                for item in data.get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                        }
                    )
                return results[:max_results]
        except Exception as e:
            logger.warning("Tavily search failed (%s); falling back to mock results", e)
            return await MockSearchProvider().search(query, max_results=max_results)


class DuckDuckGoSearchProvider(SearchProvider):
    """DuckDuckGo search provider (free, no key required)."""

    async def search(self, query: str, max_results: int = 5) -> list[dict[str, str]]:
        import httpx

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                res = await client.post(url, data={"q": query})
                res.raise_for_status()
                # Parse minimal HTML snippets or fallback
                from html.parser import HTMLParser

                class DDGParser(HTMLParser):
                    def __init__(self) -> None:
                        super().__init__()
                        self.results: list[dict[str, str]] = []
                        self.current_title = ""
                        self.current_url = ""
                        self.current_snippet = ""
                        self.in_title = False
                        self.in_snippet = False

                    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                        attrs_dict = dict(attrs)
                        class_attr = attrs_dict.get("class") or ""
                        if tag == "a" and "result__snippet" in class_attr:
                            self.in_snippet = True
                        elif tag == "a" and "result__url" in class_attr:
                            self.current_url = attrs_dict.get("href") or ""

                    def handle_endtag(self, tag: str) -> None:
                        if self.in_snippet and tag == "a":
                            self.in_snippet = False
                            if self.current_snippet and self.current_url:
                                self.results.append({
                                    "title": self.current_title or "Search Result",
                                    "url": self.current_url,
                                    "snippet": self.current_snippet,
                                })
                                self.current_title = ""
                                self.current_url = ""
                                self.current_snippet = ""

                    def handle_data(self, data: str) -> None:
                        if self.in_snippet:
                            self.current_snippet += data.strip() + " "

                parser = DDGParser()
                parser.feed(res.text)
                if parser.results:
                    return parser.results[:max_results]
        except Exception as e:
            logger.warning("DuckDuckGo search failed (%s); falling back to mock results", e)

        return await MockSearchProvider().search(query, max_results=max_results)


def get_search_provider(override_name: str | None = None) -> SearchProvider:
    """Factory creating configured SearchProvider."""
    provider_name = (override_name or settings.search_provider).lower().strip()
    if settings.mock_tools or provider_name == "mock":
        return MockSearchProvider()
    if provider_name == "tavily":
        return TavilySearchProvider()
    if provider_name == "ddg":
        return DuckDuckGoSearchProvider()
    return MockSearchProvider()


def create_web_search_tool(provider: SearchProvider | None = None) -> BaseTool:
    """Create LangChain BaseTool for web search."""
    active_provider = provider or get_search_provider()

    @tool
    async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
        """Search the web for travel destinations, sights, cultural spots, and activities."""
        try:
            results = await active_provider.search(query=query, max_results=max_results)
            return {"ok": True, "query": query, "results": results, "count": len(results)}
        except Exception as exc:
            return {"ok": False, "query": query, "error": str(exc), "results": []}

    return web_search
