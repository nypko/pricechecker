# Carriers task 4: PL, CZ, SK, HU, SI, HR (read 2026-10-31)

Mapping used for every regulator table: 700 FDD -> B28/n28; 800 -> B20/n20; 900 -> B8/n8; 1800 -> B3/n3; 2100 -> B1/n1;
2600 paired (2x) -> B7/n7; 2600 TDD -> B38/n38 only where the source says TDD/unpaired; 3.4-3.8 GHz -> n78 (no LTE band); 26 GHz -> n258.
SI only: AKOS says "2300 MHz" -> B40/n40 (TDD band, not in the brief's mapping; flagged) and "1500 MHz" -> B32 (SDL, listed because AKOS says A1 uses it).
bands.yaml: nothing missing, no change. Tests: 36 passed. No SDL listed except SI A1 B32. No rule-4 exclusions, no surrenders found.
Graphics/OCR: HU 2600 attribution (logo table, read by eye from rendered page 9), PL 2600 TDD column (text labels from the UKE occupancy PDF), HR 700/3600/26 GHz tables (PNG images, read by eye). No OCR run.

## Summary
PL 4/4 complete, CZ 3/3 complete (T-Mobile, O2 now with B38/n38), HU 3/3 complete, HR 3/3 complete, SK 2/4 complete (O2, SWAN not), SI 0/4 (basis used).

## Poland (all licensed, complete true) - UKE BIP "Rezerwacje ogólnopolskie"
Per-band tables at https://bip.uke.gov.pl/rezerwacje-czestotliwosci/rezerwacje-ogolnopolskie-tresci/{700-mhz,10 | 800-mhz,6 | 900-mhz,5 | 1800-mhz,4 | 2100-mhz,3 | 2600-mhz,2 | 3600-mhz,9}.html (band pages modified 2025-08 to 2026-10; 3600 page lists 2026-10-28 files). Each table row = holder + paired range (up/down) = FDD.
- 700 (703-733/758-788): T-Mobile 703-708/758-763; Orange 708-713 and 713-718; Polkomtel 718-723; P4 723-728 and 728-733.
- 800: Orange 791-796 and 796-801; P4 801-806; T-Mobile 806-811, 811-816, 816-821. Polkomtel: no row (no B20).
- 900: P4 880.1-885.1; Polkomtel 885.1-890.1 and 890.1-899.1; T-Mobile 899.1-908.1; Orange 908.1-914.9.
- 1800: Polkomtel 1710-1740 (six rows); T-Mobile 1740-1760 (five rows); Orange 1760-1770; P4 1770-1785.
- 2100: Orange 1920-1934.9; T-Mobile 1935-1949.9; Polkomtel 1950-1964.9; P4 1965-1979.9 (each two rows).
- 2600: Polkomtel 2500-2520/2620-2640; Orange 2520-2535; T-Mobile 2535-2550; P4 2550-2570/2670-2690 (paired -> B7/n7 all four). Polkomtel also "2570-2620 MHz" unpaired (graphic note below). Duplex for that block: UKE occupancy chart PDF (https://bip.uke.gov.pl/download/gfx/bip/pl/defaultaktualnosci/135/13/7/2023-01-04_zajetosc_2600_mhz.pdf, 2023-01-04) has columns "FDD (DL) | TDD | FDD (UL)" and "Polkomtel sp. z o.o." under TDD, 2570-2620. -> Plus gets B38/n38. Source is a 2023 chart (a graphic whose labels were extracted as text); the 2026 table gives the same single range but does not label the duplex. Plus B38/n38 therefore rests on that 2023 UKE chart only.
- 3600 (3400-3800): Polkomtel 3400-3500 (not 33 gminas per footnote); P4 3500-3600; Orange 3600-3700; T-Mobile 3700-3800. -> n78 all.
- 26 GHz: no UKE nationwide row (list stops at 3600) -> no n258. 
- Orange lte 1,3,7,8,20,28 nr +78; Plus lte 1,3,7,8,28,38 nr 1,3,7,8,28,38,78; T-Mobile and Play as Orange.
- Caveat: UKE 3600 page notes consultations opened 2026-10-28 to change P4 3500-3600 and Orange 3600-3700 reservations (n78 stays). 700 allocation matches the March 2025 auction (press only, not cited).
- MVNOs: none verified (Premium Mobile on Plus appears in third-party reviews only; premiummobile.pl fetched, names no network; virginmobile.pl and plush site unreachable).

## Czechia (all licensed, complete true) - ČTÚ open data "Přehled přídělů rádiových kmitočtů"
CSV https://data.ctu.gov.cz/sites/default/files/pridely-radiovych-kmitoctu_202606.csv (June 2026, now also the 2016 press release above; dataset page https://data.ctu.gov.cz/dataset/prehled-pridelu-radiovych-kmitoctu). 73 rows, columns "Párový kmitočet", downlink/uplink ranges, "Aplikace", "Subjekt". Rows with Aplikace "Mobilní síť" (all paired = "Ano" below 3.4 GHz):
- 700 (DL 758-788): O2 758-768 (id 35), T-Mobile 768-778 (36), Vodafone 778-788 (37).
- 800: T-Mobile 791-801 (38), O2 801-811 (39), Vodafone 811-821 (40).
- 900: Vodafone 925.1-935.1 (41), T-Mobile 935.1-947.5 (42), O2 947.5-959.9 (43).
- 1800: O2 (ids 44-49, 1805-1832.9), T-Mobile (50-51, 1832.9-1852.9), Vodafone (52-54, 1852.9-1879.9).
- 2100: O2 2110-2130 (55), Vodafone 2130-2150 (56), T-Mobile 2150-2170 (57).
- 2600 (paired): O2 2620-2640 (61), T-Mobile 2640-2660 and 2680-2690 (62, 64), Vodafone 2660-2680 (63).
- 3400-3800 (unpaired "Ne"): T-Mobile 3400-3540, Vodafone 3540-3620 and 3620-3640, O2 3640-3800.
- No 26 GHz row -> no n258.
- Rows 59-60 (fix round 1, correcting my earlier "not mobile"): ID 59 T-Mobile 2570-2595, ID 60 O2 2595-2620, unpaired ("Ne"), valid to 2029-06-30, Aplikace blank. ČTÚ press release 14 Jun 2016 (https://ctu.gov.cz/sites/default/files/obsah/ctu/tiskova-zprava-ctu-vydrazil-zbyvajici-kmitocty-v-pasmech-1800-mhz-2600-mhz/obrazky/tz20160614aukce-18002600-vydrazeno.pdf): "v nepárové části pásma 2600 MHz potom získaly společnosti O2 a T-Mobile po jednom aukčním bloku o velikost 25 MHz" (in the unpaired part of 2600 MHz, O2 and T-Mobile each got one 25 MHz block), and the operators use the spectrum for mobile internet. Matches both rows (25 MHz each). Unpaired = stated duplex -> B38/n38 for T-Mobile and O2 (complete stays true). Vodafone has no unpaired row.
- T-Mobile and O2: lte 1,3,7,8,20,28,38; nr 1,3,7,8,20,28,38,78. Vodafone lte 1,3,7,8,20,28; nr +78. Succession: none needed (names in table are the current operators).
- MVNOs: none verified (kaktus.cz and lidl-connect.cz unreachable).

## Slovakia (licensed; Orange, Telekom complete; O2, SWAN not)
Sources: RÚ public discussion 2024-09-17 (https://www.teleoff.gov.sk/files/urad/odbory-oddelenia/odbor-spravy-frekvencneho-spektra/konzultacne-miesto/20240917_diskusia_multiband_aukcia/20240917_verejna-diskusia_final.pdf), Tabuľka 3.1 and sections 3.1-3.5; auction results PDF of 9 Jul 2025 (https://www.teleoff.gov.sk/files/urad/aktuality/tlacove-spravy/urad-uspesne-ukoncil-aukciu-mobilnych-frekvencii-rekordnym-vynosom-vsetky-frekvencie-su-predane/vysledky-elektronickej-aukcie.pdf). I also fetched the press release page and the vyberove-konania page; swan.pdf (SWAN's comments hosted by RÚ) repeats Table 3.1 and is not cited.
Table 3.1 "Rozdelenie frekvenčného spektra" (MHz): 700: Orange 20, Telekom 20, O2 20; 800: 20/20/20; 900: 20.4/20.4/28.8; 1800: Orange 40, Telekom 36.4, O2 37.6, SWAN 36; 2100: 40/40/40 (SWAN none); 2600: Orange 60, Telekom 80, O2 none; 2600 TDD: Telekom 50; 3600 (footnote "Platí od 1.9.2025"): 100 each incl. SWAN. Text: 800 "O2 811-821/852-862; Slovak Telekom 791-801/832-842; Orange 801-811/842-852"; 2600 "Slovak Telekom 2530-2570/2650-2690 s módom prevádzky FDD a 2570-2620 s módom prevádzky TDD"; "Orange Slovensko 2500-2530/2620-2650".
- Orange lte 1,3,7,8,20,28 nr +78. Telekom the same + B38/n38 (stated TDD). O2: 700, 800, 900, 1800, 2100, 3600 -> lte 1,3,8,20,28 nr +78 (no 2600 in force). SWAN: 1800 and 3600 only -> lte 3, nr 78.
- Auction of 9 Jul 2025 (800, 900, 1500, 2100, 2600 FDD/TDD): O2 won 2600 FDD 2500-2520/2620-2640; SWAN won 900 (900-905/945-950), 2100 (1970-1980/2160-2170), 2600 FDD (2520-2530/2640-2650) and 1500. RÚ document says 800/900/2600 usable "od 1.1.2029", 2100 "od 8.9.2026, resp. 1.1.2029" (decision pending), 1500 immediately. These rights are not in force in the 2024 table, so I did NOT list them: O2 B7/n7 and SWAN B8/B1/B7 (+n-bands) are left out and O2, SWAN set complete false. Orange and Telekom: auction awards equal their existing bands, so complete true. Reviewer decision: if you want awarded-but-future rights listed, add O2 7/n7 and SWAN 1,7,8 / n1,7,8.
- Fix round 1, 900 MHz renewal: found. RÚ decisions (fetched, FDD, whole territory): Orange 2410531004_h_orange_900-mhz-do_2028, Slovak Telekom 2410531005_h_st_900mhz_do_2028 (both "Od 1.1.2026 Do 31.12.2028"), O2 2410531006_h_o2_do-2028 (two blocks "Od 1.1.2026" and "Od 8.9.2026", both "Do 31.12.2028"), all under https://www.teleoff.gov.sk/files/urad/odbory-oddelenia/odbor-spravy-frekvencneho-spektra/zoznam-rozhodnuti-oblasti-spravy-frekvencneho-spektra/vyberove-konania/frekvencne-pasmo-900-mhz/. B8/n8 stays, now cited. 2100: decisions 2510571002/3/4 (O2, Orange, Telekom) "Od 8.9.2026 Do 31.12.2048"; SWAN 2510571001 (5 Aug 2025): 2100 FDD 1970-1980/2160-2170, "Od 8.9.2026 Do 31.12.2048" -> in force today, so SWAN now lists B1/n1 (lte 1,3; nr 1,78). SWAN 900 and 2600 FDD start 2029, still left out, SWAN complete false.
- 1500 MHz (SDL) not listed. Succession: none.
- MVNOs: none verified.

## Hungary (all licensed, complete true) - NMHH per-band documents (no single table exists)
Sources fetched: strategy https://nmhh.hu/dokumentum/216756/NMHH_Radiospektrum_Strategia_2021_2025.pdf ; 2014 award decision https://nmhh.hu/dokumentum/164404/uf_1579288_2014_hatarozat_frekvenciapalyazat.pdf ; 900/1800 auction article https://nmhh.hu/cikk/217525/... ; 2100 band intro (2025) https://english.nmhh.hu/document/254938/2100_GHz_frequency_band.pdf ; 2600 band intro (14 Aug 2025) https://english.nmhh.hu/document/254934/2600_MHz_frequency_band.pdf ; 1800 band intro (2019, read, not listed as source: 1800 is also covered by the 2021 article) https://nmhh.hu/dokumentum/208409/1800MHz_savismerteto_2019_12_03.pdf.
- 700: strategy p.23: "A Magyar Telekom Nyrt. a 700 MHz-es sávban kétszer 10 MHz-et ... A Telenor ... kétszer 5 MHz-et ... A Vodafone ... kétszer 10 MHz-et" (2020 auction, rights to 2035).
- 800: 2014 decision: Telekom "801-811/842-852", Telenor "811-821/852-862", Vodafone "791-801/832-842" (rights to 2029; Telekom and Telenor lease parts to each other, not relevant).
- 900/1800: NMHH 28 Jan 2021 article table: Telekom 16/40 MHz, Telenor 26/40, Vodafone 18/40, valid to 9 Apr 2037.
- 2100: band intro: each of Magyar Telekom, Vodafone, Telenor ("Yettel") "was granted rights of use for 2x15 MHz FDD"; 2020 award added Telekom 2x10, Vodafone 2x5. Telekom/Yettel transferred a 2x5 block in 2024 (still held by one of them).
- 2600 (rights to 15.06.2029): Table 1 of band intro has logos only (read from the rendered page): Telekom 2500-2530/2620-2650; One 2530-2550/2650-2670 and TDD 2575-2600; Yettel 2550-2570/2670-2690. Confirmed in text by the 2014 decision: Telekom package A "2500-2530/2620-2650 ... párosított"; Telenor B "2550-2570/2670-2690"; Vodafone C "2575-2600 MHz ... párosítatlan" (unpaired) and G "2530-2550/2650-2670". Band intro: "TDD frequency band ... unpaired (2570-2620)". -> B7/n7 all; B38/n38 One only. 2600-2615 "Not allocated"; 2600 FDD+TDD left unsold in the 2020 auction.
- 3600: strategy: Telekom 120 MHz, Telenor 140, Vodafone 50 -> n78 all.
- 26 GHz: NMHH 26 GHz briefing (https://nmhh.hu/dokumentum/254233/26_ghz_savismerteto.pdf, fetched) lists fixed-service rights expiring 2027, not mobile -> no n258.
- Succession: band intro 2100: "As of 1 January 2025, Vodafone Hungary Zrt. was renamed to One Magyarország Zrt."; "Telenor Magyarország Zrt. (hereinafter referred to as 'Yettel')".
- 2600 textual proof (fix round 1): the 2025 band-introduction Table 1 is logo-only (graphic); the textual proof of who holds which 2600 block is the 2014 NMHH decision (Telekom A: 2500-2530/2620-2650 paired; Telenor B: 2550-2570/2670-2690 paired; Vodafone G: 2530-2550/2650-2670 paired and C: 2575-2600 unpaired). Risk: the logo table is 2025 and could reflect secondary trades since 2014 that the 2014 text does not; the logos agree with the 2014 text.
- DIGI: held 1800 2x5 MHz (1725-1730/1820-1825, exp. 2029 per the 2019 briefing). Telex 13 Apr 2023 (fetched, https://telex.hu/tech/2023/04/13/a-vodafone-magyarorszagi-halozatara-koltozik-a-digimobil): "Június 1-től a Vodafone Magyarország mobilhálózatán működik tovább a DIGIMobil szolgáltatás" -> DIGI Mobil runs on the Vodafone (now One) network, so it is not a separate network and is listed as an MVNO of hu-one (source kind other, press).
- Completeness caveat: every band is from a regulator document but a mix of 2014-2025 dates; 800 MHz and 2100 holders are as of those docs.
- MVNOs: hu-one: DIGI Mobil (quote above). Telekom, Yettel: none verified.

## Slovenia (all four: basis used, complete false) - AKOS deployment report
AKOS "Pokritost s storitvami mobilnih tehnologij" 24.6.2025 (Feb 2025 data) https://www.akos-rs.si/fileadmin/user_upload/dokumenti/Raziskave__analize__porocila_in_statistika/RF_Spekter/Pokritost_s_storitvami_mobilnih_tehnologij_v_februarju_2025.pdf, and the July 2023 edition (…/Radijski_spekter/Novice_2024/Pokritost_s_storitvami_mobilnih_tehnologij_julija_2023_pop_cistopis.pdf). The AKOS 2021 auction pages (arhiv.akos-rs.si) were unreachable, so no per-operator licence table: basis used (regulator deployment report), complete false.
- A1: LTE "800, 1500, 1800, 2100 in 2600 MHz" -> 20, 32, 3, 1 (2600 omitted: no duplex stated); NR "700 MHz, 2100 MHz in 3600 MHz" -> n28, n1, n78. 
- Telekom Slovenije: LTE "700, 800, 900, 1800, 2100 in 2600" -> 28, 20, 8, 3, 1; NR "700, 2600 in 3600" -> n28, n78 (2600 omitted).
- Telemach: LTE "700, 800, 1800, 2100 in 2300" -> 28, 20, 3, 1, 40; NR "3600" -> n78.
- T-2: LTE "2100 in 2300" -> 1, 40; NR "2300" -> n40.
- Nulls: none (lists given but incomplete: 2600 duplex missing, 900 for Telemach/A1 LTE not stated, snapshot is Feb 2025).
- T-2: Telemach signed an agreement in 2024 to acquire T-2 (search results only, not fetched); AKOS Feb 2025 still reports T-2 separately, so kept separate.
- MVNOs: A1 "bob" (A1 brand): bob.si "zanesljivo A1 omrežje bob signal zagotavlja eden največjih operaterjev v Evropi" (https://www.bob.si/, brand). Others none (izi.si fetched, brand of Telekom, no network sentence).

## Croatia (all licensed, complete true) - HAKOM auction results
https://hakom.hr/en/hakom-dodijelio-spektar-za-mreze-pokretnih-komunikacija/10500 (national 800/900/1800/2100/2600, decision 8 Mar 2023; HTML table) and https://www.hakom.hr/en/hakom-dodijelio-spektar-za-mreze-pokretnih-komunikacija-pete-generacije/9081 (700, 3600, 26 GHz as PNG tables, read by eye).
- 800: A1 2x10, HT 2x10, Telemach 2x10. 900: A1 2x15, HT 2x15, Telemach 2x5. 1800: A1 2x25, HT 2x30, Telemach 2x20. 2100: A1 2x15, HT 2x25, Telemach 2x20. 2600 (paired 2x): A1 2x25, HT 2x25, Telemach 2x20.
- 700: Telemach A03 713-723/768-778; HT A01 723-733/778-788; A1 A02 703-713/758-768.
- 3600: Telemach 3600-3700, HT 3480-3600, A1 3700-3800 (n78).
- 26 GHz: EOLO 27.3-27.5, Telemach 26.5-26.7, HT 26.9-27.3, A1 26.7-26.9 -> n258 (all three; EOLO is not a mobile operator). Regional 3600 holders (Digicom, Markoja) are ISPs, not included.
- All three: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78,258.
- 2600 duplex: the HAKOM table gives "2x25", "2x25", "2x20" MHz, i.e. paired = FDD by definition; accepted as a stated duplex -> B7/n7. No unpaired 2600 row.
- Succession: the HAKOM page already uses the current names (A1 Hrvatska, Hrvatski Telekom, Telemach Hrvatska); no succession claimed.
- MVNOs: none verified (bonbon.hr/simpa.hr are HT brands, no network sentence; tomato.hr empty).

## Nulls / unreachable
No nulls in lte/nr. Unreachable or unusable: arhiv.akos-rs.si, kaktus.cz, lidl-connect.cz, virginmobile.pl, plush site. MVNOs left empty except SI bob.
