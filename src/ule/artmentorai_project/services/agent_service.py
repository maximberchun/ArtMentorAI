"""AI Agent service for artwork analysis using Pydantic AI and Gemini."""

import base64

from config import AppConfig
from models import AnalysisResponse
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel


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
        self.gemini_model = GeminiModel(
            model_name=config.gemini.model_name, api_key=config.gemini.api_key
        )

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
            model=self.gemini_model,
            result_type=AnalysisResponse,
            system_prompt=system_prompt,
        )

        self.logger.info('AgentService initialized successfully')

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = 'image/jpeg',  # noqa: ARG002
    ) -> AnalysisResponse:
        """
        Analyze an artwork image using Gemini 2.5 Pro.

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
            base64.standard_b64encode(image_bytes).decode('utf-8')

            # Create user prompt
            prompt = """Please analyze this artwork in detail and provide a structured critique.

                    Be specific regarding:
                    - Identified technical strengths
                    - Concrete technical errors (anatomy, perspective, composition, etc.)
                    - A fair score
                    - Practical advice for improvement

                    Respond ONLY in valid JSON format, with no additional explanations."""

            self.logger.info('Starting artwork analysis with Gemini 2.5 Pro')

            # Call agent (Pydantic AI handles image multimodal with Gemini)
            result = await self.agent.run(user_prompt=prompt)

            self.logger.info('Analysis completed. Score: %s/10', result.data.score)
        except Exception as e:
            self.logger.exception('Error analyzing image')
            msg = f'Gemini image analysis error: {e!s}'
            raise ValueError(msg) from e
        else:
            return result.data
