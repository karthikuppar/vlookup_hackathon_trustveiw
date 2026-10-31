"""Shared test setup.

The benchmark and acceptance suites fire hundreds of requests from a single user, which the production
rate limits (30 chat/min, 20 uploads/min) would reject. Lift them for every test; the security tests that
verify the limits set their own values explicitly (see test_security_hardening.py)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _relaxed_rate_limits():
    import abuse_guard
    saved = dict(abuse_guard.limiter.limits)
    abuse_guard.limiter.limits.update({"chat": (100_000, 60), "upload": (100_000, 60), "register": (100_000, 60), "login_ip": (100_000, 60)})
    abuse_guard.limiter.reset()
    yield
    abuse_guard.limiter.limits.clear()
    abuse_guard.limiter.limits.update(saved)
