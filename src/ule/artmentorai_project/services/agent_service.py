"""AI Agent service for artwork analysis using Pydantic AI and Gemini."""

import asyncio
import os
from typing import Any

import httpx
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from ..config import AppConfig
from ..exceptions import AIServiceError
from ..models import AnalysisResponse

_BASE_PROMPT = (
    'Please analyze this artwork in detail and provide a structured critique.\n'
    'Be specific about:\n'
    '- Concrete prioritized issues with direct diagnosis\n'
    '- Root causes behind the issues\n'
    '- Targeted drills with success checks\n'
    '- A readiness gate before advanced topics\n'
    '- A fair score from 1-10\n'
    '- Confidence from 0.0 to 1.0\n\n'
    'Respond ONLY in valid JSON format, without additional explanations.'
)

_USER_CONTEXT_TEMPLATE = (
    "USER COMMENT: '{user_input}'. "
    "Please address the user's specific concerns in your critique "
    'while also covering general technical aspects.\n\n'
    'Be specific about:\n'
    '- How well the user addressed their stated concerns\n'
    '- Concrete prioritized issues (with diagnosis and priority)\n'
    '- Root causes behind the visible mistakes\n'
    '- Targeted drills with success checks\n'
    '- A readiness gate before advanced topics\n'
    '- A fair score from 1-10\n'
    '- Confidence from 0.0 to 1.0\n\n'
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

_CONVERSATION_CONTEXT_SECTION = (
    '\n\n---\n'
    "RECENT CONVERSATION TURNS: '{conversation_context}'.\n"
    'INSTRUCTION: Preserve continuity with the recent thread while prioritizing the '
    'current artwork and user request.'
)

_NO_ARTWORK_SCORING_SECTION = (
    '\n\n---\n'
    'NO ARTWORK UPLOADED.\n'
    'INSTRUCTION: Because there is no image, do not assign a numeric artwork score. '
    'Return `"score": null` and focus feedback on the provided text context only.'
)


_WEB_SEARCH_SYSTEM_INSTRUCTIONS = """
                    6. Use tool `web_search` only when you need external factual references
                       (e.g., artist context, art-history facts, medium techniques).
                    7. Never use web search for private user data, secrets, or policy decisions.
                    8. Use concise, focused queries and at most a few tool calls.
                    9. If tool output is unavailable, continue without fabricating citations.
"""


class AgentService:
    """Service for AI-powered artwork analysis using Pydantic AI and Gemini."""
    _MODEL_RUN_TIMEOUT_SECONDS = 60.0

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize the agent service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = config.logger
        self._search_calls_used = 0

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
                    """

        if config.web_search_enabled:
            system_prompt += _WEB_SEARCH_SYSTEM_INSTRUCTIONS

        system_prompt += """

                    REQUIRED RESPONSE (JSON):
                    {
                        "score": 7,
                        "rubric_anchors": ["Anchor 1", "Anchor 2"],
                        "prioritized_issues": [
                            {
                                "title": "Issue title",
                                "diagnosis": "What is wrong and why",
                                "priority": 1
                            }
                        ],
                        "root_causes": ["Cause 1", "Cause 2"],
                        "targeted_drills": [
                            {
                                "name": "Drill name",
                                "objective": "What it trains",
                                "success_check": "How to verify completion"
                            }
                        ],
                        "readiness_gate": "What must be stable before advanced topics",
                        "confidence": 0.82
                    }"""

        # Create agent
        self.agent = Agent(
            model=config.gemini.model_name,  # Reads from .env
            output_type=AnalysisResponse,
            system_prompt=system_prompt,
            retries=3,
        )
        self._register_web_search_tool()

        self.logger.info('AgentService initialized successfully')

    def _register_web_search_tool(self) -> None:
        """Register a bounded web-search tool when enabled and configured."""
        if not self.config.web_search_enabled:
            return

        if not self.config.web_search_api_key:
            self.logger.warning(
                'Web-search tool enabled but WEB_SEARCH_API_KEY is missing; tool disabled.'
            )
            return

        tool_decorator: Any = getattr(
            self.agent,
            'tool_plain',
            None,
        )
        if tool_decorator is None:
            tool_decorator = getattr(self.agent, 'tool', None)
        if tool_decorator is None:
            self.logger.warning('Current PydanticAI Agent implementation has no tool decorator.')
            return

        @tool_decorator
        async def web_search(query: str) -> str:
            """Fetch concise factual references from web search."""
            cleaned_query = ' '.join(query.split()).strip()
            if not cleaned_query:
                self.logger.info('Web-search tool call skipped: empty query')
                return 'Web search skipped: empty query.'

            max_chars = self.config.web_search_max_query_chars
            if len(cleaned_query) > max_chars:
                cleaned_query = cleaned_query[:max_chars]

            if self._search_calls_used >= self.config.web_search_max_calls_per_request:
                self.logger.info(
                    'Web-search tool call skipped: limit reached (%d/%d)',
                    self._search_calls_used,
                    self.config.web_search_max_calls_per_request,
                )
                return (
                    'Web search skipped: per-request tool-call limit reached. '
                    'Continue with available context.'
                )

            self._search_calls_used += 1
            self.logger.info(
                'Web-search tool call %d/%d | query="%s"',
                self._search_calls_used,
                self.config.web_search_max_calls_per_request,
                cleaned_query,
            )
            results = await self._run_serper_search(cleaned_query)
            if not results:
                self.logger.info(
                    'Web-search tool returned no results for query="%s"',
                    cleaned_query,
                )
                return 'No reliable web results were retrieved.'

            self.logger.info(
                'Web-search tool returned %d result(s) for query="%s"',
                len(results),
                cleaned_query,
            )
            lines = [
                f"- {item['title']} ({item['url']}): {item['snippet']}"
                for item in results
                if item.get('title') and item.get('url')
            ]
            return '\n'.join(lines) if lines else 'No reliable web results were retrieved.'

        self.logger.info(
            'Web-search tool registered (provider=%s, max_calls=%d, max_results=%d)',
            self.config.web_search_provider,
            self.config.web_search_max_calls_per_request,
            self.config.web_search_max_results,
        )

    async def _run_serper_search(self, query: str) -> list[dict[str, str]]:
        """Execute Serper search and return sanitized snippets."""
        if self.config.web_search_provider != 'serper' or not self.config.web_search_api_key:
            return []

        endpoint = 'https://google.serper.dev/search'
        headers = {
            'X-API-KEY': self.config.web_search_api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'q': query,
            'num': self.config.web_search_max_results,
        }

        self.logger.debug(
            'Executing provider web search (provider=%s, max_results=%d)',
            self.config.web_search_provider,
            self.config.web_search_max_results,
        )
        try:
            timeout = httpx.Timeout(self.config.web_search_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning('Web-search request failed: %s', str(exc))
            return []

        organic = data.get('organic', [])
        if not isinstance(organic, list):
            return []

        safe_results: list[dict[str, str]] = []
        for item in organic[: self.config.web_search_max_results]:
            if not isinstance(item, dict):
                continue
            title = str(item.get('title', '')).strip()
            url = str(item.get('link', '')).strip()
            snippet = str(item.get('snippet', '')).strip()
            if not title or not url:
                continue
            safe_results.append(
                {
                    'title': title[:180],
                    'url': url[:500],
                    'snippet': snippet[:320],
                }
            )
        return safe_results

    @staticmethod
    def _build_prompt(
        user_input: str | None,
        past_critiques: str | None,
        profile_context: str | None,
        conversation_context: str | None,
        has_artwork: bool,
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
            conversation_context: Optional recent conversation turns used for
                short-term memory continuity.
            has_artwork: Whether an artwork image was provided in the request.

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

        if conversation_context and conversation_context.strip():
            prompt += _CONVERSATION_CONTEXT_SECTION.format(
                conversation_context=conversation_context.strip(),
            )

        if not has_artwork:
            prompt += _NO_ARTWORK_SCORING_SECTION

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
        conversation_context: str | None = None,
        has_artwork: bool = True,
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
            conversation_context: Optional short-term thread context injected from
                recent user/assistant turns.
            has_artwork: True when an image is provided in the request.

        Returns:
            AnalysisResponse: Structured analysis with pedagogical critique fields.

        Raises:
            ValueError: If there's an error calling Gemini or validating the response.
        """
        try:
            self._search_calls_used = 0
            # Create user prompt
            prompt = self._build_prompt(
                user_input,
                past_critiques,
                profile_context,
                conversation_context,
                has_artwork,
            )
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
            self.logger.info(
                'Submitting request to Gemini (timeout=%ss, web_search_enabled=%s)',
                self._MODEL_RUN_TIMEOUT_SECONDS,
                self.config.web_search_enabled,
            )
            result = await asyncio.wait_for(
                self.agent.run(message),
                timeout=self._MODEL_RUN_TIMEOUT_SECONDS,
            )
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
        except TimeoutError as e:
            self.logger.error(
                'Gemini request timed out after %ss',
                self._MODEL_RUN_TIMEOUT_SECONDS,
            )
            raise AIServiceError(
                message='AI request timed out. Please try again.',
                error_code='TIMEOUT',
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
