# Seed Data Verification and Audit Report (AG-007)

This document records the verification audit status of curated places and travel routes in `agents/data/seed/` for the v1 vertical slice (Himalayan and North-East India).

---

## 1. Audit Policy & Integrity Invariant

Per Hard Rule 0 ("Do not fabricate real-world facts. Seed data must be marked with a confidence level and a verify flag") and audit finding AG-007:
1. **No False Claims of Verification:** Since places were compiled from travel literature and regional mapping rather than direct on-site verification or certified state tourism APIs, all 62 place records and 21 transit routes are honestly marked with:
   - `verify: true`: flags that physical verification or local authority confirmation is required prior to commercial operations.
   - `hours_confidence: "estimated"` / `confidence: "estimated"`: indicates realistic estimated hours and costs based on regional norms rather than certified live feeds.
   - `source: null`: explicitly documents the absence of an authoritative digital API citation.
2. **Deterministic Fallbacks:** When `verify: true`, the validator and monitor engines treat data with conservative margins (e.g. assume open if hours are unverified rather than blocking traveler schedules).

---

## 2. Regional Inventory Requiring Human Verification (`verify: true`)

All 62 place records require field verification with local administration:

| Region | Total Records | Confidence | Verification Status | Official Verification Body |
|---|---|---|---|---|
| **Darjeeling** | 16 | `estimated` | `verify: true` (16/16) | Gorkhaland Territorial Administration (GTA) Tourism / West Bengal Tourism |
| **North Sikkim** | 15 | `estimated` | `verify: true` (15/15) | Sikkim Tourism & Civil Aviation Department / Mangan District Collectorate |
| **Arunachal Pradesh** | 15 | `estimated` | `verify: true` (15/15) | Department of Tourism, Govt of Arunachal Pradesh / Tawang & Ziro DC Offices |
| **Ladakh** | 16 | `estimated` | `verify: true` (16/16) | Department of Tourism, UT Ladakh / Leh & Kargil Tourist Information Centres |
| **Mountain Routes** | 21 routes | `estimated` | `verify: true` (21/21) | Border Roads Organisation (BRO) / Project Himank / Project Beacon / State PWD |

### Key High-Priority Verification Items:
1. **Altitude & Acclimatization:** High-altitude passes (Khardung La 5359m, Chang La 5360m, Zero Point 4663m, Gurudongmar Lake 5430m, Sela Pass 4170m) must be verified against current BRO pass elevation markers.
2. **Seasonal Access Windows:** Monsoon closures (July-August) and winter snowbound windows (December-March) must be checked against annual district disaster management advisories.
3. **Inner Line & Protected Area Permits:** Checkpoint operational timings (e.g., Mangan, Thangu, Vartak, South Pullu) and permit issuance fees must be confirmed with local sub-divisional magistrates.

---

## 3. Permit Policies Summary

All permit references in seed data are marked with the mandatory disclaimer:
*"Permit requirements change; verify with official government sources before travel."*

- **Arunachal Pradesh**: Inner Line Permit (ILP) required for all domestic visitors; Protected Area Permit (PAP) for foreign nationals.
- **North Sikkim**: Protected Area Permit (PAP) mandatory for Lachen, Lachung, Yumthang, and Zero Point. Gurudongmar Lake is restricted strictly to Indian citizens.
- **Ladakh**: Inner Line Permit (ILP) required for non-locals visiting Nubra Valley (via Khardung La) and Pangong Tso (via Chang La).
