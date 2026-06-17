"""Pytest configuration for profile-service tests."""

import sys
from pathlib import Path

# Add src to path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
