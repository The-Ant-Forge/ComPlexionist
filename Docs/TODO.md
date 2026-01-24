# ComPlexionist - Development TODO

## Project Setup

- [ ] Initialize Git repository
- [ ] Create GitHub repository
- [ ] Set up `.github/` folder (workflows, issue templates, etc.)
- [ ] Choose and configure tech stack
- [ ] Set up development environment
- [ ] Configure linting and formatting

## Research & Planning

- [x] Research Plex API and authentication
- [x] Research TMDB Collections API
- [x] Research TVDB Episodes API
- [ ] Review reference implementations:
  - [ ] Movie collection gap finder repo (user to provide)
  - [ ] TV episode gap finder repo (user to provide)
- [ ] Finalize architecture decisions

## Core Features

### Authentication Module
- [ ] Implement Plex authentication (X-Plex-Token)
- [ ] Implement TMDB API key handling
- [ ] Implement TVDB API key handling
- [ ] Secure credential storage

### Plex Integration
- [ ] Connect to Plex Media Server
- [ ] Fetch library sections
- [ ] Fetch movie collections
- [ ] Fetch TV shows and episodes

### Movie Collection Gaps Feature
- [ ] Get collections from Plex movie library
- [ ] For each collection:
  - [ ] Identify collection on TMDB (by name match or ID)
  - [ ] Fetch complete movie list from TMDB
  - [ ] Compare against Plex collection items
  - [ ] Generate missing movies report

### TV Episode Gaps Feature
- [ ] Get TV shows from Plex TV library
- [ ] For each show:
  - [ ] Identify show on TVDB/TMDB
  - [ ] Fetch complete episode listing
  - [ ] Compare against Plex episodes
  - [ ] Generate missing episodes report

## User Interface

- [ ] Determine UI approach (CLI, Web, Desktop, etc.)
- [ ] Design user flows
- [ ] Implement output formatting
- [ ] Add filtering/sorting options

## Testing

- [ ] Set up testing framework
- [ ] Unit tests for API integrations
- [ ] Integration tests
- [ ] Mock data for development without live Plex server

## Documentation

- [x] Create README.md
- [x] Create Plex-Background.md
- [ ] API documentation
- [ ] User guide
- [ ] Contributing guidelines

## Future Enhancements

- [ ] Caching for API responses
- [ ] Batch processing for large libraries
- [ ] Export reports (CSV, JSON)
- [ ] Watchlist integration
- [ ] Notifications for new releases in missing collections
