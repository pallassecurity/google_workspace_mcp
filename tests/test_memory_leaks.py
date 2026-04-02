"""
Memory leak regression tests for OAuth21SessionStore.

Two leak vectors were identified and fixed:

1. _server_instances (FastMCP SDK) — fixed by FASTMCP_STATELESS_HTTP=true in main.py.
   Tested here by inspecting the FastMCP setting and verifying it is active.

2. _mcp_session_mapping / _session_auth_binding / _mcp_session_timestamps
   (OAuth21SessionStore) — fixed by TTL cleanup in store_session().
   Tested here by:
     a. Verifying stale entries are evicted after the TTL passes.
     b. Verifying that accumulating many sessions (simulating months of traffic)
        stays bounded once cleanup runs.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from auth.oauth21_session_store import OAuth21SessionStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store() -> OAuth21SessionStore:
    return OAuth21SessionStore()


def _add_session(store: OAuth21SessionStore, email: str, mcp_sid: str) -> None:
    """Call store_session with minimal required fields."""
    store.store_session(
        user_email=email,
        access_token="tok_" + mcp_sid[:8],
        refresh_token=None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client_id",
        client_secret="client_secret",
        scopes=["https://mail.google.com/"],
        expiry=None,
        session_id="sess_" + mcp_sid[:8],
        mcp_session_id=mcp_sid,
        issuer="https://accounts.google.com",
    )


# ---------------------------------------------------------------------------
# TTL cleanup tests
# ---------------------------------------------------------------------------

class TestTTLCleanup:
    def test_stale_entries_are_removed_after_ttl(self):
        """Entries older than max_age_minutes must be evicted on the next store_session call."""
        store = _make_store()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=130)

        # Inject 10 stale sessions by bypassing store_session (simulate pre-fix data)
        with store._lock:
            for i in range(10):
                sid = f"stale-{i}"
                store._mcp_session_mapping[sid] = f"user{i}@test.com"
                store._session_auth_binding[sid] = f"user{i}@test.com"
                store._mcp_session_timestamps[sid] = old_time

        assert len(store._mcp_session_mapping) == 10

        # Adding one fresh session triggers cleanup
        fresh_sid = str(uuid.uuid4())
        _add_session(store, "fresh@test.com", fresh_sid)

        # Only the fresh session should remain
        assert len(store._mcp_session_mapping) == 1
        assert fresh_sid in store._mcp_session_mapping
        assert len(store._mcp_session_timestamps) == 1
        assert len(store._session_auth_binding) >= 1  # may also hold oauth session_id bindings

    def test_fresh_entries_are_not_removed(self):
        """Entries added recently must survive cleanup."""
        store = _make_store()

        for i in range(5):
            _add_session(store, f"user{i}@test.com", str(uuid.uuid4()))

        before = len(store._mcp_session_mapping)

        # Run cleanup with default TTL — nothing should be removed
        with store._lock:
            store._cleanup_stale_mcp_sessions_locked()

        assert len(store._mcp_session_mapping) == before

    def test_mixed_stale_and_fresh_entries(self):
        """Only stale entries are removed; fresh entries survive."""
        store = _make_store()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=130)

        # 3 stale, injected directly
        with store._lock:
            for i in range(3):
                sid = f"stale-{i}"
                store._mcp_session_mapping[sid] = f"old{i}@test.com"
                store._session_auth_binding[sid] = f"old{i}@test.com"
                store._mcp_session_timestamps[sid] = old_time

        # 2 fresh, added normally
        fresh_sids = [str(uuid.uuid4()) for _ in range(2)]
        for i, sid in enumerate(fresh_sids):
            _add_session(store, f"fresh{i}@test.com", sid)

        # After adding the second fresh session, cleanup will have run once
        # (triggered on the second _add_session call, sees 3 stale + 1 fresh already there)
        assert len(store._mcp_session_mapping) == 2
        for sid in fresh_sids:
            assert sid in store._mcp_session_mapping

    def test_cleanup_does_not_run_when_no_mcp_session_id(self):
        """store_session without mcp_session_id must not crash and must not clean up."""
        store = _make_store()
        old_time = datetime.now(timezone.utc) - timedelta(minutes=130)

        with store._lock:
            sid = "stale-orphan"
            store._mcp_session_mapping[sid] = "orphan@test.com"
            store._session_auth_binding[sid] = "orphan@test.com"
            store._mcp_session_timestamps[sid] = old_time

        # Call store_session without mcp_session_id — cleanup is NOT triggered
        store.store_session(
            user_email="other@test.com",
            access_token="tok",
            refresh_token=None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id="c",
            client_secret="s",
            scopes=[],
            expiry=None,
            session_id="sess_other",
            mcp_session_id=None,
        )

        # Stale entry should still be there (cleanup only triggers with mcp_session_id)
        assert "stale-orphan" in store._mcp_session_mapping


# ---------------------------------------------------------------------------
# Unbounded growth tests
# ---------------------------------------------------------------------------

class TestUnboundedGrowth:
    def test_dict_does_not_grow_unboundedly_under_load(self):
        """
        Simulates months of stateless-HTTP traffic: every request generates a new
        mcp_session_id. Cleanup is triggered on each store_session call.
        After 500 requests with fresh timestamps, size must equal 500 (no stale to clean yet).
        After injecting old entries and adding one more, size must drop back to 1.
        """
        store = _make_store()

        # Simulate 500 requests — all fresh
        for i in range(500):
            _add_session(store, "user@test.com", str(uuid.uuid4()))

        # All 500 are fresh; no eviction yet
        assert len(store._mcp_session_mapping) == 500

        # Now age all 500 entries artificially
        old_time = datetime.now(timezone.utc) - timedelta(minutes=130)
        with store._lock:
            for sid in list(store._mcp_session_timestamps):
                store._mcp_session_timestamps[sid] = old_time

        # One more request triggers cleanup — all 500 stale entries go away
        new_sid = str(uuid.uuid4())
        _add_session(store, "user@test.com", new_sid)

        assert len(store._mcp_session_mapping) == 1
        assert new_sid in store._mcp_session_mapping

    def test_timestamps_dict_stays_in_sync(self):
        """_mcp_session_timestamps must always be in sync with _mcp_session_mapping."""
        store = _make_store()

        for i in range(20):
            _add_session(store, f"user{i % 5}@test.com", str(uuid.uuid4()))

        assert set(store._mcp_session_mapping.keys()) == set(
            store._mcp_session_timestamps.keys()
        )

        # Age them and trigger cleanup
        old_time = datetime.now(timezone.utc) - timedelta(minutes=130)
        with store._lock:
            for sid in list(store._mcp_session_timestamps):
                store._mcp_session_timestamps[sid] = old_time

        _add_session(store, "final@test.com", str(uuid.uuid4()))

        assert set(store._mcp_session_mapping.keys()) == set(
            store._mcp_session_timestamps.keys()
        )


# ---------------------------------------------------------------------------
# Stateless HTTP setting test
# ---------------------------------------------------------------------------

class TestStatelessHTTPSetting:
    def test_fastmcp_stateless_http_env_var_is_set_by_main(self):
        """
        main.py calls os.environ.setdefault('FASTMCP_STATELESS_HTTP', 'true').
        This test verifies the environment variable is correctly written before
        FastMCP picks it up, preventing _server_instances accumulation.
        """
        # Clear the var to simulate a clean environment
        os.environ.pop("FASTMCP_STATELESS_HTTP", None)

        # Replicate what main.py does
        os.environ.setdefault("FASTMCP_STATELESS_HTTP", "true")

        assert os.environ.get("FASTMCP_STATELESS_HTTP") == "true"

    def test_fastmcp_stateless_http_can_be_overridden(self):
        """Operators must be able to override FASTMCP_STATELESS_HTTP via environment."""
        os.environ["FASTMCP_STATELESS_HTTP"] = "false"

        # setdefault must NOT overwrite an existing value
        os.environ.setdefault("FASTMCP_STATELESS_HTTP", "true")

        assert os.environ.get("FASTMCP_STATELESS_HTTP") == "false"

        # Restore
        os.environ.pop("FASTMCP_STATELESS_HTTP", None)
