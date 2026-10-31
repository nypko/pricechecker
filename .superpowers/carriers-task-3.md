# Carriers task 3: FR, IT, ES, PT, MT (amended rule; read 2026-10-31)

Mapping used for regulator tables: 700 FDD -> B28/n28; 800 -> B20/n20; 900 -> B8/n8; 1800 -> B3/n3; 2100 -> B1/n1;
2600 FDD -> B7/n7; 2600 TDD -> B38/n38; 3.4-3.8 GHz -> n78 (no LTE band); 26 GHz -> n258.
1400/1500 MHz SDL (B32, n75/n76) left out everywhere (no source says it is used).
Bands config/bands.yaml: nothing missing, no change. README: one line added (38 lines).
Tests: 36 passed.

## Summary
FR 4/4 complete, IT 4/4 complete, MT 2/3 complete (Epic false), ES 0/4 (partial), PT 0/4 (ANACOM unreachable, see below).

## France (all four: basis licensed, complete true)
Regulator table: ARCEP "Le patrimoine de fréquences des opérateurs mobiles" (updated 9 July 2026),
https://www.arcep.fr/la-regulation/grands-dossiers-reseaux-mobiles/la-couverture-mobile-en-metropole/le-patrimoine-de-frequences-des-operateurs-mobiles.html
It lists per operator the authorisation (AUF) per band, with expiry, no MHz. Rows per operator:
- Orange, SFR, Bouygues: 700 MHz (exp. 07/12/2035), 800 MHz (16/01/2032), 900 and 1800 MHz (2031/2034), 2.1 GHz (2030-2032), 2.6 GHz (10/10/2031), 3.4-3.8 GHz (17/11/2035).
- Free: 700 MHz (07/12/2035), 900 and 2.1 GHz, 900 MHz, 1800 MHz (11/10/2031), 2.1 GHz, 2.6 GHz (10/10/2031), 3.4-3.8 GHz. No 800 MHz row for Free.
- No 26 GHz row for anyone (so no n258).
Duplex: the page does not say. ARCEP PDF "Les attributions de fréquences aux opérateurs de réseaux mobiles ouverts au public" (Nov 2020, pdftotext, text labels not a graphic read): 2.6 GHz drawn only as "FDD montant" 2500-2570 / "FDD descendant" 2620-2690, four blocks (15, 20, 15, 20 MHz); 2570-2620 TDD is not in the chart. So 2.6 GHz -> B7/n7 only, no B38. Same PDF: 800 "FDD", 700 "FDD", 1800/2100 FDD, 3490-3800 blocks 80/70/70/90 (four operators).
Which block belongs to which operator in the PDF is by colour (not used); the HTML page gives the operator attribution.
- Orange / SFR / Bouygues: lte 1,3,7,8,20,28; nr 1,3,7,8,20,28,78.
- Free Mobile: lte 1,3,7,8,28; nr 1,3,7,8,28,78 (no 800).
- Carrier statements: none found that a band is switched off; nothing excluded.
- MVNOs: RED by SFR on SFR (red-by-sfr.fr: "vous bénéficiez de la puissance du réseau SFR"); NRJ Mobile on Bouygues (nrjmobile.fr FAQ: "NRJ Mobile propose des offres 4G sur le réseau mobile Bouygues Telecom pour communiquer dans les meilleures conditions."); Lycamobile on Bouygues (lycamobile.fr offer line: "Réseau national • Bouygues Télécom", weaker: it is an offer label, not a network sentence). Orange and Free: none verified (sosh.fr empty on fetch, Free site unreachable). Auchan Telecom only says "Cartes de couverture sur bouyguestelecom.fr", left out. La Poste Mobile is mid-migration SFR to Bouygues per third parties only, left out.

## Italy (all four: basis licensed, complete true)
Sources (AGCOM, both fetched as PDF, text extracted):
(a) Allegato A to delibera 154/25/CONS, Tabella 1 "stato delle assegnazioni dei diritti d'uso delle bande 800, 900, 1400, 1800, 2100, 2600 e 3500 MHz i cui diritti d'uso scadono nel 2029", https://www.agcom.it/sites/default/files/media/allegato/2025/Allegato_A_Delibera_154-25-CONS.pdf. Rows (holders, MHz): 800 FDD 2x30: TIM 2x10, Wind Tre 2x10, Fastweb-Vodafone 2x10; 900 FDD 2x35: Iliad 2x5, TIM 2x10, Wind Tre 2x10, FV 2x10; 1400 SDL (left out); 1800 FDD 2x70: Iliad 2x10, TIM/WT/FV 2x20; 2100 FDD 2x60: Iliad 2x10, TIM 2x15, WT 2x20, FV 2x15; 2570-2600 TDD 30: Wind Tre 30; 2600 FDD 2x60 (2510-2570/2630-2690): Iliad 2x10, TIM 2x15, WT 2x20, FV 2x15; 3500 TDD 120 (3440-3500, 3540-3600): TIM 20, Wind Tre 60 (20 in Bolzano), FV 40 (80 in Bolzano). The PDF layout prints Iliad's line above the band row; I assigned it by arithmetic (sums: 800 3x10=30, 900 5+3x10=35, 1800 10+3x20=70, 2100 10+15+20+15=60, 2600 10+15+20+15=60) and it agrees with (b) where Iliad has 800 = 0.
(b) Allegato A to delibera 315/21/CONS Table 2 (dotazione spettrale, MHz, excl. 3.4-3.6), https://www.agcom.it/sites/default/files/migration/attachment/Allegato%2021-10-2021.pdf: 700: TIM 20, Vodafone 20, Wind Tre 0, Iliad 20; 3600-3800: TIM 80, Vodafone 80, Wind Tre 20, Iliad 20; and paragraph 41: the 26 GHz award "conclusa con l'assegnazione a 5 operatori (TIM, Vodafone, Wind Tre, Iliad e Fastweb) di 200 MHz ciascuno". Delibera 169/25/CONS (fetched) confirms Wind Tre now holds 80 MHz in 3.4-3.8 GHz.
- TIM, Vodafone (Fastweb+Vodafone, one network): lte 1,3,7,8,20,28; nr + 78, 258.
- WindTre: lte 1,3,7,8,20,38; nr 1,3,7,8,20,38,78,258 (2570-2600 TDD 30 MHz -> B38/n38; no 700). AGCOM earlier said no effective roll-out on that TDD block was observed (search snippet, not fetched in context) so B38 is licensed only.
- Iliad: lte 1,3,7,8,28; nr 1,3,7,8,28,78,258 (no 800; 3.7 GHz 20 MHz; 26 GHz 200 MHz).
- Caveat: 700/3.7/26 GHz rows are from a 2021 document; later transfers outside 3.4-3.8 are not covered. Iliad has leased/shared 26 GHz blocks to others (Open Fiber, Zefiro) but still holds the licence.
- MVNOs: none verified. ho. Mobile, Very Mobile, CoopVoce, Kena official pages do not name the host network on fetch. PosteMobile moved to TIM (TGPoste press only), left out.

## Spain (all four: basis licensed, complete FALSE, partial)
No single regulator table of holdings found. Lists are the bands that regulator documents I read attribute to each operator; 800, 2100 and 2600 FDD are NOT listed (no source read), hence incomplete.
- 700 MHz: Orden of 22 Oct 2021, BOE-A-2021-17233 (https://www.boe.es/diario_boe/txt.php?id=BOE-A-2021-17233): concession 1 "2 × 10 MHz ... TME" (Telefónica), 2 "2 × 10 MHz ... Vodafone", 3 and 4 "2 × 5 MHz ... Orange" each. Digi none. -> B28/n28 for Movistar, Vodafone, MasOrange.
- 900/1800: Real Decreto 458/2011, BOE-A-2011-5936: art. 4.2 "Se autoriza a Telefónica Móviles de España, S.A.U. y a Vodafone España, S.A.U." (900), art. 4.3 France Telecom keeps "5 MHz pareados" (900), art. 5.2 all three authorised in 1800 (each returns a 4.8 MHz paired block). Plus Orden ITC/3470/2011, BOE-A-2011-19979: "B2 2x4,8MHz Estatal 900 MHz Telefónica". -> B8/n8, B3/n3 for Movistar, Vodafone, MasOrange (France Telecom España = Orange, now MasOrange; successor not stated in the text).
- 2600 TDD: same ITC/3470/2011 table: "E1_i 10MHz (TDD) Estatal 2,6 GHz FranceTelecom; E1_ii, E1_iii 10MHz (TDD) Estatal Vodafone" (Ministry results note, 10 Nov 2011, also read). -> B38/n38 for Vodafone and MasOrange. The first 2011 auction (800, 2.6 FDD) results could not be read (digital.gob.es press page body truncated; BOE-A-2011-19979 has no 800 awards), so 800 and 2600 FDD are unlisted.
- 3.4-3.8 GHz: CNMC Informe económico sectorial 2025, 9 Jun 2026 (https://www.cnmc.es/sites/default/files/6641332.pdf, pdftotext): "en 2016, 2018 y 2021 ... adjudicatarios los tres principales operadores del mercado (Movistar, Orange y Vodafone). Grupo MASMOVIL ... 80MHz (de los cuales 20MHz se han desinvertido a favor de DIGI ...)". -> n78 for Movistar, Vodafone, MasOrange, and Digi (20 MHz).
- 26 GHz: Orden ETD/114/2023, BOE-A-2023-3490: concessions 1,2 Orange Espagne; 6,7 Vodafone España; 8-12 Telefónica Móviles España (25.10-27.50 GHz); 26 Globe Operator (regional). -> n258. VODAFONE CAVEAT: search results (bandaancha, mobileworldlive) say Vodafone Spain returned its 26 GHz concession; both returned 403 so I have no quote, and found no BOE resolution. Per rule 4 it stays listed (licensed per BOE order); flag for review.
- LTE B28: CNMC report footnote 30: operators "utilizan dicha banda de frecuencia también para maximizar la cobertura de tecnología 4G ... (DSS)" (not per operator).
- Movistar lte 3,8,28 nr 3,8,28,78,258; Vodafone lte 3,8,28,38 nr 3,8,28,38,78,258; MasOrange same as Vodafone; Digi lte null (no regulator source read for its 1800/2100 blocks; press says 2x10 at 1800, 2x10 at 2100, 20 MHz at 3.5 GHz, unfetched), nr 78.
- Digi network: CNMC says "DIGI, que este año ha iniciado el despliegue de su propia red móvil". Xfera/Yoigo is inside MasOrange.
- MVNOs: O2 on Movistar (o2online.es: "Tecnología 5G+ de Telefónica", "Cobertura de Telefónica"); Lowi on Vodafone (lowi.es: "Disfruta de la velocidad 5G de Vodafone", "Lowi es una marca registrada de Vodafone España, S.A.U."). Pepephone, Simyo, Jazztel pages name no network, left out.

## Portugal (all four: basis used, complete false, mostly null) - ANACOM UNREACHABLE
www.anacom.pt refused connections from this machine (curl timeout, WebFetch ECONNREFUSED, 3 tries over the session), so no regulator source could be read and `licensed` was impossible. Draft renewal decision (ANACOM, 29 Jun 2026) and the 2021 auction report exist but were not readable. Only carrier-confirmed use is listed:
- NOS: lte 3, 20 from nos.pt/en/institucional/wholesale/network: "4G network deployed over 800Mhz and 1,800Mhz." nr null.
- MEO, Vodafone, DIGI: lte/nr null. Vodafone press release (2021) table lists holdings (700 2x10, 800 2x10, 900 2x5+2x5, 1800 2x6+2x14, 2.1 GHz 2x20, 2.6 GHz 2x20+25, 3.6 GHz 90) but is a holdings statement by the carrier, not regulator data, and says nothing about use, so not used for the list. digi.pt only says "A rede móvel 5G da DIGI já está disponível em todas as linhas do Metropolitano de Lisboa."
- Not included: NOWO (acquired by DIGI), Dense Air (wholesale 5G holder).
- MVNOs: none verified.
Recommended follow-up: rerun PT from a network that can reach anacom.pt (SPD_renovacao_SCET_finalPublica_20260629.pdf, contentId=1851157, and the 2021 5G auction final report) to upgrade to licensed + complete.

## Malta (GO complete, Melita complete, Epic complete FALSE; basis licensed)
Regulator register: MCA Spectrum Licensing page, https://www.mca.org.mt/regulatory/authorizations_licensing/spectrum-licensing (no date on page; file names carry 2026-01/2026-07). Entries (link text): 800 MHz: GO plc, Melita Limited, Epic Communications Limited; 900-1800 MHz: GO plc "900 -1800 MHz", Epic "900 - 1800 MHz", Melita "900 MHz" only; 2100 MHz: GO, Melita, Epic; 2600 MHz: GO plc, Epic only; 3600 MHz: GO, Melita, Epic. No 700 or 26 GHz licence listed (MCA search result says offered, no interest).
2600 duplex read from the licence PDFs (scanned, read by OCR of rendered pages, i.e. from a graphic): GO "MCA/L/18-3174" Annex I: "Spectrum for Frequency Division Duplex (FDD) operation: Channel 1: 2500 - 2505 MHz / 2620 - 2625 MHz ... Channel 8" -> B7/n7 only. Epic "MCA/L/20-4091": FDD channels 9-14 (2540-2570 / 2660-2690 MHz) plus "Spectrum for Time Division Duplex (TDD) or FDD Downlink (FDD external) operation: Channels 1 - 5: 2570 - 2595 MHz" -> B7/n7 and B38/n38. Because the Epic block is "TDD or FDD downlink", Epic is complete: false.
- GO: lte 1,3,7,8,20; nr 1,3,7,8,20,78. Melita: lte 1,8,20; nr 1,8,20,78 (no 1800, no 2600). Epic: lte 1,3,7,8,20,38; nr same + 78.
- Not opened: the 800, 900-1800, 2100, 3600 licence PDFs (page names them only); 1800 for Melita absent from the list.
- MVNOs: none verified.

## Counts / nulls
Complete: FR 4/4, IT 4/4, MT 2/3, ES 0/4, PT 0/4.
Null: ES-Digi lte; PT MEO/Vodafone/DIGI lte and nr; PT NOS nr.
## Unusable or missing sources
anacom.pt (all), mobileworldlive/bandaancha (403), first Spanish 2011 auction results (800, 2.6 FDD), MIMIT bando-5g (connection refused), many MVNO sites (ECONNREFUSED/empty).
## Attributions read from a graphic
Malta GO/Epic 2600 licence duplex (scanned PDF, OCR). France 2020 PDF text labels were extractable (not a graphic read); Italian block ownership from tables with text (arithmetic check).
