"""Evaluation set: 20 scripted trips across 4 regions and 10 disruption scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from reroute_agents.state import InjectedSignals, TripSpec


@dataclass
class TripScenario:
    id: str
    name: str
    spec: TripSpec
    expected_valid: bool = True
    edge_case_note: str = ""


@dataclass
class DisruptionScenario:
    id: str
    name: str
    trip_id: str
    injected: InjectedSignals
    expected_type: str
    locked_item_index: int | None = None
    description: str = ""


def get_evaluation_trips() -> list[TripScenario]:
    """Return 20 scripted trips covering normal flows and critical regional edge cases."""
    trips: list[TripScenario] = [
        # --- Darjeeling Region (1-5) ---
        TripScenario(
            id="trip_01_darj_balanced",
            name="Darjeeling 3-Day Balanced Tea & Culture",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Darjeeling",
                start_date=date(2026, 12, 1),
                end_date=date(2026, 12, 3),
                group_size=2,
                budget_total=Decimal(16000),
                currency="INR",
                pace="balanced",
                vibe_tags=["tea", "culture", "nature"],
            ),
            edge_case_note="Standard multi-day balanced itinerary",
        ),
        TripScenario(
            id="trip_02_darj_relaxed",
            name="Darjeeling 2-Day Relaxed Food Tour",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Darjeeling",
                start_date=date(2026, 12, 5),
                end_date=date(2026, 12, 6),
                group_size=2,
                budget_total=Decimal(12000),
                currency="INR",
                pace="relaxed",
                vibe_tags=["food", "cafe", "bakery"],
            ),
            edge_case_note="Relaxed pace with daily span cap of 8 hours",
        ),
        TripScenario(
            id="trip_03_darj_1day_packed",
            name="Darjeeling 1-Day Packed Sprint",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Darjeeling",
                start_date=date(2026, 12, 10),
                end_date=date(2026, 12, 10),
                group_size=1,
                budget_total=Decimal(6000),
                currency="INR",
                pace="packed",
                vibe_tags=["sightseeing", "nature"],
            ),
            edge_case_note="1-day trip boundary test",
        ),
        TripScenario(
            id="trip_04_darj_tight_budget",
            name="Darjeeling Ultra-Tight Budget",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Darjeeling",
                start_date=date(2026, 12, 12),
                end_date=date(2026, 12, 14),
                group_size=2,
                budget_total=Decimal(1500),  # Very tight budget
                currency="INR",
                pace="balanced",
                vibe_tags=["nature"],
            ),
            edge_case_note="Very low budget constraint challenge",
        ),
        TripScenario(
            id="trip_05_darj_luxury",
            name="Darjeeling Luxury High-Budget",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Darjeeling",
                start_date=date(2026, 12, 15),
                end_date=date(2026, 12, 17),
                group_size=2,
                budget_total=Decimal(50000),
                currency="INR",
                pace="balanced",
                vibe_tags=["tea", "heritage"],
            ),
            edge_case_note="High budget ceiling test",
        ),
        # --- North Sikkim Region (6-10) ---
        TripScenario(
            id="trip_06_sikkim_balanced",
            name="North Sikkim 3-Day Gangtok, Lachen & Lachung",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="North Sikkim",
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 12),
                group_size=2,
                budget_total=Decimal(25000),
                currency="INR",
                pace="balanced",
                vibe_tags=["monastery", "nature"],
            ),
            edge_case_note="High mountain transfers with permit requirements",
        ),
        TripScenario(
            id="trip_07_sikkim_high_altitude",
            name="North Sikkim High-Altitude Alpine (Gurudongmar)",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="North Sikkim",
                start_date=date(2026, 5, 15),
                end_date=date(2026, 5, 17),
                group_size=2,
                budget_total=Decimal(30000),
                currency="INR",
                pace="balanced",
                vibe_tags=["high_altitude", "lake"],
            ),
            edge_case_note="Extreme elevation gain check (5154m)",
        ),
        TripScenario(
            id="trip_08_sikkim_monsoon_edge",
            name="North Sikkim Monsoon Season Edge Case",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="North Sikkim",
                start_date=date(2026, 7, 20),
                end_date=date(2026, 7, 22),
                group_size=2,
                budget_total=Decimal(20000),
                currency="INR",
                pace="balanced",
                vibe_tags=["nature"],
            ),
            edge_case_note="Seasonal monsoon road closure flags expected",
        ),
        TripScenario(
            id="trip_09_sikkim_relaxed",
            name="North Sikkim 2-Day Relaxed Monasteries",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="North Sikkim",
                start_date=date(2026, 10, 10),
                end_date=date(2026, 10, 11),
                group_size=2,
                budget_total=Decimal(18000),
                currency="INR",
                pace="relaxed",
                vibe_tags=["culture", "buddhist"],
            ),
            edge_case_note="Low intensity cultural trip",
        ),
        TripScenario(
            id="trip_10_sikkim_4day_packed",
            name="North Sikkim 4-Day Comprehensive Expedition",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="North Sikkim",
                start_date=date(2026, 11, 20),
                end_date=date(2026, 11, 23),
                group_size=3,
                budget_total=Decimal(40000),
                currency="INR",
                pace="packed",
                vibe_tags=["adventure", "nature", "snow"],
            ),
            edge_case_note="Multi-leg route with high active duration",
        ),
        # --- Arunachal Pradesh Region (11-15) ---
        TripScenario(
            id="trip_11_arunachal_tawang_heritage",
            name="Arunachal Pradesh 4-Day Tawang Cultural Heritage",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Arunachal Pradesh",
                start_date=date(2026, 10, 15),
                end_date=date(2026, 10, 18),
                group_size=2,
                budget_total=Decimal(28000),
                currency="INR",
                pace="balanced",
                vibe_tags=["culture", "monastery", "heritage"],
            ),
            edge_case_note="Permit requirements (ILP/PAP) integration check",
        ),
        TripScenario(
            id="trip_12_arunachal_pass_circuit",
            name="Arunachal Dirang to Sela Pass Circuit",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Arunachal Pradesh",
                start_date=date(2026, 11, 5),
                end_date=date(2026, 11, 7),
                group_size=2,
                budget_total=Decimal(22000),
                currency="INR",
                pace="balanced",
                vibe_tags=["high_pass", "nature"],
            ),
            edge_case_note="Sela Pass elevation (4170m) transit",
        ),
        TripScenario(
            id="trip_13_arunachal_ziro_tribal",
            name="Arunachal Ziro Valley Tribal Cultural Tour",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Arunachal Pradesh",
                start_date=date(2026, 9, 24),
                end_date=date(2026, 9, 26),
                group_size=2,
                budget_total=Decimal(18000),
                currency="INR",
                pace="relaxed",
                vibe_tags=["tribal", "paddy", "apatani"],
            ),
            edge_case_note="Indigenous Apatani valley and fish farm exploration",
        ),
        TripScenario(
            id="trip_14_arunachal_winter_edge",
            name="Arunachal Winter Sela Pass Snow Challenge",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Arunachal Pradesh",
                start_date=date(2026, 1, 10),
                end_date=date(2026, 1, 12),
                group_size=2,
                budget_total=Decimal(20000),
                currency="INR",
                pace="balanced",
                vibe_tags=["snow", "scenic"],
            ),
            edge_case_note="Winter seasonal road closure on Sela Pass",
        ),
        TripScenario(
            id="trip_15_arunachal_budget",
            name="Arunachal Backpacker Tight Budget",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Arunachal Pradesh",
                start_date=date(2026, 10, 20),
                end_date=date(2026, 10, 22),
                group_size=1,
                budget_total=Decimal(5000),
                currency="INR",
                pace="balanced",
                vibe_tags=["culture"],
            ),
            edge_case_note="Low budget solo traveler test",
        ),
        # --- Ladakh Region (16-20) ---
        TripScenario(
            id="trip_16_ladakh_leh_heritage",
            name="Ladakh 3-Day Leh & Sham Valley Heritage",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Ladakh",
                start_date=date(2026, 8, 10),
                end_date=date(2026, 8, 12),
                group_size=2,
                budget_total=Decimal(24000),
                currency="INR",
                pace="balanced",
                vibe_tags=["monastery", "culture", "palace"],
            ),
            edge_case_note="Standard high-altitude valley exploration",
        ),
        TripScenario(
            id="trip_17_ladakh_arrival_altitude",
            name="Ladakh Arrival Day Acclimatization Challenge",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Ladakh",
                start_date=date(2026, 8, 15),
                end_date=date(2026, 8, 16),
                group_size=2,
                budget_total=Decimal(20000),
                currency="INR",
                pace="packed",  # Packed pace on arrival day at 3500m
                vibe_tags=["adventure", "outdoor"],
            ),
            edge_case_note="Tests altitude acclimatization rule on Day 1",
        ),
        TripScenario(
            id="trip_18_ladakh_nubra_camels",
            name="Ladakh Nubra Valley & Sand Dunes via Khardung La",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Ladakh",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 3),
                group_size=2,
                budget_total=Decimal(32000),
                currency="INR",
                pace="balanced",
                vibe_tags=["desert", "sand_dunes", "buddhist"],
            ),
            edge_case_note="Pass crossing at Khardung La (5359m)",
        ),
        TripScenario(
            id="trip_19_ladakh_pangong_lake",
            name="Ladakh Pangong Tso 3-Day Expedition",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Ladakh",
                start_date=date(2026, 8, 20),
                end_date=date(2026, 8, 22),
                group_size=2,
                budget_total=Decimal(30000),
                currency="INR",
                pace="balanced",
                vibe_tags=["lake", "high_altitude"],
            ),
            edge_case_note="Endorheic salt lake transit via Chang La",
        ),
        TripScenario(
            id="trip_20_ladakh_5day_grand",
            name="Ladakh 5-Day Grand Himalayan Circuit",
            spec=TripSpec(
                trip_id=uuid4(),
                destination="Ladakh",
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 14),
                group_size=2,
                budget_total=Decimal(55000),
                currency="INR",
                pace="balanced",
                vibe_tags=["monastery", "lake", "desert"],
            ),
            edge_case_note="Comprehensive 5-day multi-valley circuit",
        ),
    ]
    return trips


def get_disruption_scenarios() -> list[DisruptionScenario]:
    """Return 10 representative disruption scenarios for replanning evaluation."""
    return [
        DisruptionScenario(
            id="disrupt_01_rain",
            name="Heavy afternoon rain on outdoor stops",
            trip_id="trip_01_darj_balanced",
            injected=InjectedSignals(
                type="weather",
                day_index=2,
                params={"precip_prob": 0.88, "from": "13:00", "to": "17:00"},
            ),
            expected_type="weather",
            description="Swaps outdoor viewpoint for indoor tea museum / bakery",
        ),
        DisruptionScenario(
            id="disrupt_02_snowfall",
            name="Sudden high pass snowfall",
            trip_id="trip_07_sikkim_high_altitude",
            injected=InjectedSignals(
                type="weather",
                day_index=2,
                params={"precip_prob": 0.75, "snowfall": 4.5, "from": "08:00", "to": "14:00"},
            ),
            expected_type="weather",
            description="Replaces high altitude pass with lower valley hot springs",
        ),
        DisruptionScenario(
            id="disrupt_03_pass_closure",
            name="Landslide blocks Sela Pass road",
            trip_id="trip_12_arunachal_pass_circuit",
            injected=InjectedSignals(
                type="closure",
                day_index=2,
                params={"reason": "Landslide blocks Sela Pass road"},
            ),
            expected_type="closure",
            description="Closes transit over pass; reroutes to local heritage dzong",
        ),
        DisruptionScenario(
            id="disrupt_04_permit_office",
            name="DC permit issuing server down",
            trip_id="trip_11_arunachal_tawang_heritage",
            injected=InjectedSignals(
                type="closure",
                day_index=1,
                params={"reason": "DC office permit portal down for PAP verification"},
            ),
            expected_type="closure",
            description="Delays restricted stop and substitutes unrestricted cultural museum",
        ),
        DisruptionScenario(
            id="disrupt_05_travel_delay",
            name="Mountain highway traffic jam (+50 min)",
            trip_id="trip_06_sikkim_balanced",
            injected=InjectedSignals(
                type="delay",
                day_index=1,
                params={"delay_minutes": 50},
            ),
            expected_type="delay",
            description="Pushes downstream stops or drops last stop to preserve daily limit",
        ),
        DisruptionScenario(
            id="disrupt_06_budget_overrun",
            name="Actual meal/cab expenses exceeded by 25%",
            trip_id="trip_05_darj_luxury",
            injected=InjectedSignals(
                type="budget_overrun",
                day_index=1,
                params={"overrun_pct": 0.25},
            ),
            expected_type="budget_overrun",
            description="Replaces expensive upcoming stops with free public walking loops",
        ),
        DisruptionScenario(
            id="disrupt_07_locked_item",
            name="Disruption on day with locked item",
            trip_id="trip_04_darj_tight_budget",
            injected=InjectedSignals(
                type="weather",
                day_index=2,
                params={"precip_prob": 0.90, "from": "10:00", "to": "16:00"},
            ),
            expected_type="weather",
            locked_item_index=0,
            description="Locked item must stay byte-identical while unlocked stops adapt",
        ),
        DisruptionScenario(
            id="disrupt_08_multistop_delay",
            name="Severe transfer delay (+75 min)",
            trip_id="trip_18_ladakh_nubra_camels",
            injected=InjectedSignals(
                type="delay",
                day_index=2,
                params={"delay_minutes": 75},
            ),
            expected_type="delay",
            description="Major delay crossing Khardung La compresses evening schedule",
        ),
        DisruptionScenario(
            id="disrupt_09_attraction_closed",
            name="Monastery closed for private puja rituals",
            trip_id="trip_16_ladakh_leh_heritage",
            injected=InjectedSignals(
                type="closure",
                day_index=1,
                params={"reason": "Monastery closed for annual monks retreat ceremony"},
            ),
            expected_type="closure",
            description="Swaps closed monastery for open palace museum",
        ),
        DisruptionScenario(
            id="disrupt_10_fog_low_visibility",
            name="Dense valley fog (< 500m visibility)",
            trip_id="trip_03_darj_1day_packed",
            injected=InjectedSignals(
                type="weather",
                day_index=1,
                params={"precip_prob": 0.70, "visibility": 300, "from": "09:00", "to": "12:00"},
            ),
            expected_type="weather",
            description="Low visibility replaces morning outdoor stop with indoor cultural venue",
        ),
    ]
