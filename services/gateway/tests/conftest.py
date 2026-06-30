"""Pytest configuration for gateway-service tests."""

import os


# ---------------------------------------------------------------------------
# Test environment bootstrap
# ---------------------------------------------------------------------------
# Keep test execution deterministic regardless of host/container env values.
os.environ["LOCAL_AUTH_BYPASS"] = "true"
os.environ["LOCAL_USER_SUB"] = "test-sub"
os.environ["LOCAL_USER_EMAIL"] = "test@example.com"
os.environ["LOCAL_USER_ISSUER"] = "http://test-cognito"
os.environ["PROFILE_SERVICE_URL"] = "http://profile-service:8080"
