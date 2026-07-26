"""Tests for results screen overlay management.

Regression coverage for the organize dialog "Control must be added to the
page first" crash: Flet controls are dataclasses whose generated ``__eq__``
compares fields, so a pristine dialog left in ``page.overlay`` by a previous
ResultsScreen instance compares equal to the new instance's pristine dialog.
Equality-based membership checks then keep the old (mounted) control and
never append the new one, leaving it unmounted.
"""

import flet as ft

from complexionist.gui.screens.results import (
    _ORGANIZE_OVERLAY_TAG,
    _sync_organize_overlays,
)


def _make_organize_pair() -> tuple[ft.AlertDialog, ft.SnackBar]:
    """Create a dialog/snackbar pair exactly as ResultsScreen.__init__ does."""
    dialog = ft.AlertDialog(
        title=ft.Text(""),
        content=ft.Container(width=550, height=350),
        modal=True,
        data=_ORGANIZE_OVERLAY_TAG,
    )
    snack = ft.SnackBar(content=ft.Text(""), duration=4000, data=_ORGANIZE_OVERLAY_TAG)
    return dialog, snack


class TestSyncOrganizeOverlays:
    def test_adds_own_controls_to_empty_overlay(self):
        dialog, snack = _make_organize_pair()
        overlay: list = []

        _sync_organize_overlays(overlay, (dialog, snack))

        assert any(c is dialog for c in overlay)
        assert any(c is snack for c in overlay)

    def test_replaces_pristine_pair_from_previous_instance(self):
        """Pristine controls from an old screen compare == to the new ones;
        the sync must still swap them out by identity, or the new dialog is
        never mounted and its update() raises at Organize-click time."""
        old_dialog, old_snack = _make_organize_pair()
        new_dialog, new_snack = _make_organize_pair()
        # Sanity: this is the equality trap that caused the bug
        assert old_dialog == new_dialog
        assert old_dialog is not new_dialog

        overlay: list = [old_dialog, old_snack]
        _sync_organize_overlays(overlay, (new_dialog, new_snack))

        assert any(c is new_dialog for c in overlay), "new dialog must be appended"
        assert any(c is new_snack for c in overlay), "new snack must be appended"
        assert not any(c is old_dialog for c in overlay), "old dialog must be evicted"
        assert not any(c is old_snack for c in overlay), "old snack must be evicted"

    def test_replaces_mutated_pair_from_previous_instance(self):
        """An old dialog that was opened (title/actions mutated) must also be
        evicted."""
        old_dialog, old_snack = _make_organize_pair()
        old_dialog.title = ft.Text("Organize: Some Collection")
        old_dialog.actions = [ft.TextButton("Close")]
        new_dialog, new_snack = _make_organize_pair()

        overlay: list = [old_dialog, old_snack]
        _sync_organize_overlays(overlay, (new_dialog, new_snack))

        assert any(c is new_dialog for c in overlay)
        assert any(c is new_snack for c in overlay)
        assert not any(c is old_dialog for c in overlay)
        assert not any(c is old_snack for c in overlay)

    def test_keeps_own_controls_already_in_overlay(self):
        """Calling sync again with the same instances must not duplicate."""
        dialog, snack = _make_organize_pair()
        overlay: list = [dialog, snack]

        _sync_organize_overlays(overlay, (dialog, snack))

        assert sum(1 for c in overlay if c is dialog) == 1
        assert sum(1 for c in overlay if c is snack) == 1

    def test_leaves_untagged_overlay_controls_alone(self):
        other = ft.SnackBar(content=ft.Text("transient message"))
        dialog, snack = _make_organize_pair()
        overlay: list = [other]

        _sync_organize_overlays(overlay, (dialog, snack))

        assert any(c is other for c in overlay)
