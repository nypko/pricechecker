# Mobile networks

One file per country, `config/carriers/<CC>.yaml` (ISO code), for the 27 EU states, GB, US, CA and AU.
`pricechecker/carriers.py` validates them; band numbers must exist in `config/bands.yaml`.

```yaml
country: DE
networks:
  - id: de-telekom          # unique across all files
    name: Telekom
    lte: [1, 3, 7, 8, 20]   # bands listed, or null if not researched
    nr: [1, 3, 28, 78]
    basis: used             # used | licensed (see below)
    complete: true          # true only if a source gives the network's full list
    mvnos: [Congstar]       # brands on this network
    sources:
      - {url: "https://...", kind: carrier, checked: 2026-10-31}   # kind: regulator|carrier|brand|other
```

## Sourcing rule (amended 2026-10-31)

A band is listed when the national regulator's licence data says the network **holds** it, or when the network's own
pages or a regulator deployment report say it **uses** it. A licence held but stated as switched off is left out.
- `basis: used`: every listed band is confirmed in use. `basis: licensed`: the list comes, wholly or partly, from
  licence data.
- `complete: true` only when a source gives the full list (a regulator licence table does); a list built from
  scattered mentions (a 5G launch page naming 3.5 GHz) is `complete: false`. `licensed` needs a `regulator` source;
  `complete: true` needs both lists filled.
- Supplementary downlink bands (1400/1500 MHz: B32, n75, n76) are listed only when a source says they are used; leaving them out does not make a list incomplete.
Prefer a regulator, then the carrier's own page, then the phone brand's page. Wikipedia may point you to a source but
a network with only `other` sources fails validation. Every source needs an https url and the date you read it.
Networks not checked for 12 months are logged in the build.

## Adding a network

1. Add an entry to the country's file (create the file if the country has none).
2. Fill `lte`, `nr`, `basis`, `complete` and `mvnos` from your sources; add each source with today's date.
3. Run `.venv/bin/python -m pytest -q tests/test_carriers.py`.
