# Carriers task 2: DE, AT, NL, BE, LU (checked 2026-10-31)

Quotes are exact; German/Dutch/French translated in brackets where noted. "Regulator page" for AT is RTR's per-channel technology table.
Band numbers: 2100=B1/n1, 1800=B3/n3, 2600=B7, 900=B8, 800=B20, 700=n28, 3.4-3.8 GHz=n78, 1500=B32.

## Germany (BNetzA data not used; carrier pages)
### Telekom: lte 1,3,7,8,20,32 | nr 1,28,78
- telekom.com/en/newsroom/topic-hubs/networks/these-are-the-5g-frequencies-telekom-uses-in-germany: "Telekom uses two 5G Frequency bands in Germany." "One band is in the 3.6 gigahertz (GHz) range. The second operates at 2.1 GHz." (-> n78, n1). "the 800, 900, and 1,800 MHz Frequencies can each serve as an anchor" (-> LTE B20, B8, B3); "The 1,800 MHz Frequency and the 2,600 MHz Frequency also serve as anchors for 5G at 3.6 GHz." (-> B7).
- telekom.com/en/.../2022/6/telekom-uses-700-mhz-frequency-for-5g-for-the-first-time: "Telekom is now using a new frequency in its 5G network: 700 megahertz (MHz)." (-> n28)
- telekom.com/de/.../2026/04/telekom-nimmt-65-neue-mobilfunkstandorte-in-betrieb: "Alle Standorte nutzen künftig Low-Band-Frequenzen: 700, 800 und 900 Megahertz (MHz)." "90 Prozent der Standorte erhalten zusätzlich Mid-Band-Frequenzen: 1.500, 1.800 und 2.100 MHz." (-> B1 LTE 2100; B32 1500 MHz). Weakest: B1 and B32 rest on this line (technology not named per band); 1500 MHz in DE is the supplemental-downlink band (B32).
- MVNO congstar: congstar.de/hilfe-service/netzabdeckung/: "Mit einem congstar Tarif surfst du automatisch im Mobilfunknetz der Telekom".

### Vodafone: lte 3,7,20 | nr 3,28,78
- vodafone.de/featured/digital-life/5g-wellenlaenge-...: "Vodafone hat sich die Frequenzen 3,5 Gigahertz und 1,8 Gigahertz gesichert." "Vodafone nutzt aber noch eine dritte Frequenz (700 Megahertz)" (-> n78, n3, n28).
- unternehmen.vodafone.de/newsroom/vodafone-technik-einfach-erklaert-zu-5g-midband: "Seit dem Frühjahr bringt Vodafone 5G zusätzlich mit Frequenzen im Low-Band (700 Mhz) in die Fläche."; Mid-Band (1,8 GHz) city rollout; High-Band 3,5 GHz.
- unternehmen.vodafone.de/newsroom/ueberall-frequenzen-...: "Mit den durchdringungsstärksten 800 Megahertz Frequenzen bringt Vodafone LTE so weit in abgelegene Gebiete"; "bündelt die Frequenzbänder aus den 800er, 1800er und 2600er MHz-Bereich" (-> B20, B3, B7).
- Not listed (no source): LTE 2100/900, NR n1.
- MVNO Lidl Connect: kundenkonto.lidl-connect.de/faq-v2.html mentions "deutschen Vodafone-Netz" in roaming footnotes and names Vodafone GmbH as service provider ("erbringt Dienstleistungen an Endkunden aufgrund der Allgemeinen Geschäftsbedingungen für Vodafone-Dienstleistungen"). Indirect evidence, flagged.

### O2 Telefónica: lte 1,3,7,20 | nr 3,28,78
- telefonica.de/.../2022/05/better-network-for-events-and-emergencies-...: "comprehensive 4G capacities (800 MHz, 1800 MHz, 2100 MHz and 2600 MHz)" and 5G at 3.6 GHz.
- telefonica.de/.../2023/10/5g-plus-launches-...: 5G Plus "exclusively uses frequencies designated for 5G ... which currently include 700 megahertz, 3.6 gigahertz and 1800 megahertz (DSS)" (-> n28, n78, n3).
- MVNO ALDI TALK: alditalk.de/netzabdeckungskarte: "Netzbetreiber: Telefónica Germany GmbH & Co. OHG." (legal note 1; service provider E-Plus Service GmbH).

### 1&1: lte null, nr null
- unternehmen.1und1.de/o-ran-mobilfunknetz, 1und1.de/magazin/..., 2023 press release: none names the bands of the 1&1 network ("Als vierter Netzbetreiber setzt 1&1 auf ein Open-RAN-Netz"). 1&1 also uses national roaming (Vodafone/Telefónica), so bands are not inferable. No MVNOs listed (none verified).

## Austria (regulator RTR "Kanäle und Technologien": https://www.rtr.at/TKP/was_wir_tun/telekommunikation/spectrum/framework/Channels.de.html)
The page lists, per band, the technology and bandwidth operators run (A1 TA, T-Mobile, Hutchison; "H3A" read as Hutchison Drei Austria, "TMA" as T-Mobile Austria). Page says NR use will grow, GSM/LTE decline. Carrier-side confirmation not fetched (a1.net technology FAQ names no bands), so the single source is the regulator's deployment table.
- A1: "800: LTE A1 TA: Kanal 6250 (20 MHz)"; "1800 LTE: A1 TA: 20 MHz + 15 MHz (inband-CA)"; "2600 LTE: A1 TA: Kanal 2850 (20 MHz)"; "2100 NR: A1 TA: 25 MHz"; "3.4 GHz NR: A1 100 MHz + regional 20..80 MHz" -> lte 20,3,7; nr 1,78. A1 has no 700.
- Magenta (T-Mobile): 700 NR "T-Mobile: 20 MHz"; 800 LTE "Kanal 6400 (20 MHz)"; 900 LTE "TMA: 5/10 MHz" (assumes TMA = T-Mobile Austria; weakest row); 1800 LTE "T-Mobile: 20 MHz"; 2100 LTE "T-Mobile 15 MHz"; 2600 LTE "Kanal 3050 (20 MHz)"; 3.4 GHz NR "T-Mobile 100 MHz + regional 40..60 MHz" -> lte 1,3,7,8,20; nr 28,78.
- Drei (Hutchison): 700 NR "H3A: 10 MHz"; 900 LTE "Hutchison: Kanal 3632 (3 MHz) oder 5 MHz"; 1800 LTE "Hutchison: 15 MHz"; 2100 LTE "Hutchison: 15 MHz bzw. 20 MHz"; 2600 LTE "Hutchison Kanal 3350 (20 MHz) + 5 MHz"; 3.4 GHz NR "Hutchison 100 MHz" -> lte 1,3,7,8; nr 28,78. No 800 for Drei.
- MVNO evidence (drei.at/de/planet-drei/blog/artikel/vorwahl-handynetze-oesterreich.html, table of prefixes -> network operator): Yesss! and bob under "A1 Telekom Austria AG"; HoT under "T-Mobile Austria GmbH"; Spusu under "Hutchison Drei Austria GmbH". Also yesss.at/fragen/internet-netz-roaming: "yesss! Kunden telefonieren und surfen im Netz von A1." bob.at/service/netzabdeckung: bob now A1 (from 2026-07-13, per search snippet; page not fetched).

## Netherlands
### KPN: lte null | nr 28,78
- kpn.com/overons/nieuws/en/the-next-phase-of-5g-arrives-today/: "We have provided 5G coverage throughout the Netherlands via the 700 MHz band in recent years." "We have already installed the 3.5 GHz band in the busiest places and are activating it today." (n28, n78). Not used: forum claim of n1 (not official). No official 4G band list found.
- MVNOs: simyo.nl/en/klantenservice/netwerk (page title "Netwerkinfo van Simyo, op het KPN netwerk"; Simyo offers 4G/5G via KPN). Youfone: youfone.nl/blog/youfone-beste-sim-only-provider-volgens-pricewise: "Wij maken gebruik van het premium KPN-netwerk, dus reken maar op goed bereik."

### VodafoneZiggo (Vodafone): lte null, nr null
- vodafoneziggo.nl/en/nieuws/vodafone-first-offer-nationwide-5g/: "During the spectrum auction, Vodafone acquired frequencies in the 700, 1400 and 2100 MHz bands." Licence only; "will use ... to further deploy 5G", no deployed band named. 2020 launch release says 5G ran "in bestaande frequentiebanden" via DSS without naming them (the 1800 MHz detail is only in Telecompaper, secondary), so null.
- MVNO hollandsnieuwe: hollandsnieuwe.nl/3g: "We maken gebruik van het betrouwbare 5G-netwerk van Vodafone, het beste internationale netwerk."

### Odido: lte null | nr 78
- odido.nl/blog/5g-boost: "We gebruiken nu de 3,5 GHz-frequentie en zo krijgt ons mobiele netwerk een flinke boost." mobiel.nl/nieuws/odido-activeert-5g (kind other): "Op 10 juli 2024 activeerde Odido als eerste provider in Nederland de 5G-frequenties." No other Odido bands stated on odido.nl/netwerk/4g or /5g, so only n78 is listed (a lower bound; Odido likely has more).
- MVNO Ben: ben.nl/service/netwerk-dekking/dekking-bereik/van-welk-netwerk-maakt-ben-gebruik: "Namelijk het netwerk van Odido."
- RDI/ACM licence tables not used (they show holdings only).

## Belgium
### Proximus: lte null | nr 78
- proximus.com/news/2020/20201217-5g-spectrum.html: "More specifically, Proximus uses spectrum in the 3.6-3.8 GHz band." Proximus FAQ lists "800, 900, 1800, 2100 and 2600 MHz" for 2G/3G/4G collectively, not per generation, so lte null. Telecompaper (not used) mentions 5G on 2100 MHz.
- MVNO Scarlet: scarlet.be support page: "We use the mobile network of Proximus."

### Orange Belgium: lte null, nr null
- Orange pages (corporate.orange.be/.../orange-belgium-opens-5g-all-its-postpaid-customers, business.orange.be 6-questions) say only "using the temporary spectrum allowed by the national regulator BIPT"; 2022 auction release gives holdings (700/900/1800/2100/3600 MHz) not deployment.
- MVNO edpnet: corporate.orange.be/en/about-orange/partnerships: "With this MVNO agreement, edpnet ..." (wholesale partner page; list incomplete: JIM Mobile/Mobile Vikings conflicting host info, so not listed).

### Telenet (BASE): lte null | nr 78
- press.telenet.be/telenet-to-launch-5g-in-first-regions-around-leuven-antwerp-and-the-coast: "The spectrum is granted at 3.6 GHz and 3.8 GHz." and "Telenet will also reuse 4G spectrum for 5G at certain locations." This is the launch announcement; commercial availability beyond it rests on search snippets, so n78 is the weakest NR entry.
- MVNOs: none verified as current (Lycamobile release ~2017; TADAAM host not stated), so omitted.
- Not included as networks: Citymesh Mobile and Network Research Belgium (hold 2022 spectrum; no deployed public mobile network sourced).

## Luxembourg: all lists null
- POST (post.lu "Is the quantity of 5G frequencies sufficient"): "The 5G frequencies, 700 MHz and 3.6 Ghz, were awarded to Luxembourg through an auction in July 2020." "POST was allocated large amounts of spectrum, 20 MHz for the 700 MHz band and 110 MHz for the 3.6 GHz band." Another POST page: "Today, the frequencies used for 5G include in particular 700 MHz and 3.6 GHz" (generic, not POST-specific); POST 4G page says only "between 800 MHz and 2600 MHz". Deployment per band not stated, so null (n28/n78 probable but unsourced).
- Orange Luxembourg: obtained "2x10 sur la bande de 700 MHz, 1x110 sur la bande de 3.6 GHz" (2020 release); no deployed bands named.
- Proximus Luxembourg (Tango): proximus.lu 5G first connections (2019 temporary 3.6 GHz); no deployed bands. ILR octroi page lists only qualified candidates, no results (also fetched).
- Luxembourg Online (10 MHz at 3.6 GHz) and Eltrona not included (no public mobile network sourced). No MVNOs verified.

## Failed or unusable sources
telekom.de pages need login or 404; POST "comment-post-va-t-elle-deployer" and other post.lu pages 404; vodafoneziggo community pages 403; no BNetzA, ACM/RDI, BIPT or ILR deployment tables found for DE/NL/BE/LU beyond holdings.
