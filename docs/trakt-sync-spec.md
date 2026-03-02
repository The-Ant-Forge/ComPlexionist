# Trakt Collection Sync (Spec — Not Implemented)

> **Status:** Shelved. Trakt API registration obligations (app approval process, required redirect URIs, terms of service constraints) make it impractical to distribute as part of a standalone desktop tool.

## Concept

Push Plex library (movies + TV shows) into Trakt.tv collection. Smart diff: fetch user's current Trakt collection first, only push items not already there. Collection sync only (not watched status or ratings).

## Trakt API Overview

- Base URL: `https://api.trakt.tv`
- Auth: OAuth2 device code flow (no browser redirect needed)
- Required headers: `Content-Type: application/json`, `trakt-api-version: 2`, `trakt-api-key: {client_id}`, `Authorization: Bearer {access_token}`
- Key endpoints:
  - `POST /oauth/device/code` → device code flow start
  - `POST /oauth/device/token` → poll for token
  - `POST /oauth/token` → refresh token
  - `GET /users/me/collection/movies` → current movie collection
  - `GET /users/me/collection/shows` → current show collection
  - `POST /sync/collection` → bulk add to collection (accepts movies + shows arrays with IDs)
  - `GET /users/settings` → validate token, get username

## INI Format

```ini
[trakt]
client_id = your_trakt_client_id
client_secret = your_trakt_client_secret
access_token = (auto-saved after OAuth)
refresh_token = (auto-saved after OAuth)
token_expires = (auto-saved, epoch timestamp)
```

Requires user to create a Trakt API app at https://trakt.tv/oauth/applications to get client_id and client_secret.

## Planned Architecture

### Config — `src/complexionist/config.py`

`TraktConfig` model with client_id, client_secret, access_token, refresh_token, token_expires. `save_trakt_tokens()` for persisting OAuth tokens after auth flow.

### Package — `src/complexionist/trakt/`

- `models.py` — TraktMovie, TraktShow, TraktIds, SyncResult (Pydantic models)
- `client.py` — TraktClient extending BaseAPIClient (get_collection_movies/shows, add_to_collection, test_connection)
- `auth.py` — Device code flow (start_device_auth, poll_for_token, refresh_access_token)
- `sync.py` — TraktSync class with smart diff logic (fetch existing, filter new, bulk POST)

### CLI Commands

- `complexionist trakt auth` — device code flow, display code + URL, poll, save tokens
- `complexionist trakt sync [--server NAME]` — fetch Plex library, diff against Trakt, push new items
- `complexionist trakt status` — show authenticated username, collection counts

### GUI

- Settings: Trakt section with auth dialog (device code flow), disconnect button, sync now button
- Dashboard: Trakt status indicator (green/red dot)

### Sync Logic

1. Fetch current Trakt collection (movies + shows)
2. Build set of existing IDs (TMDB, IMDB, TVDB)
3. Filter Plex items to those not already in Trakt
4. Bulk POST to `/sync/collection`
5. Report: added, already existed, not found

Uses existing Plex model IDs (tmdb_id, imdb_id, tvdb_id) — no Plex model changes needed.

## Why Shelved

Trakt requires developers to register an API application with specific approval criteria. The registration process and terms make it difficult to ship client_id/client_secret embedded in a standalone desktop application, and requiring end users to create their own API app adds significant friction.
