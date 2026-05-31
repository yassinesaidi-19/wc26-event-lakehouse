# API Keys

## Bad

Do not keep API keys in files like:

- `data/raw/api_football.txt`
- `data/raw/api_football_data.txt`

## Good

Keep secrets only in local `.env`:

```env
API_FOOTBALL_KEY=...
FOOTBALL_DATA_KEY=...
```

## Warning

If real API keys were ever committed to GitHub, rotate them immediately.

## Migration Behavior

The project migration logic does the following locally:

- reads key material from the legacy raw text files when present
- writes `API_FOOTBALL_KEY=...` into `.env` only if it is not already present
- writes `FOOTBALL_DATA_KEY=...` into `.env` only if it is not already present
- moves the legacy raw text files into an ignored quarantine folder
- never prints the keys in logs or terminal output
