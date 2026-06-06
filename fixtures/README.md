# Fixtures

`fixtures.json` is the single source of truth for the 104 World Cup 2026 matches.

## Populating it

Run `python model/fetch_fixtures.py` to pull the official schedule and team-to-group
mapping. The script writes directly into `fixtures.json`.

## Match record shape

Each entry in `matches` follows this shape:

```json
{
  "id": "m-001",
  "stage": "GROUP",
  "group": "A",
  "round": 1,
  "kickoff": "2026-06-11T20:00:00Z",
  "venue": "Estadio Azteca, Mexico City",
  "home": "MEX",
  "away": "TBD",
  "score": { "home": null, "away": null },
  "status": "SCHEDULED"
}
```

`stage` is one of `GROUP`, `R32`, `R16`, `QF`, `SF`, `3RD`, `FINAL`.
`status` is one of `SCHEDULED`, `LIVE`, `FINISHED`, `POSTPONED`.
Teams are ISO 3-letter codes (FIFA codes).
