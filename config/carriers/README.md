# Mobile networks

One file per country, `config/carriers/<CC>.yaml` (ISO code), for the 27 EU states, GB, US, CA and AU.
`pricechecker/carriers.py` validates them; band numbers must exist in `config/bands.yaml`.

```yaml
country: DE
networks:
  - id: de-telekom          # unique across all files
    name: Telekom
    lte: [1, 3, 7, 8, 20]   # bands in use, or null if not researched
    nr: [1, 3, 28, 78]
    mvnos: [Congstar]       # brands on this network
    sources:
      - {url: "https://...", kind: carrier, checked: 2026-10-31}   # kind: regulator|carrier|brand|other
```

## Sourcing rule

List the bands the network uses, deployed, not just licensed. A licence or auction result is not proof of service.
Prefer a regulator, then the carrier's own page, then the phone brand's compatibility page. Wikipedia may point you to
a source but is never the only one: a network with only `other` sources fails validation.
Every source needs an https url and the date you read it. Networks not checked for 12 months are logged in the build.

## Adding a network

1. Add an entry to the country's file (create the file if the country has none).
2. Fill `lte`, `nr` and `mvnos` from your sources and add each source with today's date.
3. Run `.venv/bin/python -m pytest -q tests/test_carriers.py`.
