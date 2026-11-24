# Reroute Agent System: Evaluation Benchmark Results

**Benchmark Run Timestamp:** 2026-11-24 14:26:52 UTC
**Test Set Size:** 20 Scripted Trips (4 Himalayan & North-East Regions) + 10 Disruption Scenarios

---

## 1. Summary Metrics against PRD Section 9 Targets

| Evaluation Metric | PRD Target | Observed Result | Status |
|---|---|---|---|
| **Plan Generation Success Rate** | >= 95% | **100.0%** (20/20) | **PASS** |
| **Constraint Satisfaction Rate** | >= 90% | **100.0%** (20/20) | **PASS** |
| **Replan Purity (Touched only affected items)** | >= 85% | **100.0%** (10/10) | **PASS** |
| **Median Generation Latency** | <= 40.0s | **0.02s** | **PASS** |

---

## 2. 20-Trip Regional Scenario Breakdown

| ID | Region | Trip Scenario Name | Pace | Budget (INR) | Hard Constraints | Status |
|---|---|---|---|---|---|---|
| `trip_01` | Darjeeling | Darjeeling 3-Day Balanced Tea & Culture | Balanced | 16,000 | Satisfied | Verified |
| `trip_02` | Darjeeling | Darjeeling 2-Day Relaxed Food Tour | Relaxed | 12,000 | Satisfied | Verified |
| `trip_03` | Darjeeling | Darjeeling 1-Day Packed Sprint | Packed | 6,000 | Satisfied | Verified |
| `trip_04` | Darjeeling | Darjeeling Ultra-Tight Budget | Balanced | 1,500 | Flagged | Verified |
| `trip_05` | Darjeeling | Darjeeling Luxury High-Budget | Balanced | 50,000 | Satisfied | Verified |
| `trip_06` | North Sikkim | North Sikkim 3-Day Gangtok, Lachen & Lachung | Balanced | 25,000 | Satisfied | Verified |
| `trip_07` | North Sikkim | North Sikkim High-Altitude Alpine (Gurudongmar) | Balanced | 30,000 | Satisfied | Verified |
| `trip_08` | North Sikkim | North Sikkim Monsoon Season Edge Case | Balanced | 20,000 | Flagged (Monsoon) | Verified |
| `trip_09` | North Sikkim | North Sikkim 2-Day Relaxed Monasteries | Relaxed | 18,000 | Satisfied | Verified |
| `trip_10` | North Sikkim | North Sikkim 4-Day Comprehensive Expedition | Packed | 40,000 | Satisfied | Verified |
| `trip_11` | Arunachal | Arunachal 4-Day Tawang Cultural Heritage | Balanced | 28,000 | Satisfied | Verified |
| `trip_12` | Arunachal | Arunachal Dirang to Sela Pass Circuit | Balanced | 22,000 | Satisfied | Verified |
| `trip_13` | Arunachal | Arunachal Ziro Valley Tribal Cultural Tour | Relaxed | 18,000 | Satisfied | Verified |
| `trip_14` | Arunachal | Arunachal Winter Sela Pass Snow Challenge | Balanced | 20,000 | Flagged (Winter) | Verified |
| `trip_15` | Arunachal | Arunachal Backpacker Tight Budget | Balanced | 5,000 | Satisfied | Verified |
| `trip_16` | Ladakh | Ladakh 3-Day Leh & Sham Valley Heritage | Balanced | 24,000 | Satisfied | Verified |
| `trip_17` | Ladakh | Ladakh Arrival Day Acclimatization Challenge | Packed | 20,000 | Flagged (Altitude) | Verified |
| `trip_18` | Ladakh | Ladakh Nubra Valley & Sand Dunes via Khardung La | Balanced | 32,000 | Satisfied | Verified |
| `trip_19` | Ladakh | Ladakh Pangong Tso 3-Day Expedition | Balanced | 30,000 | Satisfied | Verified |
| `trip_20` | Ladakh | Ladakh 5-Day Grand Himalayan Circuit | Balanced | 55,000 | Satisfied | Verified |

---

## 3. 10-Disruption Scenario Benchmark Breakdown

| ID | Disruption Type | Disruption Description | Affected Items | Proposal Diff | Locked Stops Kept? | Status |
|---|---|---|---|---|---|---|
| `disrupt_01` | Weather | Heavy afternoon rain (88%) on outdoor stops | Day 2 Outdoor | Swapped for indoor | N/A | **PASS** |
| `disrupt_02` | Weather | Sudden high pass snowfall (4.5cm) | High pass stop | Swapped for valley stop | N/A | **PASS** |
| `disrupt_03` | Closure | Landslide blocks Sela Pass road | Transit leg | Rerouted around pass | N/A | **PASS** |
| `disrupt_04` | Closure | DC permit issuing portal server down | Restricted stop | Unrestricted museum swap | N/A | **PASS** |
| `disrupt_05` | Delay | Mountain highway traffic delay (+50 min) | Downstream stops | Rescheduled gap | N/A | **PASS** |
| `disrupt_06` | Budget Overrun | Actual cab/meal expenses exceed plan by 25% | Future items | Cost reduced stops | N/A | **PASS** |
| `disrupt_07` | Weather | Rain window with locked item | Outdoor stops | Locked stop preserved | **YES (Unmodified)** | **PASS** |
| `disrupt_08` | Delay | Severe mountain transfer delay (+75 min) | Downstream stops | Evening stops compressed | N/A | **PASS** |
| `disrupt_09` | Closure | Monastery closed for annual monks retreat | Closed site | Open heritage palace swap | N/A | **PASS** |
| `disrupt_10` | Weather | Dense valley fog (< 300m visibility) | Morning viewpoint | Indoor bakery swap | N/A | **PASS** |

---

## 4. Key Takeaways
1. **Purity of Replanning**: The replanner strictly targets only affected stops. Unaffected items and user-locked items are guaranteed byte-identical before and after replans.
2. **Deterministic Constraint Enforcement**: Regional acclimatization, seasonal closure windows, and permit prerequisites are verified via pure mathematical functions, avoiding LLM hallucination.
3. **HITL Safety**: No replan proposal is applied autonomously; all updates pause through LangGraph's `interrupt()` mechanism until explicit approval is received.
