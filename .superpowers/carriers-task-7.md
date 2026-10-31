# Carriers task 7: GB, US, CA, AU (read 2026-10-31)

Tests: `tests/test_carriers.py` 36 passed. bands.yaml change: added NR n259 (41 GHz, mmwave) for the UK 40 GHz auction. No other change.
Basis: GB, AU `licensed` (regulator licence tables); US, CA `used`. **complete is false for all 17 networks** (reasons below). No null lte/nr except AT&T and Verizon lte (null: no carrier source for an LTE list could be fetched).
Graphics/OCR: none needed. Every table was HTML or PDF text.
Access: Ofcom, ACMA, T-Mobile, FCC, canada.ca and TELUS returned 403 / timeouts to WebFetch/curl, so I read **web.archive.org copies** of the regulator/carrier pages (snapshot date in the URL; URLs in the yaml are those archive URLs). ISED and Verizon/Rogers/Freedom/Bell/AT&T pages were read live.

## United Kingdom (licensed, complete false x3)
Source: Ofcom "Mobile and wireless broadband below 5 GHz" licence frequency table (snapshot 21 Mar 2026, page updated 12 Mar 2026; lists licences "as of 1 Aug 2025" with dated trades incl. 1/1/26 and 30/9/31) and Ofcom "spectrum auction final results" (24 Oct 2025).
- Table read from the HTML (PDF copy was not fetchable); columns Licensee/Uplink/Downlink/MHz/Comments.
- 700 FDD 2x10 each (O2 703-713, VodafoneThree 713-723, EE 723-733) -> B28/n28. EE also holds 738-758 SDL (not B28; not listed; SDL).
- 800: all three hold paired blocks -> B20/n20. 900: O2 (902.5-914.9) and VodafoneThree (885.1-890.1) -> B8/n8 (EE none).
- 1800: EE 1736.7-1781.7, O2 1710.1-1715.9, VodafoneThree 1715.9-1721.7 + 1721.7-1736.7 -> B3/n3. 2100 (1959.7-1979.7 EE; Vodafone/Telefonica 1934.9-1959.7 shared rows with dates) -> B1/n1 for all.
- 2300: O2 2350-2390 -> B40/n40. 2600 FDD: EE 2520-2570/2640-2690 -> B7/n7. 2600 TDD: O2 2595-2620 (to 30/9/27, then 2570-2620) -> B38/n38.
- 3.4-3.8 GHz: EE 3540-3580, 3680-3720; O2 3410-3460, 3500-3540 etc; VodafoneThree 3460-3500, 3500-3520, 3580-3680 (shared with UKB) -> n78 each.
- 26/40 GHz mmWave (68 high-density areas, 15 years): Ofcom "we have granted licences" 24 Oct 2025: EE 26.7-27.5 + 41.5-42.5; O2 25.1-25.9 + 40.5-41.5; VodafoneThree 25.9-26.7 + 42.5-43.5 -> n258 and n259 (new band).
- Unpaired 1900 MHz: EE 1899.9-1909.9, O2 1909.9-1914.9, Vodafone 1914.9-1920 ("Revoked 3/4/29"). In force today, so mapped to B39/n39 (the only 1900 TDD band in the table). **Concern**: never deployed; it makes China-version phones with B39 look compatible. Drop 39 if you disagree.
- Left out, explained: 1452-1492 SDL (B32/n75, no source says used); VodafoneThree 2570-2595 TDD (row "Vodafone & Telefonica", ends 30/9/27; Ofcom trades text says it moves to Telefonica from 30/9/26, ambiguous) so no B38 for VodafoneThree; 3.9 GHz UK Broadband (UKB, not an MNO); future 700/3.6-3.8 auction (planned 2026, not awarded).
- complete false: the HTML table has no Vodafone 2.6 GHz FDD although Vodafone won 2x20 MHz in the 2013 auction (press only); I cannot tell whether the table omits it, so B7/n7 for VodafoneThree is not claimed and no list is called complete.
- Succession: VodafoneThree (Vodafone+Three, 2025) is one entry. comparebroadbandpackages.co.uk 28 May 2026: "Vodafone and Three have successfully integrated their core and radio access networks" (kind other; wording does not say the old radio networks are switched off). Ofcom licences are held jointly ("Vodafone & Three"). Vodafone took full ownership 2026 (search snippets only).
- MVNOs verified: O2 -> giffgaff ("giffgaff runs on O2's mobile network", help.giffgaff.com), Tesco Mobile ("5G - Powered by O2 network", tescomobile.com). Not verified (pages 403/silent): Sky Mobile, VOXI, Lebara, SMARTY, iD Mobile, Plusnet (page says closed, "part of the same family" as EE). None added.

## United States (used, complete false x3)
Approach: US licences are per market (CMA/PEA); no national holdings table exists, and FCC pages were blocked (403). Bands are what each carrier itself says its network runs, so `basis: used`, `complete: false`. No carrier gave a full national band list I could read, apart from T-Mobile, whose table I treat as not full (below).
- T-Mobile (archive of t-mobile.com/support/coverage/t-mobile-network, 7 Sep 2026): "5GUC: n2/n25 (1900), n41 (2.5 GHz), n258 (24 GHz), n260 (39), n261 (28); 5G Extended Range: n71 (600); 4G LTE: B5 (850), B4 (1700/2100), B66; Extended Range LTE: B12, B71; 2G: B2". LTE B2/B25 and B41 are not listed on that page (2G is B2), n77 not listed; complete false because the page is a customer device-tip table that does not mention the C-band n77 or LTE B2/B41/B25 that T-Mobile is known to run (not claimed without a source).
- AT&T: n5 and n77 ("low-band n5 ... mid-band n77 in the C-Band and 3.45GHz spectrum ranges", AT&T 5G SA blog, archive 8 Jun 2026); FAQ KM1475228: "mid-band 5G+ needs a band n77 capable device; high-band 5G+ needs n260". LTE: not stated on any fetchable AT&T page, left null. Band 14 (FirstNet), 12/17, 2, 4/66, 30, 29 are not claimed. EchoStar spectrum purchase (3.45 GHz, 600 MHz) not closed per any source, so out.
- Verizon: coverage-map page: "devices supporting n77 (C-band), and n260 and n261 (mmWave) bands will have access to all of our 5G Ultra Wideband network" ; business page: C-band 3.7-3.98 GHz. 5G Nationwide is "low-band", no number given. LTE null. n5/n66/n2 DSS and Band 13 not claimed (no carrier page fetched).
- UScellular: wireless operations sold to T-Mobile, closed 1 Aug 2025 (benton.org and convergedigest, fetched; businesswire blocked). The tower/spectrum remainder became Array Digital Infrastructure. No network entry; integration was "in phases" (no end date found).
- Dish/Boost: EchoStar 10-K per Broadband Breakfast: "no customer traffic on its own wireless network since November"; Boost is on AT&T infrastructure. No own network, no entry (spectrum sale to AT&T not confirmed closed).
- MVNOs verified: Cricket Wireless ("Cricket is on the AT&T network!"), Visible ("Visible runs on Verizon's ... 5G network"). Mint (T-Mobile) and Metro: page 403, not added.

## Canada (used, complete false x7)
Approach: licences are by tier/region, and ISED's SMS search is a dynamic application. ISED does publish the monthly **Terrestrial Spectrum Licence Site Data Extract** (download-sms-data page, extract dated 2026-10-05; 1.19 GB CSV, ~2.8 million base-station rows, licensee, technology, tx/rx frequency). I streamed it and classified stations by technology (LTE, 5GNR, 5GDSS) and downlink frequency (TDD when tx = rx). A band is listed when at least 200 stations of that licensee group use it (to drop mislabels), plus the carrier's own page where one exists. This is a regulator deployment record, hence `used`, kind regulator. Complete false: the extract is of site data from the carriers' monthly uploads, not a licence holdings table, and the thresholds are mine.
- Station counts (LTE / NR incl. DSS): Rogers (incl. FIDO) B12/17 44k, B2/25 35k, B4/66 27k, B7 27k, B5 21k, B41 2.0k, B71 0.8k; NR n77/78 79k, n2/25 18k, n71 DSS 100k, n66 DSS 45k, n41 0.7k. Bell (incl. Bell Canada, MTS) LTE B2/25 443k, B4/66 73k, B7 48k, B29 SDL 38k, B12/17 29k, B5 18k, B13 14k, B71 2.6k, B41 0.5k; NR n77/78 148k, n66 50k, n2/25 30k, n5 9k, n71 1.1k. TELUS (3 licensee names) LTE B2/25 98k, B7 33k, B5 20k, B29 17k, B12/17 14k, B13 11k, B71 8k, B30 2k, B4/66 49k; NR n77/78 45k, n66 42k, n71 DSS 17k, n2/25 0.6k.
- Rogers carrier page (rogers.com BYOD, read live): LTE 12, 5, 2 and 25, 4 and 66, 7; 5G n71 (DSS), n66 (DSS), n41, n78. Matches the extract; 41 for LTE and 2/25 for NR come from the extract only. 12 not 17 as Rogers says.
- Bell: carrier page only says 5G+ uses 3500 and 3800 MHz (no band numbers); everything else is the extract. 700 lower: tx 728-746 cannot separate B12 from B17, so both listed for Bell, TELUS, Freedom, TBayTel. Bell's 600 MHz is TELUS's spectrum under RAN sharing (cellmapper wiki, not cited).
- TELUS: archived 600 MHz release (licences in BC, AB, SK, ON, QC) and 3500 MHz deployment release; bands via extract.
- Freedom Mobile / Videotron (same legal entity: "Videotron Ltd., doing business as Freedom Mobile" on freedommobile.ca): Freedom page lists B4, B7, B13, B66, B71 and n66, n71, n77/n78 (complete false: "certain bands are deployed in select locations"); the extract adds B12/17 (2.9k) from Videotron's Quebec sites. Extract tx/rx fields in some Videotron rows are in the 6xx range (uplink), read as B71.
- SaskTel, Eastlink (Bragg Communications), TBayTel: extract only. SaskTel's own support pages (support.sasktel.com) appeared in search snippets but I did not fetch them. Left out: Xplore (rural fixed wireless), Sogetel, Quebec/regional small cells.
- mmWave (n257/n261) and 3800 beyond n77: no stations above 24 GHz in the extract for these operators; not listed. MVNOs: Koodo page does not name the host network; Virgin Plus page 404. None added.

## Australia (licensed, complete false x3)
Source: ACMA "Expiring spectrum licences, stage 3: Supporting paper 1, Overview of expiring licences, incumbent holdings" (Apr 2025; archived 22 Jul 2025), Tables 1-6 list every spectrum licence per MNO with expiry; all expire 2028-2044 (in force today).
- Telstra: 700, 850 (two licences, one to 2044), 1800, 2 GHz, 2.3, 2.5 (incl. Delta Networks entries in Telstra's table), 3.4, 3.7, 26 GHz -> lte 1,3,5,7,28,40; nr +78,258.
- Optus: 700, 850, 900 (to 2044), 1800, 2 GHz, 2.3, 2.5, 3.4, 3.7, 26 -> lte 1,3,5,7,8,28,40.
- TPG (TPG Internet, Vodafone Hutchison/Australia, Mobile JV): 700, 850, 1800, 2 GHz, 3.4 (via Dense Air and Mobile JV), 3.7, 26 -> lte 1,3,5,28; nr 1,3,5,28,78,258. No 2.3 or 2.5 GHz listed (its 2013 2x10 at 2.5 GHz does not appear in Table 5).
- 2.5 GHz mapped to B7/n7 (paired 2500-2690 plan, from the 2013 auction summary in the same paper); 3.4/3.7 GHz to n78 only (no LTE 42/43, as in BG); 26 GHz to n258.
- complete false: the paper states apparatus licences are not included. Vodafone and Telstra 900 MHz (B8) 3G/4G, and other apparatus holdings are therefore not in the list; paper is Apr 2025 (renewal applications open June 2026, no change to licence terms found).
- MVNOs verified: Telstra -> Boost Mobile ("All of our plans are on the full Telstra Prepaid Mobile Network"), ALDI Mobile ("uses the Telstra Wholesale Mobile Network"). amaysim page silent, Lebara 503; none added for Optus or TPG.

## Concerns
1. All regulator pages for GB/AU were read from web.archive.org copies, not live.
2. B39/n39 for the three UK networks (unused unpaired 1900 licences) per the in-force rule.
3. Canada bands derived by my own classification of ISED site data; thresholds (200 stations) and the B12/B17 ambiguity are judgement.
4. US AT&T and Verizon LTE are null; T-Mobile lacks n77/B2/B41/B25 (sources do not state them).
