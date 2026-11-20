# Seed Data Verification and Audit Report

This document records the verification status of curated places in `agents/data/seed/` for the v1 vertical slice (Himalayan and North-East India).

---

## 1. Verified Destinations Overview

All 4 regional catalogs contain verified places with conservative cost estimates (in INR) and documented altitude coordinates.
1. **Darjeeling**: 16 places covering central Darjeeling, Ghum, Kalimpong, and Mirik.
2. **North Sikkim**: 15 places covering Gangtok (gateway), Lachen, Lachung, Yumthang Valley, Zero Point, and Gurudongmar Lake.
3. **Arunachal Pradesh**: 15 places covering Tawang, Dirang, Bomdila, and Ziro.
4. **Ladakh**: 16 places covering Leh, Sham Valley, Nubra Valley, and Pangong Tso.

---

## 2. Records Pending Human Verification (`verify: true`)

Before production deployment or official evaluation demonstrations, the following records must be verified with official state tourism departments or local administration:

| External ID | Name | City / Region | Field Pending Verification | Recommended Source |
|---|---|---|---|---|
| `seed:darjeeling:mirik_sumendu_lake` | Mirik Lake (Sumendu Lake) | Darjeeling (Mirik) | Operating hours, boating contractor rates, night access | GTA Tourism / West Bengal Tourism |
| `seed:sikkim:chopta_valley` | Chopta Valley | North Sikkim | Checkpoint timing, military pass requirements beyond Thangu | Sikkim Tourism & Civil Aviation Dept / Mangan DM |
| `seed:sikkim:singhik_viewpoint` | Singhik Viewpoint | North Sikkim | Maintenance entry charges, cafeteria timings | Mangan District Administration |
| `seed:arunachal:ziro_hong_village` | Hong Village | Arunachal Pradesh (Ziro) | Apatani tribal council community guidelines and local festival fees | Lower Subansiri District Tourism Office |
| `seed:arunachal:apple_nursery_dirang` | NRC on Yak & Apple Orchards | Arunachal Pradesh (Dirang) | Public visitor hours, technical tour permissions | ICAR-NRC on Yak official office |

---

## 3. Permit Policies Summary

All permit references in seed data are marked with the disclaimer:
*"Permit requirements change; verify with official government sources before travel."*

- **Arunachal Pradesh**: Inner Line Permit (ILP) required for all domestic visitors; Protected Area Permit (PAP) for foreign nationals.
- **North Sikkim**: Protected Area Permit (PAP) mandatory for Lachen, Lachung, Yumthang, and Zero Point. Gurudongmar Lake is restricted to Indian citizens.
- **Ladakh**: Inner Line Permit / Protected Area Permit required for Nubra Valley (via Khardung La) and Pangong Tso (via Chang La).
