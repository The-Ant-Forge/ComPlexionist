"""UI strings for ComPlexionist GUI.

Centralizes all user-facing text for consistency and future localization.
"""

from __future__ import annotations

# =============================================================================
# Application
# =============================================================================
APP_TITLE = "ComPlexionist"

# =============================================================================
# Navigation
# =============================================================================
NAV_HOME = "Home"
NAV_RESULTS = "Results"
NAV_SETTINGS = "Settings"

# =============================================================================
# Dashboard
# =============================================================================
DASHBOARD_WELCOME = "Welcome to ComPlexionist"
DASHBOARD_SCAN_MOVIES = "Scan Movies"
DASHBOARD_SCAN_MOVIES_DESC = "Find missing movies in your collections"
DASHBOARD_SCAN_TV = "Scan TV Shows"
DASHBOARD_SCAN_TV_DESC = "Find missing episodes in your shows"
DASHBOARD_SCAN_BOTH = "Full Scan"
DASHBOARD_SCAN_BOTH_DESC = "Scan both movies and TV shows"

# =============================================================================
# Scanning
# =============================================================================
SCAN_TITLE_MOVIES = "Scanning Movie Collections"
SCAN_TITLE_TV = "Scanning TV Shows"
SCAN_TITLE_BOTH = "Scanning Libraries"
SCAN_PREPARING = "Preparing..."
SCAN_PROCESSING = "Processing..."
SCAN_COMPLETE = "Complete!"
SCAN_FINISHED = "Scan finished"
SCAN_CANCEL = "Cancel"

# =============================================================================
# Results
# =============================================================================
RESULTS_TITLE = "Results"
RESULTS_NO_GAPS_MOVIES = "No gaps found!"
RESULTS_ALL_COMPLETE_MOVIES = "All collections are complete."
RESULTS_NO_GAPS_TV = "No gaps found!"
RESULTS_ALL_COMPLETE_TV = "All episodes are present."
RESULTS_EXPORT_CSV = "Export CSV"
RESULTS_EXPORT_JSON = "Export JSON"
RESULTS_COPY_CLIPBOARD = "Copy to Clipboard"
RESULTS_COPIED = "Results copied to clipboard"
RESULTS_NO_RESULTS = "No results to export"
RESULTS_SAVED = "Saved: {filename}"
RESULTS_OPEN_FOLDER = "Open folder"

# =============================================================================
# Settings
# =============================================================================
SETTINGS_TITLE = "Settings"
SETTINGS_CONNECTIONS = "Connections"
SETTINGS_PLEX_SERVER = "Plex Server"
SETTINGS_TMDB = "TMDB"
SETTINGS_TMDB_DESC = "Movie collection data"
SETTINGS_TVDB = "TVDB"
SETTINGS_TVDB_DESC = "TV episode data"
SETTINGS_TEST_CONNECTIONS = "Test Connections"
SETTINGS_RUN_SETUP = "Run Setup Wizard"
SETTINGS_NOT_CONFIGURED = "Not configured"
SETTINGS_ALL_CONNECTED = "All connections successful!"
SETTINGS_CACHE = "Cache"
SETTINGS_CLEAR_CACHE = "Clear Cache"
SETTINGS_CACHE_CLEARED = "Cache cleared ({count} entries removed)"
SETTINGS_APPEARANCE = "Appearance"
SETTINGS_DARK_MODE = "Dark Mode"

# =============================================================================
# Onboarding
# =============================================================================
ONBOARDING_WELCOME = "Welcome to ComPlexionist"
ONBOARDING_INTRO = "Let's set up your Plex and API connections."
ONBOARDING_NEXT = "Next"
ONBOARDING_BACK = "Back"
ONBOARDING_FINISH = "Finish"
ONBOARDING_SKIP = "Skip"

# =============================================================================
# Dialogs
# =============================================================================
DIALOG_START_SCAN = "Start {type} Scan"
DIALOG_CANCEL = "Cancel"
DIALOG_START = "Start Scan"
DIALOG_MOVIE_LIBRARY = "Movie Library"
DIALOG_TV_LIBRARY = "TV Library"
DIALOG_NO_LIBRARIES = "No libraries available. Check your Plex connection."

# =============================================================================
# Errors - User Friendly Messages
# =============================================================================
ERROR_UNKNOWN = "An unexpected error occurred. Please try again."
ERROR_CONNECTION_REFUSED = "Cannot connect to the server. Is it running?"
ERROR_CONNECTION_TIMEOUT = "Connection timed out. The server may be slow or unreachable."
ERROR_PLEX_UNAUTHORIZED = "Plex authentication failed. Check your token in settings."
ERROR_PLEX_NOT_FOUND = "Plex server not found at the configured URL."
ERROR_TMDB_UNAUTHORIZED = "TMDB API key is invalid. Check your key in settings."
ERROR_TMDB_RATE_LIMIT = "TMDB rate limit reached. Please wait a moment and try again."
ERROR_TVDB_UNAUTHORIZED = "TVDB API key is invalid. Check your key in settings."
ERROR_TVDB_RATE_LIMIT = "TVDB rate limit reached. Please wait a moment and try again."
ERROR_NO_CONFIG = "No configuration found. Please run the setup wizard."
ERROR_SCAN_FAILED = "Scan failed: {error}"
ERROR_EXPORT_FAILED = "Export failed: {error}"

# =============================================================================
# Error Detail Button
# =============================================================================
ERROR_SHOW_DETAILS = "Show Details"

# =============================================================================
# Ignore Actions
# =============================================================================
IGNORE_COLLECTION_ADDED = "'{name}' added to ignore list"
IGNORE_SHOW_ADDED = "'{name}' added to ignore list"
