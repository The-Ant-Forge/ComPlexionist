"""Help screen for ComPlexionist GUI."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import flet as ft

from complexionist import __version__
from complexionist.gui.screens.base import BaseScreen

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


# Help content as embedded markdown
HELP_CONTENT = """
# ComPlexionist User Guide

ComPlexionist finds gaps in your Plex media library by comparing what you own against complete series and movie collections from TMDB and TVDB.

---

## Getting Started

### First Run Setup

When you first launch ComPlexionist, the setup wizard will guide you through:

1. **Plex Connection** - Enter your Plex server URL and authentication token
2. **TMDB API Key** - For movie collection data (free at themoviedb.org)
3. **TVDB API Key** - For TV episode data (free at thetvdb.com)

The wizard tests each connection before proceeding. Your settings are saved to `complexionist.ini` in the same folder as the application.

### Where to Get API Keys

- **Plex Token**: Settings > Account > Authorized Devices, or use browser developer tools while logged into Plex
- **TMDB**: Create free account at [themoviedb.org](https://www.themoviedb.org/settings/api)
- **TVDB**: Create free account at [thetvdb.com](https://thetvdb.com/dashboard/account/apikey)

---

## Running Scans

### Scan Types

- **Movies** - Finds missing movies from collections you've started
- **TV** - Finds missing episodes from TV shows you own
- **Full Scan** - Runs both movie and TV scans

### Starting a Scan

1. Click one of the scan buttons on the home screen
2. Select the library to scan from the dropdown
3. Click **Start Scan**

### During the Scan

The progress screen shows:
- Current phase (loading library, checking collections, etc.)
- Progress bar with item counts
- Live statistics (API calls, cache hits, elapsed time)

You can cancel at any time with the **Cancel** button.

---

## Understanding Results

### Completion Score

The score shows what percentage of available content you own:
- **90%+** Excellent - Nearly complete!
- **70-89%** Good - Minor gaps
- **50-69%** Fair - Some gaps to fill
- **Below 50%** - Significant gaps

### Movie Results

Movies are grouped by collection (e.g., "Harry Potter Collection"). Each collection shows:
- Movies you **own** (with checkmark)
- Movies you're **missing** (with X)
- Collection completion percentage

### Organizing Collections

If your movies from a collection are scattered in different folders, an **Organize** button (orange) appears. Click it to:
- See where each movie file is currently located
- View the suggested collection folder path
- Move all files into a single collection folder with one click

The move operation includes safety checks to prevent overwriting files.

### TV Results

TV shows are grouped by series, then by season. Each entry shows:
- Episode code (S01E05)
- Episode title
- Air date

### Filtering Results

Use the search box to filter by title. Results update as you type.

### Ignoring Items

Right-click (or long-press) on a collection or show to add it to your ignore list. Ignored items won't appear in future scans.

---

## Exporting Results

Click the **Export** button on the results screen to:

- **CSV** - Spreadsheet format, opens in Excel/Google Sheets
- **JSON** - Structured data for scripts or other tools
- **Copy** - Copy results to clipboard as text

---

## Settings

### Theme

Toggle between dark mode (default) and light mode.

### Re-run Setup

Click to go through the setup wizard again if you need to change API keys or server settings.

### Test Connections

Verify that all your API connections are working.

### Ignored Items

View and manage your ignore lists for collections and TV shows. Click the X to remove an item from the ignore list.

### Cache

ComPlexionist caches API responses to speed up scans:
- TMDB data: 7-30 days depending on type
- TVDB data: 24 hours

The cache location is shown in settings. Clear it if you're seeing stale data.

---

## Troubleshooting

### "Connection failed" errors

- Check your Plex server is running and accessible
- Verify API keys are correct (re-run setup if needed)
- Check your internet connection

### Missing shows/movies

- The show might not exist in TVDB/TMDB
- Check spelling matches exactly
- Some content is region-locked in the databases

### Scan takes too long

- First scans are slower (building cache)
- Large libraries (1000+ items) take longer
- Subsequent scans use cached data and are much faster

### Error Log

Errors are logged to `complexionist_errors.log` in the same folder as the application. Check this file if you encounter issues.

---

## Tips

- **Run scans periodically** to catch new releases
- **Use ignore lists** for collections you don't want to complete
- **Check the cache stats** in settings to see how effective caching is
- **Export to CSV** for easy tracking in a spreadsheet

---

## About

ComPlexionist is open source software. Report issues or contribute at GitHub.
"""


class HelpScreen(BaseScreen):
    """Help and user guide screen."""

    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        on_back: Callable[[], None],
    ) -> None:
        """Initialize help screen.

        Args:
            page: Flet page instance.
            state: Application state.
            on_back: Callback to go back.
        """
        super().__init__(page, state)
        self.on_back = on_back

    def build(self) -> ft.Control:
        """Build the help screen UI."""
        # Header with back button
        header = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=lambda _: self.on_back(),
                    tooltip="Back to Home",
                ),
                ft.Text("Help", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text(
                    f"v{__version__}",
                    size=12,
                    color=ft.Colors.GREY_500,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        # Help content in scrollable markdown
        help_markdown = ft.Markdown(
            HELP_CONTENT,
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            on_tap_link=lambda e: self.page.launch_url(e.data),
        )

        # Wrap in scrollable container
        content = ft.Container(
            content=ft.Column(
                [
                    header,
                    ft.Divider(),
                    ft.Container(
                        content=help_markdown,
                        expand=True,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=20,
            expand=True,
        )

        return content
