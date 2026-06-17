import os
import pytest

# Force local auth bypass for all gateway tests
os.environ.setdefault("LOCAL_AUTH_BYPASS", "true")
os.environ.setdefault("LOCAL_USER_SUB", "test-sub")
os.environ.setdefault("LOCAL_USER_EMAIL", "test@example.com")
os.environ.setdefault("LOCAL_USER_ISSUER", "http://test-cognito")
os.environ.setdefault("PROFILE_SERVICE_URL", "http://profile-service-mock")
