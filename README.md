# ComPlexionist

A tool to identify missing content in your Plex Media Server libraries.

## Features

### Movie Collection Gaps
Plex automatically creates Collections when you own movies that belong to a franchise (e.g., "Alien Collection", "Star Wars Collection"). However, Plex doesn't tell you which movies from those collections you're missing.

ComPlexionist solves this by:
- Scanning your Plex movie library collections
- Cross-referencing with TMDB (The Movie Database) to get the complete collection
- Listing all missing movies from each collection

### TV Episode Gaps
For TV show libraries, ComPlexionist identifies missing episodes:
- Scans your Plex TV library for series
- Cross-references with TVDB/TMDB for complete episode listings
- Reports missing episodes by season

## Tech Stack

*TBD - To be determined during project setup*

## Prerequisites

- Plex Media Server with configured libraries
- Plex authentication token
- TMDB API key (free)
- TVDB API key (for TV features)

## Installation

*Coming soon*

## Usage

*Coming soon*

## Documentation

- [Plex Background Research](Docs/Plex-Background.md) - Technical details about Plex API and data structures

## License

*TBD*

## Acknowledgments

- [Plex](https://www.plex.tv/) - Media server platform
- [TMDB](https://www.themoviedb.org/) - Movie metadata
- [TVDB](https://thetvdb.com/) - TV show metadata
- [python-plexapi](https://github.com/pkkid/python-plexapi) - Python bindings for Plex API
