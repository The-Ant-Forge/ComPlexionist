# Plex Media Server Background Research

## Overview

Plex Media Server is a media management and streaming platform that organizes personal media (movies, TV shows, music, photos) into libraries. Each library is dedicated to a single content type, enabling specialized metadata handling and organization.

## Library Architecture

### Separation by Content Type
- **Movie Libraries**: Contain only movies
- **TV Show Libraries**: Contain only television series
- **Music Libraries**: Contain only audio content
- **Photo Libraries**: Contain only images

This separation enables:
- More accurate file name parsing and media identification
- Appropriate metadata agent selection per content type
- Consistent data enrichment from external sources (TMDB, TVDB)

### TV Show Hierarchy
```
TV Show Library
└── Series (Show)
    └── Season
        └── Episode
```

## Plex API

### Authentication

#### X-Plex-Token (Traditional)
- All API requests require authentication via `X-Plex-Token` header or URL parameter
- Example: `http://[PMS_IP]:32400/library/sections?X-Plex-Token=YourToken`
- Tokens can be found in Plex Web app (XML view) or via API

#### JWT Authentication (2025+)
- New security enhancement using JSON Web Tokens
- Shorter token lifespans, public-key authentication model
- Device registers public key (JWK) with auth endpoint
- Tokens refresh every 7 days
- Same `X-Plex-Token` header interface maintained

#### PIN Authentication Flow (Recommended for Apps)
- POST to `https://clients.plex.tv/api/v2/pins`
- Required headers: `X-Plex-Client-Identifier`
- Body includes JWK with public key data
- Best approach for new applications

### Response Format
- Default: XML
- JSON: Requires `Accept: application/json` header
- **Recommendation**: Use JSON for new applications

### Key Endpoints

#### Library Sections
```
GET /library/sections
```
Returns all library sections (Movies, TV Shows, etc.)

#### Library Contents
```
GET /library/sections/{sectionId}/all
```
Returns all items in a library section

#### Collections
```
GET /library/sections/{sectionId}/collections
```
Returns all collections in a library section

#### Collection Items
```
GET /library/collections/{collectionId}/children
```
Returns all items within a specific collection

#### TV Show Episodes
```
GET /library/metadata/{showId}/allLeaves
```
Returns all episodes for a TV show

```
GET /library/metadata/{seasonId}/children
```
Returns episodes for a specific season

## Collections in Plex

### What Are Collections?
Collections are curated groupings of related movies. They can be:
- **Auto-generated**: Created by Plex based on TMDB collection data
- **Manual**: User-created groupings
- **Smart Collections**: Dynamic collections based on filter criteria

### Collection Metadata
Each collection object includes:
- `ratingKey`: Unique identifier
- `key`: API URL path
- `title`: Collection name
- `type`: Always "collection"
- `subtype`: Content type (movie, show, etc.)
- `index`: Plex index number
- `childCount`: Number of items in collection

### The Missing Movies Problem
Plex shows collections when you own at least one movie from that collection. However:
- Plex does NOT indicate which movies are missing from the collection
- Users must manually cross-reference with external sources
- This is a key pain point our app addresses

## External Data Sources

### TMDB (The Movie Database)
- Primary source for movie metadata
- Provides collection information with all movies in each collection
- **Collection Details Endpoint**: Returns all movies in a collection by collection ID
- API: `https://api.themoviedb.org/3/collection/{collection_id}`
- Requires API key (free tier available)

### TVDB (TheTVDB)
- Primary source for TV show metadata
- Provides complete episode listings per series
- **Series Episodes Endpoint**: Returns all episodes for a series
- V4 API: `https://api4.thetvdb.com/v4/series/{id}/episodes/{season-type}`
- Requires API key

## Python PlexAPI Library

The unofficial `python-plexapi` library provides comprehensive bindings:

### Installation
```bash
pip install plexapi
```

### Basic Usage
```python
from plexapi.server import PlexServer

# Connect to server
plex = PlexServer('http://localhost:32400', 'YOUR_TOKEN')

# Get movie library
movies = plex.library.section('Movies')

# Get all collections
collections = movies.collections()

# Get items in a collection
for collection in collections:
    items = collection.items()
```

### Key Classes
- `PlexServer`: Main entry point
- `LibrarySection`: Represents a library (MovieSection, ShowSection)
- `Collection`: Represents a collection
- `Movie`: Individual movie
- `Show`: TV series
- `Season`: TV season
- `Episode`: TV episode

## Related Tools & Prior Art

### Gaps
- Tool to "Find the missing movies in your Plex Server"
- Compares Plex collections against TMDB collection data
- Relevant reference for our movie collection feature

### Plex Meta Manager
- Comprehensive metadata management tool
- Can create/manage collections based on external lists

## Key Data Structures for Our App

### For Movie Collections Feature
1. **Plex Collection**: Get collection name and contained movies
2. **TMDB Collection**: Get complete list of movies in that collection
3. **Comparison**: Identify movies in TMDB but not in Plex

### For TV Episodes Feature
1. **Plex Show**: Get all episodes currently in library
2. **TVDB/TMDB Series**: Get complete episode listing
3. **Comparison**: Identify missing episodes by season/episode number

## Sources

- [Plex API Documentation](https://developer.plex.tv/pms/)
- [Python PlexAPI Documentation](https://python-plexapi.readthedocs.io/en/latest/)
- [Plex Support - Finding Auth Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
- [Plex Pro Week '25 - API Unlocked](https://www.plex.tv/blog/plex-pro-week-25-api-unlocked/)
- [TMDB API Getting Started](https://developer.themoviedb.org/reference/intro/getting-started)
- [TVDB V4 API Documentation](https://thetvdb.github.io/v4-api/)
- [Plexopedia - TV Episodes API](https://www.plexopedia.com/plex-media-server/api/library/tvshows-episodes/)
