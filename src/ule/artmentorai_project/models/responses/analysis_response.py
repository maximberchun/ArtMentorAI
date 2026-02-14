"""Response models for artwork analysis."""

from typing import ClassVar

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """
    Structured response for artwork analysis.

    This model validates the AI response to ensure it meets all requirements.
    Pydantic automatically validates types, ranges, and string lengths.
    """

    summary: str = Field(
        ..., min_length=10, max_length=500, description='General summary of the artwork analysis'
    )

    score: int = Field(..., ge=1, le=10, description='Score from 1 (beginner) to 10 (mastery)')

    technical_errors: list[str] = Field(
        default=[],
        min_items=0,
        max_items=10,
        description='List of identified technical errors (anatomy, perspective, etc.)',
    )

    constructive_advice: str = Field(
        ...,
        min_length=20,
        max_length=500,
        description='Practical and constructive advice for improvement',
    )

    class Config:
        """Pydantic configuration for the AnalysisResponse model."""

        json_schema_extra: ClassVar = {
            'example': {
                'summary': 'Figure drawing with good proportions but perspective errors',
                'score': 7,
                'technical_errors': [
                    'Inconsistent linear perspective',
                    'Right arm slightly disproportionate',
                ],
                'constructive_advice': (
                    'Practice head construction with guide lines. Your work shows potential; '
                    'focus on perspective studies.'
                ),
            }
        }
