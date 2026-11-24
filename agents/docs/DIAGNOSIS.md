# Root Cause Diagnosis: "Same Results for Different Destinations" Bug

**Bug Report**: In the deployed site, choosing "Arunachal Pradesh" and choosing "Sikkim" returned the same places. The system picked from a fixed list instead of researching the chosen destination.

---

## 1. Reproduction and Evidence

We analyzed the end-to-end data flow across `frontend/`, `reroute-backend/`, and `agents/reroute_agents/`. We tested the behavior under CLI `--fake-llm --mock-tools` and under database repository queries.

### Reproduction Command and Results
When querying the place catalog repository with sub-region towns (e.g., `Tawang` in Arunachal Pradesh, or `Gangtok` in Sikkim):
```python
# Query: "Tawang" -> resolve_destination returns "arunachal", but search_places returns 0 places
# Query: "Gangtok" -> resolve_destination returns "north_sikkim", but search_places returns 0 places
```

When 0 candidate places are returned:
1. In `reroute-backend/app/services/agent_repositories.py:L488-L490`:
   ```python
   places = result.scalars().all()
   if not places:
       fallback = await self.db.execute(select(Place).limit(limit))
       places = fallback.scalars().all()
   ```
   The backend catches the empty result and falls back to selecting the first 30 places in the database with **no destination or city filter**. The first 30 places are the Darjeeling seed places.
2. In `frontend/src/mocks/handlers.ts:L471`:
   ```typescript
   this.itineraries[tripId] = {
     trip_id: tripId,
     version: { ... },
     days: JSON.parse(JSON.stringify(SEED_DARJEELING_ITINERARY_V1.days)),
   };
   ```
   When the deployed frontend operates in mock/demo mode (or if backend calls fail), the mock service worker always returns `SEED_DARJEELING_ITINERARY_V1.days` regardless of the requested destination.
3. In `agents/reroute_agents/nodes/planner.py:L61-L62`:
   ```python
   # Fallback generator when candidates list is empty:
   item = DraftItem(
       ...
       title=cand.name if cand else f"Scenic Stop {pos + 1}",
       lat=cand.lat if cand else 27.04,   # Darjeeling latitude!
       lng=cand.lng if cand else 88.26,   # Darjeeling longitude!
   )
   ```
   If candidates is empty, the fallback planner generates generic stops located at Darjeeling's geographic coordinates (27.04, 88.26).

---

## 2. Hypothesis Analysis

| Hypothesis | Verdict | Evidence and Details |
|---|---|---|
| **1. Mock / fake mode in deployed environment** | **TRUE** | `frontend/src/mocks/handlers.ts:L471` explicitly hardcodes `SEED_DARJEELING_ITINERARY_V1.days` whenever the frontend mock service worker is active. |
| **2. Destination resolution discarded & backend unconstrained fallback** | **TRUE** | In `agents/reroute_agents/nodes/researcher.py:L20-L21`, `resolve_destination(spec.destination)` is called but its return value is discarded. Then `catalog_repo.search_places(city=city_query)` fails on sub-destinations like "Tawang" or "Gangtok". In `reroute-backend/app/services/agent_repositories.py:L488-L490`, empty results trigger `select(Place).limit(limit)` with no city filter, returning Darjeeling places for all destinations. |
| **3. Cache key missing destination** | **PARTIAL** | Tool-level caching in `weather.py` and `routing.py` includes coordinates, but the system lacked a dedicated research caching layer keyed by canonical destination and vibe tags. |
| **4. Researcher / planner ignores destination** | **FALSE (with caveat)** | The planner includes `spec.destination` in the prompt, but if candidate places are missing, the deterministic fallback generates stops hardcoded to Darjeeling's coordinates (27.04, 88.26). |
| **5. Static seed catalog is the only source (no web research)** | **TRUE** | Prior to adding the Web Agent, the agent system had zero capability to perform live web search. It only knew the 4 pre-seeded regions in `agents/data/seed/`. Unseeded destinations (e.g. Meghalaya, Manali, Goa) produced zero results. |
| **6. Outside agents/ (Frontend & Backend)** | **TRUE** | Both the frontend MSW mock handler (`handlers.ts:L471`) and backend repository fallback (`agent_repositories.py:L488-L490`) contain hardcoded behaviors that return Darjeeling places. |

---

## 3. The Multi-Part Solution

To permanently fix this issue:
1. **Build a dedicated Web Agent (`agents/reroute_agents/agents/web/`)**: Searches the web for any destination, extracts verified places with sources, and geocodes them within valid bounding boxes.
2. **Canonical Destination Resolution**: Resolve destination text (aliases, sub-regions, towns) to canonical regions before searching or fetching.
3. **Strict Disjointness and Bounding Box Validation**: Reject out-of-region places and prevent cross-region catalog leakage.
4. **Integration Notes**: Instruct backend to remove `select(Place).limit(limit)` unconstrained fallback and instruct frontend to disable static MSW mocking for non-Darjeeling trips.
