# Data Sources

## Source Strategy

The project intentionally uses three source modes at once:

- deterministic sample data for 2026 testing
- public downloaded historical datasets
- optional live APIs for current raw payload capture and normalization

This balances reproducibility with realism.

## 1. Local Sample Files

Location:

```text
data/sample/
```

Role:

- controlled 2026 MVP inputs
- deterministic testing
- safe current-tournament logic validation without inventing official results

## 2. openfootball

Location:

```text
data/external/openfootball/
```

Role:

- public tournament structure and fixture data
- contributes canonical match and team context through the existing local pipeline path

Current reality:

- it contributes scheduled match coverage
- it is not currently the dominant source of finished standings rows

## 3. Fjelstul World Cup Database

Location:

```text
data/external/fjelstul/
```

Role:

- strongest historical structured source in the repo
- contributes the bulk of historical finished group-stage matches
- drives most historical standings rows in the current state engine

## 4. API-Football

Raw location:

```text
data/raw/api_football/
```

Normalized role:

- raw fixtures and teams now normalize into standardized match and team records
- normalized records contribute to `event_log`, `dim_team`, `fact_match`, `fact_match_event` lifecycle rows, and downstream marts

Current limitations:

- detailed event normalization only works if raw event payloads are available
- provider plan limits can restrict completeness
- official 2026 competition identifiers may need updating later

Security:

- key must live in `.env` as `API_FOOTBALL_KEY`
- key must never live under `data/raw/`
- key must never be printed in logs

## 5. football-data.org

Raw location:

```text
data/raw/football_data/
```

Normalized role:

- raw teams and matches normalize into standardized team and match records
- normalized records contribute to `event_log`, `dim_team`, `fact_match`, and downstream marts

Current limitations:

- the current plan does not provide detailed match events, so `fact_match_event` contribution is currently zero for this source
- official 2026 competition identifiers and coverage may change later

Security:

- key must live in `.env` as `FOOTBALL_DATA_KEY`
- key must never live under `data/raw/`
- key must never be printed in logs

## Source Contribution Transparency

The pipeline writes:

```text
data/quality/source_contribution_report.csv
```

This makes the live-source contribution explicit. If an API returns no usable canonical records, the report shows zero contribution instead of hiding it.
