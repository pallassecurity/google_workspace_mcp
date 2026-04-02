"""
Tests for OAuth scope hierarchy expansion in auth/scopes.py.

Verifies that expand_scopes() correctly infers implied scopes so that
tokens with broader grants (e.g. gmail.modify) satisfy narrow requirements
(e.g. gmail.send) without requiring the exact scope string.

Each case maps to a real Google API endpoint's "Authorization scopes" list
as documented at https://developers.google.com/workspace/gmail/api/reference/rest/
"""

from auth.scopes import (
    expand_scopes,
    DRIVE_SCOPE,
    DRIVE_READONLY_SCOPE,
    DRIVE_FILE_SCOPE,
    DOCS_WRITE_SCOPE,
    DOCS_READONLY_SCOPE,
    SHEETS_WRITE_SCOPE,
    SHEETS_READONLY_SCOPE,
    CALENDAR_SCOPE,
    CALENDAR_READONLY_SCOPE,
    CALENDAR_EVENTS_SCOPE,
    GMAIL_MODIFY_SCOPE,
    GMAIL_READONLY_SCOPE,
    GMAIL_SEND_SCOPE,
    GMAIL_COMPOSE_SCOPE,
    GMAIL_LABELS_SCOPE,
)


# ---------------------------------------------------------------------------
# Drive
# ---------------------------------------------------------------------------


def test_drive_satisfies_drive_readonly():
    """drive (full) → drive.readonly (files.list accepts both)"""
    result = expand_scopes({DRIVE_SCOPE})
    assert DRIVE_READONLY_SCOPE in result


def test_drive_satisfies_drive_file():
    """drive (full) → drive.file (files.create accepts both)"""
    result = expand_scopes({DRIVE_SCOPE})
    assert DRIVE_FILE_SCOPE in result


def test_drive_readonly_does_not_satisfy_drive():
    """drive.readonly does NOT imply full drive write access"""
    result = expand_scopes({DRIVE_READONLY_SCOPE})
    assert DRIVE_SCOPE not in result


# ---------------------------------------------------------------------------
# Google Docs
# ---------------------------------------------------------------------------


def test_docs_write_satisfies_docs_readonly():
    """documents (write) → documents.readonly (documents.get accepts both)"""
    result = expand_scopes({DOCS_WRITE_SCOPE})
    assert DOCS_READONLY_SCOPE in result


def test_docs_readonly_does_not_satisfy_docs_write():
    """documents.readonly does NOT imply write access"""
    result = expand_scopes({DOCS_READONLY_SCOPE})
    assert DOCS_WRITE_SCOPE not in result


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------


def test_sheets_write_satisfies_sheets_readonly():
    """spreadsheets (write) → spreadsheets.readonly (spreadsheets.values.get accepts both)"""
    result = expand_scopes({SHEETS_WRITE_SCOPE})
    assert SHEETS_READONLY_SCOPE in result


def test_sheets_readonly_does_not_satisfy_sheets_write():
    """spreadsheets.readonly does NOT imply write access"""
    result = expand_scopes({SHEETS_READONLY_SCOPE})
    assert SHEETS_WRITE_SCOPE not in result


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------


def test_calendar_satisfies_calendar_readonly():
    """calendar (full) → calendar.readonly (events.list accepts both)"""
    result = expand_scopes({CALENDAR_SCOPE})
    assert CALENDAR_READONLY_SCOPE in result


def test_calendar_satisfies_calendar_events():
    """calendar (full) → calendar.events (events.insert accepts both)"""
    result = expand_scopes({CALENDAR_SCOPE})
    assert CALENDAR_EVENTS_SCOPE in result


def test_calendar_readonly_does_not_satisfy_calendar():
    """calendar.readonly does NOT imply full calendar write access"""
    result = expand_scopes({CALENDAR_READONLY_SCOPE})
    assert CALENDAR_SCOPE not in result


# ---------------------------------------------------------------------------
# Gmail — gmail.modify (the root cause of the reported bug)
# ---------------------------------------------------------------------------


def test_gmail_modify_satisfies_gmail_send():
    """
    gmail.modify → gmail.send.
    Root cause of bug: send_gmail_message requires gmail.send but token only
    had gmail.modify. Verified against users.messages.send authorization scopes:
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
    """
    result = expand_scopes({GMAIL_MODIFY_SCOPE})
    assert GMAIL_SEND_SCOPE in result


def test_gmail_modify_satisfies_gmail_compose():
    """gmail.modify → gmail.compose (users.messages.send accepts both)"""
    result = expand_scopes({GMAIL_MODIFY_SCOPE})
    assert GMAIL_COMPOSE_SCOPE in result


def test_gmail_modify_satisfies_gmail_readonly():
    """gmail.modify → gmail.readonly (users.labels.list accepts both)"""
    result = expand_scopes({GMAIL_MODIFY_SCOPE})
    assert GMAIL_READONLY_SCOPE in result


def test_gmail_modify_satisfies_gmail_labels():
    """gmail.modify → gmail.labels (users.labels.list accepts both)"""
    result = expand_scopes({GMAIL_MODIFY_SCOPE})
    assert GMAIL_LABELS_SCOPE in result


def test_gmail_compose_satisfies_gmail_send():
    """
    gmail.compose → gmail.send.
    users.messages.send accepts both scopes as valid alternatives.
    """
    result = expand_scopes({GMAIL_COMPOSE_SCOPE})
    assert GMAIL_SEND_SCOPE in result


def test_gmail_compose_does_not_satisfy_gmail_readonly():
    """gmail.compose does NOT imply read access to the mailbox"""
    result = expand_scopes({GMAIL_COMPOSE_SCOPE})
    assert GMAIL_READONLY_SCOPE not in result


def test_gmail_send_does_not_satisfy_gmail_modify():
    """gmail.send (narrow) does NOT imply the broader gmail.modify"""
    result = expand_scopes({GMAIL_SEND_SCOPE})
    assert GMAIL_MODIFY_SCOPE not in result


# ---------------------------------------------------------------------------
# Realistic token scenario (mirrors the reported production token)
# ---------------------------------------------------------------------------


def test_token_with_gmail_modify_and_compose_satisfies_send():
    """
    Reproduces the exact bug: token has gmail.modify + gmail.compose but NOT
    gmail.send. After expansion, gmail.send must be present so send_gmail_message
    passes the scope check.
    """
    token_scopes = {GMAIL_MODIFY_SCOPE, GMAIL_COMPOSE_SCOPE, GMAIL_READONLY_SCOPE}
    expanded = expand_scopes(token_scopes)
    assert GMAIL_SEND_SCOPE in expanded


def test_expand_scopes_does_not_remove_original_scopes():
    """expand_scopes must be additive — original scopes are preserved"""
    token_scopes = {GMAIL_MODIFY_SCOPE, DRIVE_SCOPE}
    expanded = expand_scopes(token_scopes)
    assert GMAIL_MODIFY_SCOPE in expanded
    assert DRIVE_SCOPE in expanded
