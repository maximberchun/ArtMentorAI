"""AI Agent service for artwork analysis using Pydantic AI and Gemini."""

import os

from pydantic_ai import Agent, BinaryContent

from ..config import AppConfig
from ..models import AnalysisResponse


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
            result_type=AnalysisResponse,
            system_prompt=system_prompt,
        )

        self.logger.info('AgentService initialized successfully')

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = 'image/jpeg',
    ) -> AnalysisResponse:
        """
        Analyze an artwork image using Gemini 2.5 Flash.

        Args:
            image_bytes: Raw image bytes to analyze
            mime_type: MIME type of the image (image/jpeg, image/png, etc.)

        Returns:
            AnalysisResponse: Structured analysis with summary, score, errors, and advice

        Raises:
            ValueError: If there's an error calling Gemini
            ValidationError: If response doesn't match AnalysisResponse model
        """
        try:
            # Encode image to base64
            image_content = BinaryContent(data=image_bytes, media_type=mime_type)

            # Create user prompt
            prompt = """Please analyze this artwork in detail and provide a structured critique.

                    Be specific regarding:
                    - Identified technical strengths
                    - Concrete technical errors (anatomy, perspective, composition, etc.)
                    - A fair score
                    - Practical advice for improvement

                    Respond ONLY in valid JSON format, with no additional explanations."""

            self.logger.info('Starting artwork analysis with Gemini 2.5 Flash')

            # Call agent (Pydantic AI handles image multimodal with Gemini)
            result = await self.agent.run([prompt, image_content])
            analysis_data = result.data

            # If result is a dict, convert to AnalysisResponse
            if isinstance(analysis_data, dict):
                analysis_data = AnalysisResponse(**analysis_data)
            elif not isinstance(analysis_data, AnalysisResponse):
                # Try to convert via model_validate
                try:
                    analysis_data = AnalysisResponse.model_validate(analysis_data)
                except (TypeError, ValueError):
                    # Last resort: convert to dict then to model
                    if hasattr(analysis_data, 'model_dump'):
                        analysis_data = AnalysisResponse(**analysis_data.model_dump())
                    else:
                        analysis_data = AnalysisResponse(**dict(analysis_data))

            self.logger.info('Analysis completed. Score: %s/10', analysis_data.score)
            if hasattr(analysis_data, 'model_dump'):
                return analysis_data.model_dump()
            if isinstance(analysis_data, dict):
                return analysis_data
            return AnalysisResponse(**vars(analysis_data))
        except Exception as e:
            self.logger.exception('Error analyzing image')
            msg = f'Gemini image analysis error: {e!s}'
            raise ValueError(msg) from e
        else:
            return result.data if hasattr(result, 'data') else result
