"""Response models for artwork analysis."""

from pydantic import BaseModel, ConfigDict, Field


class PrioritizedIssue(BaseModel):
    """Single critique issue with an explicit priority order."""

    title: str = Field(..., min_length=4, max_length=140, description='Short name of the issue.')
    diagnosis: str = Field(
        ...,
        min_length=20,
        max_length=600,
        description='Concrete diagnosis describing what is wrong.',
    )
    priority: int = Field(
        ...,
        ge=1,
        le=10,
        description='Issue rank where 1 is most important.',
    )


class TargetedDrill(BaseModel):
    """Practice activity tied to a specific skill gap."""

    name: str = Field(..., min_length=3, max_length=120, description='Drill name.')
    objective: str = Field(
        ...,
        min_length=12,
        max_length=400,
        description='What this drill is intended to improve.',
    )
    success_check: str = Field(
        ...,
        min_length=12,
        max_length=400,
        description='How the learner can verify successful execution.',
    )


class AnalysisResponse(BaseModel):
    """
    Structured pedagogy-first critique contract for analysis responses.

    This model intentionally favors deterministic, structured critique output.
    """

    score: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description='Score from 1 (beginner) to 10 (mastery). Null when no artwork was uploaded.',
    )
    rubric_anchors: list[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description='Short rubric anchors that justify the score assignment.',
    )
    prioritized_issues: list[PrioritizedIssue] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description='Ordered list of issues from highest to lowest priority.',
    )
    root_causes: list[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description='Underlying causes driving the observed issues.',
    )
    targeted_drills: list[TargetedDrill] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description='Drills mapped to the learner’s highest-impact gaps.',
    )
    readiness_gate: str = Field(
        ...,
        min_length=12,
        max_length=400,
        description='Readiness checkpoint that must be met before advanced topics.',
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description='Model confidence in the critique from 0.0 to 1.0.',
    )

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'score': 7,
                'rubric_anchors': [
                    'Solid gesture rhythm in major limbs',
                    'Perspective consistency breaks on torso box',
                ],
                'prioritized_issues': [
                    {
                        'title': 'Torso perspective drift',
                        'diagnosis': 'The ribcage box rotates without a shared horizon reference.',
                        'priority': 1,
                    },
                    {
                        'title': 'Forearm proportion mismatch',
                        'diagnosis': 'Right forearm length exceeds upper arm by roughly 20 percent.',
                        'priority': 2,
                    },
                ],
                'root_causes': [
                    'Construction lines were skipped before rendering.',
                    'Landmark checks were not done against a reference unit.',
                ],
                'targeted_drills': [
                    {
                        'name': 'Ribcage-box rotation sheet',
                        'objective': 'Lock a stable horizon while rotating torso boxes.',
                        'success_check': 'At least 8 of 10 boxes share coherent vanishing direction.',
                    }
                ],
                'readiness_gate': 'Advance to anatomy detail only after box perspective is stable.',
                'confidence': 0.86,
            }
        }
    )
