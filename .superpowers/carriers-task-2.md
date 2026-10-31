# Carriers task 2: DE, AT, NL, BE, LU (rewritten under the amended rule; read 2026-10-31)

Mapping used for regulator tables (FDD ranges, unambiguous): 700 FDD -> B28/n28; 800 -> B20/n20; 900 -> B8/n8; 1800 -> B3/n3;
2100 -> B1/n1; 2600 FDD -> B7/n7; 2600 TDD -> B38/n38; 3.4-3.8 GHz TDD -> n78 (no LTE band listed); 26 GHz -> n258.
1400/1500 MHz SDL (B32, n75/n76) left out everywhere: no regulator or carrier source says it is used that way.
basis is `licensed` for every network (all lists come wholly or partly from regulator licence data); "used" evidence is kept as extra sources.

## Germany (all four: basis licensed, complete true)
Regulator table: Bundesnetzagentur "Drahtloser Netzzugang in den Bereichen von 700 MHz bis 3,8 GHz", Stand 29.01.2026,
https://www.bundesnetzagentur.de/SharedDocs/Downloads/DE/Sachgebiete/Telekommunikation/Unternehmen_Institutionen/Frequenzen/OffentlicheNetze/Mobilfunk/DrahtloserNetzzugang/UebersichtFrequenzbereiche.pdf
(a one-page colour chart, legend 1&1 / Telefónica / Telekom / Vodafone; I read it as an image). Rows read per band (operators holding blocks): 700 MHz gepaart: Telefónica, Telekom, Vodafone; 800 MHz gepaart: Telefónica, Vodafone, Telekom; 900 MHz gepaart: Telefónica, Vodafone, Telekom; 1500 MHz: Telekom, Vodafone; 1800 MHz gepaart: Telekom, Telefónica, Vodafone; 2100 MHz gepaart: Vodafone, Telefónica, 1&1, Telekom; 2600 MHz gepaart: Vodafone, Telekom, Telefónica, plus 1&1 marked "Überlassung" (leased); 3600 MHz (3400-3610): Vodafone, 1&1, Telefónica, Telekom.
Colour reading is by eye, so the weakest point is operator attribution of individual blocks; the pattern (three incumbents in every low/mid band, 1&1 only 2100/2600/3600) matches the BNetzA press text ("The spectrum is currently being used by the three established mobile network operators"; 1&1 "cannot directly acquire its own spectrum"; Telefónica leases 2600 to 1&1).
- Telekom: lte 1,3,7,8,20; nr 1,3,7,8,20,28,78. LTE 28 left out: Telekom says "Die Telekom nutzt den 700-MHz-Bereich ausschließlich für 5G" (teltarif 2025 quote of Telekom; telekom.com 2022: "Telekom is now using ... 700 megahertz (MHz)" for 5G). 1500 MHz: carrier lists it ("90 Prozent der Standorte erhalten zusätzlich Mid-Band-Frequenzen: 1.500, 1.800 und 2.100 MHz", telekom.com 2026/04) but names no technology, so B32 left out (changed from the first draft). Used evidence: "the 800, 900, and 1,800 MHz Frequencies can each serve as an anchor ... 1,800 MHz and 2,600 MHz also serve as anchors for 5G at 3.6 GHz"; 5G on "3.6 GHz" and "2.1 GHz".
- Vodafone: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78. Used evidence (carrier): "Vodafone hat sich die Frequenzen 3,5 Gigahertz und 1,8 Gigahertz gesichert ... dritte Frequenz (700 Megahertz)"; LTE "bündelt die Frequenzbänder aus den 800er, 1800er und 2600er MHz-Bereich". No source says 700 is unused for LTE, so B28 kept as licensed. 1500 MHz (chart) left out.
- O2 Telefónica: lte 1,3,7,8,20,28; nr same + 78 (1,3,7,8,20,28,78). Used evidence: "comprehensive 4G capacities (800 MHz, 1800 MHz, 2100 MHz and 2600 MHz)" (telefonica.de 2022/05); 5G "700 megahertz, 3.6 gigahertz and 1800 megahertz (DSS)" (2023/10). 900 MHz is licensed (chart) though O2 describes it as 2G.
- 1&1: lte 1,7; nr 1,7,78. Chart: 2100 (1&1 blocks), 2600 leased, 3600 (5 x 10 MHz). 1&1's own pages name no bands, so this is purely licence data; note 1&1 also roams on Vodafone/Telefónica (not counted).
- MVNOs (unchanged): congstar (congstar.de/hilfe-service/netzabdeckung/: "Mit einem congstar Tarif surfst du automatisch im Mobilfunknetz der Telekom"); Lidl Connect (kundenkonto.lidl-connect.de/faq-v2.html refers to the "deutschen Vodafone-Netz", Vodafone GmbH is service provider; indirect); ALDI TALK (alditalk.de/netzabdeckungskarte: "Netzbetreiber: Telefónica Germany GmbH & Co. OHG."). None for 1&1 (none verified).

## Austria (all three: basis licensed, complete true)
Regulator table: RTR "Spektrum je Betreiber", https://www.rtr.at/TKP/was_wir_tun/telekommunikation/spectrum/framework/FRQshare.de.html (page "Stand: 10.05.2026"). I used the period "29.04.2024 – 31.12.2026" (current today). Rows (A1 Telekom | T-Mobile | Hutchison): 700 FDD: – | 2x20 | 2x10; 800 FDD: 2x20 | 2x10 | –; 900 FDD: 2x15 | 2x15 | 2x5; 1500 SDL: 30 | 20 | 30; 1800 FDD: 2x35 | 2x20 | 2x20; 2100 FDD: 2x25 | 2x15 | 2x20; 2600 FDD: 2x25 | 2x20 | 2x25; 2600 TDD: 25 | – | 25; 3400 TDD: 100 | 110 | 100; 26 GHz: 400 | 400 | 600. (2300 TDD 60 MHz for T-Mobile starts 2027, so left out.)
- A1: lte 1,3,7,8,20,38; nr 1,3,7,8,20,38,78,258. No 700.
- Magenta (T-Mobile): lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78,258. No 2600 TDD.
- Drei (Hutchison): lte 1,3,7,8,28,38; nr 1,3,7,8,28,38,78,258. No 800.
- Used evidence kept in the earlier RTR channel table (https://www.rtr.at/.../Channels.de.html, per-channel technology) and is still listed as a second regulator source; it agrees (e.g. "700 MHz NR: H3A 10 MHz; T-Mobile 20 MHz", "3.4 GHz NR: A1/T-Mobile/Hutchison 100 MHz", "2100 NR: A1 TA: 25 MHz"). 26 GHz: A1 also states it acquired 400 MHz at 26 GHz (a1 newsroom, from search results). Whether n258 is deployed is not established; it is listed as licensed.
- MVNOs: drei.at blog table (drei.at/de/planet-drei/blog/artikel/vorwahl-handynetze-oesterreich.html): Yesss! and bob -> "A1 Telekom Austria AG"; HoT -> "T-Mobile Austria GmbH"; Spusu -> "Hutchison Drei Austria GmbH". yesss.at: "yesss! Kunden telefonieren und surfen im Netz von A1."

## Netherlands (all three: basis licensed, complete FALSE)
Regulator sources found hold only the 2020 and 2024 auctions, not the older 800/900/1800/2600 licences, so each list is partial:
- Kamerstuk 24 095 nr. 525 (21 July 2020, letter from the State Secretary; the Agentschap Telecom ran the auction), https://zoek.officielebekendmakingen.nl/kst-24095-525.pdf: table "700 MHz band | 1400 MHz band | 2100 MHz band: KPN 2 | 3 | 4; T-Mobile NL 2 | 2 | 4; VodafoneZiggo 2 | 3 | 4"; "Alle geveilde vergunningen lopen tot en met 31 december 2040". -> B28/n28, B1/n1 for all; 1400 left out.
- rijksoverheid.nl news 2024-07-01, https://www.rijksoverheid.nl/actueel/nieuws/2024/07/01/kpn-odido-en-vodafoneziggo-winnaars-veiling-nederlandse-5g-netwerken: "KPN, Odido en VodafoneZiggo kunnen hierdoor al vanaf juli 2024 deze frequenties in gebruik nemen" (3.5 GHz band) -> n78 for all. The page gives no MHz split (search results say 100 MHz each, from non-regulator sources).
- All three: lte 1,28; nr 1,28,78. Still not covered by any regulator source I could open: 800, 900, 1800, 2600 licences (RDI frequency register not reachable; RDI pages list no per-operator holdings).
- Used evidence (carrier): KPN "We have provided 5G coverage throughout the Netherlands via the 700 MHz band ... already installed the 3.5 GHz band in the busiest places" (kpn.com/overons/nieuws/en/the-next-phase-of-5g-arrives-today/). Odido "We gebruiken nu de 3,5 GHz-frequentie" (odido.nl/blog/5g-boost). VodafoneZiggo: "Vodafone acquired frequencies in the 700, 1400 and 2100 MHz bands" (vodafoneziggo.nl/en/nieuws/vodafone-first-offer-nationwide-5g/).
- KPN's old community post says 700 MHz is not used for 4G ("Zover ik weet", 2019, hedged); not treated as authoritative, so B28 stays on the LTE list as licensed.
- MVNOs (unchanged): Simyo and Youfone (KPN: simyo.nl "Netwerkinfo van Simyo, op het KPN netwerk"; youfone.nl blog "Wij maken gebruik van het premium KPN-netwerk"), hollandsnieuwe (hollandsnieuwe.nl/3g: "We maken gebruik van het betrouwbare 5G-netwerk van Vodafone"), Ben (ben.nl: "Namelijk het netwerk van Odido.").

## Belgium (all three: basis licensed, complete FALSE)
- BIPT "Results of the 2022 multi-band auction", https://www.bipt.be/operators/results-of-the-2022-multi-band-auction: rights granted: "700 MHz: Citymesh Mobile, Orange Belgium, Proximus, Telenet Group"; "3600 MHz: Citymesh Mobile, Network Research Belgium, Orange Belgium, Proximus, Telenet Group"; "900, 1800, 2100 MHz: Citymesh Mobile, Orange Belgium, Proximus, Telenet Group"; "1400 MHz: Orange Belgium, Proximus, Telenet Group". -> B28/n28, B8/n8, B3/n3, B1/n1, n78 (1400 left out).
- BIPT decision of 7 January 2025 (renewal of 2600 MHz rights), https://www.bipt.be/sectors/publication/decision-of-7-january-2025-regarding-the-renewal-of-the-2600-mhz-rights-of-use: rights "allocated to Proximus N.V., Citymesh Air N.V., Telenet group N.V. and Orange Belgium N.V." and renewed until 30 June 2032 -> B7/n7 (the page does not say FDD vs TDD or MHz; FDD assumed, flagged).
- All three: lte 1,3,7,8,28; nr 1,3,7,8,28,78. complete false because no regulator source for the 800 MHz holders (the 2013 award is not on a page I could open), so B20/n20 is missing.
- Used evidence kept: Proximus "Proximus uses spectrum in the 3.6-3.8 GHz band" (proximus.com/news/2020/20201217-5g-spectrum.html); Telenet "The spectrum is granted at 3.6 GHz and 3.8 GHz" (press.telenet.be launch release); Orange: only "temporary spectrum allowed by ... BIPT", no band named.
- Not included as networks: Citymesh Mobile / Citymesh Air (Digi), Network Research Belgium: hold spectrum but no deployed public network sourced.
- MVNOs (unchanged): Scarlet on Proximus (scarlet.be support: "We use the mobile network of Proximus."); edpnet on Orange (corporate.orange.be/en/about-orange/partnerships: "With this MVNO agreement, edpnet"); none for Telenet (none verified current).

## Luxembourg (all three: basis licensed, complete true)
Regulator table: ILR consultation CP/F24/1 (26 April 2024), Tables 1 and 2, https://www.ilr.lu/wp-content/uploads/consultation/ilr-fre-cp-20240426_CP-F24-1_Document-de-consultation.pdf. Rows (holder; "Entreprise des Postes & Télécommunications" = POST; "Tango S.A. devenu Proximus"):
- 700: 703-713/758-768 Orange; 713-723/768-778 POST; 723-733/778-788 Proximus -> B28/n28.
- 3.4-3.75 GHz: 3420-3530 POST; 3530-3540 Luxembourg Online; 3540-3650 Orange; 3650-3750 Proximus -> n78.
- 2100: 1920-1935/2110-2125 POST; 1935-1950/2125-2140 Orange; 1950-1965/2140-2155 Proximus; 1965-1980/2155-2170 Luxembourg Online -> B1/n1.
- 900: 890.1-894.7... POST; 895.1-899.7... Proximus; 880.1-889.9/925.1-934.9 Orange -> B8/n8. 1800: 1760-1785/1855-1880 POST; 1735-1760 Proximus; 1710.1-1735/1805.1-1830 Orange -> B3/n3.
- 800: 791-801/832-842 POST; 801-811/842-852 Proximus; 811-821/852-862 Orange -> B20/n20. 2600 FDD: 2500-2520/2620-2640 POST; 2540-2560/2660-2680 Proximus; 2520-2540/2640-2660 Orange -> B7/n7 (2570-2620 TDD and 2560-2570/2680-2690 FDD unassigned).
- All three: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78. complete true (full licence tables); caveat: table dated April 2024; 800/900/1800/2600 licences expire 2027.
- Used evidence (not required now): POST "700 MHz and 3.6 GHz ... awarded" + launch Oct 2020; Orange 2020 release; none names deployed bands. Luxembourg Online (3530-3540 MHz and 1965-1980/2155-2170 MHz) not listed as a network: no public mobile network sourced.
- MVNOs: none verified, none listed.

## Counts
Complete lists: DE 4/4, AT 3/3, LU 3/3, NL 0/3, BE 0/3. No lte/nr left null any more.
## Unusable or missing sources
telekom.de pages need login; several post.lu pages 404; vodafoneziggo community 403; RDI/ACM register of per-operator 800/900/1800/2600 licences not found; BIPT 800 MHz holders not found; the BNetzA chart gives band blocks only graphically (read from the rendered PDF).
