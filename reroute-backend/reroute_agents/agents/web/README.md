# Web Research Agent

## Purpose
The Web Research Agent autonomously discovers, scrapes, and geocodes travel destinations and attractions from the open web. It transforms unstructured online information into verified, structured `ResearchResult` payloads.

## Architecture
- **Framework:** LangGraph `StateGraph`
- **Graph Nodes:**
  1. `search`: Formulates queries based on destination and vibe tags; queries search providers.
  2. `fetch`: Safely fetches page contents with SSRF protection and HTML text extraction.
  3. `extract`: Extracts factual place properties (name, category, cost, hours) inside `<untrusted_web_content>` tags.
  4. `geocode`: Verifies geographic coordinates against regional bounding boxes.

## Inputs and Outputs
- **Input:**
  - `destination: str`: Target city or region (e.g. "Arunachal Pradesh", "Sikkim")
  - `vibe_tags: list[str]`: User vibe preferences (e.g. `["nature", "culture"]`)
- **Output:**
  - `ResearchResult`: Pydantic model containing:
    - `destination: str`
    - `places: list[PlaceResearchItem]`
    - `source: str` ("web", "seed_fallback", "mock")
    - `fallback: bool`
    - `tool_counts: dict[str, int]`

## Dedicated Tools
The Web Agent is strictly restricted to these dedicated tools:
- `web_search`: Queries configured search provider (`tavily`, `ddg`, or `mock`).
- `web_fetch`: Secure HTTP client enforcing SSRF protection and 50KB size cap.
- `web_geocode`: Nominatim / Mock geocoding service enforcing 1 req/sec rate limit and regional bounding boxes.

## Safety & Invariants
- **Prompt Injection Defense:** Web pages are wrapped in `<untrusted_web_content>` delimiters with explicit instructions to ignore prompt injection commands.
- **SSRF Defense:** Blocks access to private (`10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`), loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and internal hostnames.
- **Budget Limits:** Hard limits of 5 searches, 10 fetches, and 10 geocodes per research run.
- **Fallback Guarantee:** Gracefully falls back to regional seed catalogs if network is unavailable or queries yield 0 results. Never raises uncaught exceptions.
