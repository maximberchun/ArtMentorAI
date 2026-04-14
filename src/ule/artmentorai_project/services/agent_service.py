"""AI Agent service for artwork analysis using Pydantic AI and Gemini."""

import os

from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from ..config import AppConfig
from ..exceptions import AIServiceError
from ..models import AnalysisResponse

_BASE_PROMPT = (
    'Please analyze this artwork in detail and provide a structured critique.\n'
    'Be specific about:\n'
    '- Identified technical strengths\n'
    '- Concrete technical errors (anatomy, perspective, composition, etc.)\n'
    '- A fair score from 1-10\n'
    '- Practical advice for improvement\n\n'
    'Respond ONLY in valid JSON format, without additional explanations.'
)

_USER_CONTEXT_TEMPLATE = (
    "USER COMMENT: '{user_input}'. "
    "Please address the user's specific concerns in your critique "
    'while also covering general technical aspects.\n\n'
    'Be specific about:\n'
    '- How well the user addressed their stated concerns\n'
    '- Concrete technical errors (anatomy, perspective, composition, etc.)\n'
    '- A fair score from 1-10\n'
    '- Practical and actionable advice for improvement\n\n'
    'Respond ONLY in valid JSON format, without additional explanations.'
)

_PAST_CRITIQUES_SECTION = (
    '\n\n---\n'
    "USER HISTORY (Past Memory): '{past_critiques}'.\n"
    'INSTRUCTION: Review whether the user has improved on these past errors '
    'or whether they are repeating them. '
    'Be encouraging if they improved, but correct them gently if they repeat mistakes.'
)

_PROFILE_CONTEXT_SECTION = (
    '\n\n---\n'
    "USER PROFILE: '{profile_context}'.\n"
    "INSTRUCTION: Tailor your critique to the user's stated goals, preferred "
    'and disliked styles, favorite artists, and experience level. When giving '
    'advice, connect it explicitly to these preferences when helpful.'
)


class AgentService:
    """Service for AI-powered artwork analysis using Pydantic AI and Gemini."""

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the agent service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = config.logger

        # Initialize Gemini model
        os.environ['GEMINI_API_KEY'] = config.gemini.api_key

        # System Prompt - Defines the agent role
        system_prompt = """You are an expert and rigorous art teacher with over 20 years of
                    experience. Your task is to evaluate student artwork with constructive honesty.

                    CRITICAL INSTRUCTIONS:
                    1. Analyze composition, technique, anatomy, and perspective.
                    2. Be SPECIFIC about the identified technical errors.
                    3. Provide a FAIR score between 1 (beginner) and 10 (mastery).
                    4. The advice must be PRACTICAL and actionable.
                    5. Be encouraging but honest - the goal is student growth.

                    REQUIRED RESPONSE (JSON):
                    {
                        "summary": "1-3 sentence summary of the general analysis",
                        "score": 7,
                        "technical_errors": ["Error 1", "Error 2", ...],
                        "constructive_advice": "Specific and actionable advice for improvement"
                    }"""

        # Create agent
        self.agent = Agent(
            model=config.gemini.model_name,  # Reads from .env
            output_type=AnalysisResponse,
            system_prompt=system_prompt,
            retries=3,
        )

        self.logger.info('AgentService initialized successfully')

    @staticmethod
    def _build_prompt(
        user_input: str | None,
        past_critiques: str | None,
        profile_context: str | None,
    ) -> str:
        """Construct the user-turn prompt sent to Gemini.

        When the user has provided a comment, the comment is surfaced at the
        top of the prompt so that Gemini addresses it explicitly before moving
        on to the standard technical checklist.  When no comment is present the
        base prompt is used unchanged.

        Args:
            user_input: Optional free-text comment from the user, e.g.
                        "I struggled with the nose".
            past_critiques: Pre-formatted string of past critique summaries and
                advice retrieved from the vector DB, or ``None`` if
                no history exists yet.
            profile_context: Optional textual summary of the user profile used
                to personalise the critique (goals, preferences, artists, level).

        Returns:
            A fully-formed prompt string ready to pass to ``agent.run()``.
        """
        if user_input and user_input.strip():
            prompt = _USER_CONTEXT_TEMPLATE.format(user_input=user_input.strip())
        else:
            prompt = _BASE_PROMPT

        if profile_context and profile_context.strip():
            prompt += _PROFILE_CONTEXT_SECTION.format(
                profile_context=profile_context.strip(),
            )

        if past_critiques and past_critiques.strip():
            prompt += _PAST_CRITIQUES_SECTION.format(past_critiques=past_critiques.strip())

        return prompt

    async def analyze_image(
        self,
        image_bytes: bytes | None = None,
        mime_type: str | None = None,
        user_input: str | None = None,
        past_critiques: str | None = None,
        profile_context: str | None = None,
    ) -> AnalysisResponse:
        """
        Analyze an artwork request using Gemini (multimodal: image and/or text).

        This method supports:

        - Image-only analysis (when ``image_bytes`` is provided).
        - Text-only analysis (when only ``user_input`` is provided).
        - Combined image + text analysis enriched with optional past critiques.

        Args:
            image_bytes: Raw image bytes to analyze, if any.
            mime_type: MIME type of the image (image/jpeg, image/png, etc.).
            user_input: Optional user-provided context or specific concerns.
            past_critiques: Optional string of previous critiques to inform the analysis.
            profile_context: Optional textual summary of the user profile used
                to personalise the critique (goals, preferences, artists, level).

        Returns:
            AnalysisResponse: Structured analysis with summary, score, errors, and advice.

        Raises:
            ValueError: If there's an error calling Gemini or validating the response.
        """
        try:
            # Create user prompt
            prompt = self._build_prompt(user_input, past_critiques, profile_context)
            message: list = [prompt]
            if image_bytes is not None:
                message.append(
                    BinaryContent(data=image_bytes, media_type=mime_type or 'image/jpeg')
                )

            if user_input and user_input.strip():
                self.logger.info(
                    'Starting artwork analysis with Gemini %s (with user comment)',
                    self.config.gemini.model_name,
                )
            else:
                self.logger.info(
                    'Starting artwork analysis with Gemini %s (standard analysis)',
                    self.config.gemini.model_name,
                )

            # Call agent (Pydantic AI handles image multimodal with Gemini)
            result = await self.agent.run(message)
            analysis_data = result.output

            # Normalise result to AnalysisResponse
            if not isinstance(analysis_data, AnalysisResponse):
                if isinstance(analysis_data, dict):
                    analysis_data = AnalysisResponse(**analysis_data)
                elif hasattr(analysis_data, 'model_dump'):
                    analysis_data = AnalysisResponse(**analysis_data.model_dump())
                else:
                    analysis_data = AnalysisResponse.model_validate(analysis_data)

            self.logger.info('Analysis completed. Score: %s/10', analysis_data.score)
            return analysis_data  # noqa: TRY300
        except ModelHTTPError as e:
            self.logger.error('Gemini API error: %s (status=%s)', e.message, e.status_code)
            if e.status_code == 429:
                retry_after = self._extract_retry_delay(e.body)
                raise AIServiceError(
                    message='AI service quota exceeded. Please wait a moment before trying again.',
                    error_code='QUOTA_EXCEEDED',
                    retry_after=retry_after,
                ) from e
            elif e.status_code == 503:
                raise AIServiceError(
                    message='AI service is temporarily unavailable. Please try again later.',
                    error_code='SERVICE_UNAVAILABLE',
                ) from e
            elif e.status_code == 503:
                raise AIServiceError(
                    message='AI service is temporarily unavailable. Please try again later.',
                    error_code='SERVICE_UNAVAILABLE',
                ) from e
            else:
                raise AIServiceError(
                    message=f'AI service error: {e.message}',
                    error_code='API_ERROR',
                ) from e
        except UnexpectedModelBehavior as e:
            self.logger.error('AI model output validation failed: %s', e.message)
            raise AIServiceError(
                message='AI response format invalid. Please try again.',
                error_code='OUTPUT_VALIDATION_ERROR',
            ) from e
        except Exception as e:
            self.logger.exception('Error analyzing image')
            msg = f'Gemini image analysis error: {e!s}'
            raise ValueError(msg) from e

    @staticmethod
    def _extract_retry_delay(body: dict) -> float | None:
        """Extract retry delay from API error response body."""
        try:
            details = body.get('details', [])
            for detail in details:
                if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                    retry_delay = detail.get('retryDelay', '')
                    if retry_delay.endswith('s'):
                        return float(retry_delay[:-1])
        except Exception:
            pass
        return None
