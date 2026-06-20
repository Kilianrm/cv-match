from __future__ import annotations

from psycopg import connect

from src.modules.profile.profile_base import BaseProfileStoreMixin
from src.modules.profile.profile_certifications import ProfileCertificationsStoreMixin
from src.modules.profile.profile_cv_upload import ProfileCvUploadStoreMixin
from src.modules.profile.profile_education import ProfileEducationStoreMixin
from src.modules.profile.profile_experience import ProfileExperienceStoreMixin
from src.modules.profile.profile_preferred_roles import ProfilePreferredRolesStoreMixin
from src.modules.profile.profile_schema import ProfileSchemaMixin
from src.modules.profile.profile_shared import ProfileSharedMixin
from src.modules.profile.profile_skills import ProfileSkillsStoreMixin


class ProfileStore(
    ProfileSchemaMixin,
    ProfileSharedMixin,
    BaseProfileStoreMixin,
    ProfileCvUploadStoreMixin,
    ProfileSkillsStoreMixin,
    ProfilePreferredRolesStoreMixin,
    ProfileExperienceStoreMixin,
    ProfileEducationStoreMixin,
    ProfileCertificationsStoreMixin,
):
    def __init__(self, database_url: str, max_init_retries: int = 20, retry_delay_seconds: float = 1.0) -> None:
        self._database_url = database_url
        self._max_init_retries = max_init_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._initialize_schema()

    def _connect(self):
        return connect(self._database_url)
