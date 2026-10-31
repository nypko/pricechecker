# Carriers task 5: BG, RO, GR, CY (read 2026-10-31)

Mapping as in the brief (700 FDD B28/n28, 800 B20/n20, 900 B8/n8, 1800 B3/n3, 2100 B1/n1, 2600 paired B7/n7, 2600 unpaired/TDD B38/n38 only where labelled, 3.4-3.8 GHz n78, 26 GHz n258). bands.yaml: nothing missing, no change. Tests: 36 passed. No SDL listed. No rule-4 exclusions, no surrenders found.
Graphics/OCR: none needed. Every table was text (PDF text extracted with pdftotext, or HTML). No attribution comes from a graphic.
Succession: only Greece (WIND now NOVA, EETT table "WIND νυν NOVA") and Romania (Telekom merged into Vodafone, below).

## Summary
BG 3/3 complete, GR 3/3 complete, CY 3/4 complete (Cyta, Epic, PrimeTel; Cablenet not), RO 0/3 complete (no single current regulator table; all bands individually sourced). MVNOs: none verified anywhere, all empty. No nulls in lte/nr.

## Bulgaria (all licensed, complete true) - CRC register page
https://crc.bg/en/articles/2535/... (single table of all permits, 700/800/900/1800/2 GHz/2.6/3.6/26 GHz; holders A1 Bulgaria EAD, Vivacom Bulgaria EAD, Yettel Bulgaria EAD only). Cross-check: CEPT ECO Report 03 (18 Sep 2024), Bulgaria section, same blocks (kind other).
- 700: A1 703-713/758-768, Vivacom 713-723/768-778, Yettel 723-733/778-788, all 2x10, expiry 28.11.2038. 800: A1 791-801/832-842, Vivacom 801-811/842-852, Yettel 811-821/852-862, 2x10, 2038.
- 900: 2x11.6 each (A1 to 2034, Vivacom 2034, Yettel 23.01.2031). 1800: 2x25 each (same expiries). 2 GHz: 2x20 each, expiry 25.04.2035. ECO (2024) still showed 25.04.2025 for 2 GHz; the CRC page now says 2035, so the renewal is on the regulator page (rule 6 met by the CRC page itself).
- 2.6: 2x20 each, 2510-2530/2630-2650 (A1), 2530-2550/2650-2670 (Vivacom), 2550-2570/2670-2690 (Yettel), expiry 2041. All paired, so B7/n7. No unpaired 2570-2620 block held by anyone (nothing unexplained).
- 3.6: 120 MHz each in 3440-3800, expiry 11.05.2041 -> n78. 26 GHz: all three -> n258. The CRC table has one 26 GHz row with no holder name (26.7-26.9 GHz); ECO names it Vivacom. Irrelevant to the lists (all three already have n258).
- All three: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78,258. Duplex labels: the CRC page has no paired/unpaired column; pairing is read from the UL/DL pair of ranges.
- MVNOs: none verified.

## Greece (all licensed, complete true) - EETT consultation document of 2 Feb 2026
https://www.eett.gr/wp-content/uploads/2026/02/...φάσμα_02.02.2026.pdf, Table 1 "Ζώνες συχνοτήτων ανά πάροχο" (OTE / VODAFONE / NOVA / public rural networks, with expiry):
700 2x10 each (Nov 2036); 800 2x10 each (Feb 2030); 900 OTE 2x10, Vodafone 2x15, Nova 2x10 (Sep 2027); 1800 OTE 2x35, Vodafone 2x25, Nova 2x15 (40 MHz Nov 2027, 110 MHz Dec 2035); 2 GHz 2x20 each (Aug 2036); 2600 FDD OTE 2x30, Vodafone 2x20, Nova 2x20 (Feb 2030); 2600 TDD OTE 20, Vodafone 20, Nova "-" (Feb 2030); 3400-3800 OTE 150, Vodafone 140, Nova 100, rural networks 60 (Dec 2035; rural 60 to Apr 2037); 26 GHz OTE 400, Vodafone 400, Nova 200 (Dec 2035).
- The 2600 unpaired block is labelled "TDD" in the table, so B38/n38 for Cosmote and Vodafone; Nova has none. 900 MHz rights run to Sep 2027 and 1800 40 MHz to Nov 2027 (still valid today).
- Awarded-but-future: another EETT-era document (DEI answer, may.pdf, not cited) says that of the 390 MHz in 3.5 GHz awarded in 2020, 330 MHz was usable at once and 60 MHz only from 2029. Each operator still has 3.5 GHz in force now, so n78 stands; the table total (150+140+100) is the award, so the exact in-force MHz is not given. Not an issue for the band list.
- Cross-check ECO Report 03 Greece section (2024): same operators and blocks; 2600 unpaired 2575-2595 Cosmote, 2595-2615 Vodafone. Succession: EETT text "WIND νυν NOVA".
- Cosmote, Vodafone: lte 1,3,7,8,20,28,38; nr 1,3,7,8,20,28,38,78,258. Nova: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78,258.
- MVNOs: none verified.

## Cyprus (Cyta, Epic, PrimeTel complete; Cablenet not) - DEC (regulator)
Sources fetched: DEC consultation doc 2019 (Tables 1-4 give each holder's ranges, duplex labelled "(FDD)/(TDD)"); DEC consultation doc 3 Feb 2023 on renewing 800/900/1800/2100/2600 rights (Tables 1-2 with expiry dates, and: 4 operators received 700 and 3600 authorisations in 2021, 20 years); results page 4 Apr 2023; DEC announcement of contest D1/2024; ECO Report 03 Cyprus section (kind other).
- Validity: Cyta 900/1800/2100 expired 27.02.2024 and Epic 1.12.2023 in the 2023 DEC table; DEC proposed renewal to 21.06.2029 and said it would proceed at once (results doc). The renewal itself is evidenced by ECO Report 03: "License was renewed on 2023-10-13. Expire date extended from 2023-12-01 to 2029-06-21" for each block. That is a secondary (CEPT, from the administration) source for the renewal; I did not find the DEC renewal decision itself. This is the one place where a renewal rests on a kind-other source.
- Cyta: 700, 800 (2x10), 900 (2x12.2), 1800 (2x24.8), 2100 (2x15), 2600 FDD 2x20, 2600 TDD 15 MHz (labelled TDD), 3500-3600. lte 1,3,7,8,20,28,38; nr +78. Epic: the same with 3700-3800.
- PrimeTel: 700 (2x5), 900 (2x10), 1800, 2100, 3600-3700, no 800, no 2600. lte 1,3,8,28; nr 1,3,8,28,78. Expiry 21.06.2029 after the same renewal.
- Cablenet (own 4G/5G spectrum, mobile launched 2021): 700 (2x5, 2041), 800 (2x10), 2600 FDD 2x20, 2600 TDD 15 (labelled TDD), 3400-3500. lte 7,20,28,38; nr +78, complete false because DEC contest D1/2024 (2100 MHz, 1965-1980/2155-2170) was offered to Cablenet on 28 Aug 2024 at EUR 1.2m, "granted only if requirements are met within 30 days"; I found no confirmation of the grant, so B1/n1 is left out. Cablenet's own site also mentions a RAN-sharing agreement (not resolved), so "own radio network" is claimed from the licences only.
- 26 GHz: DEC homepage (through 29 May 2025) shows no 26 GHz award, and a 2026 consultation-results document exists (gov.cy, returned HTTP 403, unread). No n258 listed; complete true assumes none awarded yet.
- MVNOs: none verified.

## Romania (all licensed, complete false) - ANCOM
No single current ANCOM holdings table was found (the ANCOM licence register is not public as a table). Bands are built from regulator documents and each band is sourced; complete false for all three.
- 2012 auction results (ANCOM Position Document 2019, fetched): 800/900/1800/2600 rights 06.04.2014-05.04.2029: 800 Telekom 2x5, Orange 2x10, Vodafone 2x10; 900 Telekom 2x10, Orange 2x10, Vodafone 2x10, RCS&RDS 2x5; 1800 Telekom 2x25, Orange 2x20, Vodafone 2x30; 2600 FDD Telekom 2x10, Orange 2x20; 2600 TDD (2570-2615) 2K Telecom 30 MHz (later RCS&RDS), Vodafone 15 MHz.
- ANCOM 2022 selection tender (Caiet de sarcini, 2.4.3, Table 2.7): 2600 FDD Telekom 2x10 (2500-2510/2620-2630), Orange 2x20 (2510-2530/2630-2650), RCS&RDS 2x20 (2530-2550/2650-2670); 2600 TDD (labelled "(TDD)", 2570-2615) RCS&RDS 3 blocks 15 MHz, all to 05.04.2029; Vodafone has no 2600 in that table (its 15 MHz TDD block is now RCS&RDS's).
- 2100: ANCOM 31 Mar 2020: Orange and Vodafone licences extended 1 Apr 2020 - 31 Dec 2031. RCS&RDS and Telekom extension (fee due 30 Nov 2021) was proposed, and the ANCOM Oct 2025 release assigns 2100 MHz sub-band 1940-1950/2130-2140 from Telekom to Digi and cites licences valid to 5 Apr 2029 and 31 Dec 2031, but I found no ANCOM page confirming Digi's own 2100 extension. Digi B1/n1 rests on the 2025 assignment.
- 2022 auction result (ANCOM 15 Nov 2022): Orange 2x2x5 MHz 700 FDD (25 years from 1 Jan 2023), Vodafone 1x2x5 700 FDD; 3400-3800: Orange 16x10, Vodafone 10x10, RCS&RDS 5x10, 22 years from 1 Jan 2026 (in force today, 2026-10-31). RCS&RDS also 4x2x5 FDD 2600. Orange 1500 MHz (8x5) is SDL, not listed.
- 8 Oct 2025 ANCOM release: Telekom assigned to Digi 900 895-900/940-945, 1800 1770-1785/1865-1880, 2100 1940-1950/2130-2140, 2600 2500-2510/2620-2630; Digi leases 893-895/938-940 until 5 Apr 2029.
- Telekom succession: Vodafone took sole control 1 Oct 2025; Telekom's prepaid base went to Digi; Telekom Romania Mobile Communications merges into Vodafone at end of 30.06.2026 (Telekom subscriber notice, fetched, from telekom.ro: "La finalul zilei de 30.06.2026, Vodafone Romania S.A. si Telekom Romania Mobile Communications S.A. vor fuziona", and users stay on the Telekom network until the networks are integrated). Telekom is therefore no network entry. Its bands (800/900/1800/2100/2600) add no band to Vodafone beyond those it already holds (its 2600 went entirely to Digi). Press for the merger came from search snippets only (mobilissimo, economedia), not cited.
- Orange: lte 1,3,7,8,20,28; nr +78. Vodafone: lte 1,3,8,20,28; nr +78. Digi: 900, 1800, 2100, 2600 FDD (B7), 2600 TDD (B38), 3.4-3.8: lte 1,3,7,8,38; nr 1,3,7,8,38,78. Digi has no 700 or 800.
- Not found: 26 GHz in Romania (no ANCOM award seen), Telekom's exact holdings after temporary sharing with Vodafone, Digi 2100 own-licence extension.
- MVNOs: none verified.
