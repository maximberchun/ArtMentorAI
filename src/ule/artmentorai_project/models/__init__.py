"""
The `models` package contains the data models used across the API.

This package typically includes:
- Request models (`models.requests`) for validating and parsing client input.
- Response models (`models.responses`) for structuring and validating API output.
- (Optional) Domain or persistence models that represent internal entities.

Files placed here should define the shape of the data exchanged within
the application and with external clients. Models must remain focused
on data representation, separate from business logic (`services`) and
infrastructure concerns (`core`).
"""

from .responses import (
    AnalysisResponse,
    ConversationChatResponse,
    ConversationTurnIntent,
    PortfolioHistoryItem,
    PortfolioUploadResponse,
    ProgressMeResponse,
    ProgressSnapshotSummary,
)
from .auth_user import AuthUser
from .user_profile import UserProfile, UserProfileBase

__all__ = [
    'AnalysisResponse',
    'ConversationChatResponse',
    'ConversationTurnIntent',
    'AuthUser',
    'PortfolioHistoryItem',
    'PortfolioUploadResponse',
    'ProgressMeResponse',
    'ProgressSnapshotSummary',
    'UserProfile',
    'UserProfileBase',
]

