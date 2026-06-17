from pydantic import BaseModel
from typing import Optional

class ProfileUpdate(BaseModel):
    role_title:         Optional[str]         = None
    skills_summary:     Optional[str]         = None
    experience_years:   Optional[int]         = None
    inclusion_keywords: Optional[list[str]]   = None
    exclusion_keywords: Optional[list[str]]   = None
    salary_min:         Optional[int]         = None
    salary_max:         Optional[int]         = None
    work_type:          Optional[str]         = None
    preferred_regions:  Optional[list[str]]   = None
    alerts_paused:      Optional[bool]        = None
    onboarding_complete:Optional[bool]        = None

class NotificationSettingsUpdate(BaseModel):
    channels:   Optional[list[str]] = None    # ['telegram']
    frequency:  Optional[str]       = None    # 'immediate' | 'digest'

class UserProfileOut(BaseModel):
    role_title:         Optional[str]
    skills_summary:     Optional[str]
    experience_years:   Optional[int]
    inclusion_keywords: list[str]
    exclusion_keywords: list[str]
    salary_min:         Optional[int]
    salary_max:         Optional[int]
    work_type:          str
    preferred_regions:  list[str]
    alerts_paused:      bool
    onboarding_complete:bool

    class Config:
        from_attributes = True

class NotificationSettingsOut(BaseModel):
    channels:           list[str]
    frequency:          str
    telegram_connected: bool

    class Config:
        from_attributes = True
