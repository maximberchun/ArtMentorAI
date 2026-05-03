"""AI Agent service for artwork analysis using Pydantic AI and Gemini."""

import asyncio
import os
from typing import Any

import httpx
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from ..config import AppConfig
from ..exceptions import AIServiceError
from ..models import AnalysisResponse, ConversationChatResponse, ConversationTurnIntent

_BASE_PROMPT = (
    'Analyze the artwork with objective pedagogy-first standards.\n'
    'Follow these deterministic rules:\n'
    '1) Score with evidence, not tone. Use 1-10 only when artwork is present.\n'
    '2) Give exact diagnosis for each issue using this pattern:\n'
    '   - what is wrong\n'
    '   - why it is wrong (fundamental principle)\n'
    '   - how to verify the issue in the image\n'
    '3) Rank issues by learning dependency, not by surface visibility.\n'
    '4) Keep strictness adaptive:\n'
    '   - beginner/WIP/exploratory intent: strict on fundamentals, supportive on tone\n'
    '   - intermediate/advanced/polish intent: stricter technical bar and precision\n'
    '5) Do not jump to advanced anatomy/style advice before construction/form readiness.\n'
    '6) Rubric anchors must justify score ceilings and allow 10/10 when fundamentals are truly strong.\n\n'
    'Output fields to fill:\n'
    '- Concrete prioritized issues with exact diagnosis\n'
    '- Root causes behind the issues\n'
    '- Targeted drills with success checks\n'
    '- A readiness gate before advanced topics\n'
    '- A fair score from 1-10 (or null without artwork)\n'
    '- Confidence from 0.0 to 1.0\n\n'
    'Respond ONLY in valid JSON format, without additional explanations.'
)

_USER_CONTEXT_TEMPLATE = (
    "USER COMMENT: '{user_input}'. "
    "Address the user's specific concern first, then complete a full technical critique.\n\n"
    'Apply this response protocol:\n'
    '1) Diagnose stated concern with evidence from the artwork or text context.\n'
    '2) For every issue, include what is wrong, why, and how to verify.\n'
    '3) Calibrate strictness to intent signals in user comment/profile/conversation.\n'
    '4) Keep sequencing fundamentals-first before anatomy/detail/stylization.\n'
    '5) Assign score from objective rubric anchors, not encouragement style.\n\n'
    'Be specific about:\n'
    '- How well the user addressed their stated concern\n'
    '- Concrete prioritized issues (diagnosis + priority)\n'
    '- Root causes behind the visible mistakes\n'
    '- Targeted drills with success checks\n'
    '- A readiness gate before advanced topics\n'
    '- A fair score from 1-10 (or null without artwork)\n'
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
    "INSTRUCTION: Tailor strictness, vocabulary, and drill difficulty to the user's "
    'experience level, goals, preferred/disliked styles, and favorite artists. Keep '
    'technical truth constant, but adapt delivery and expected quality bar.'
)

_CONVERSATION_CONTEXT_SECTION = (
    '\n\n---\n'
    "RECENT CONVERSATION TURNS: '{conversation_context}'.\n"
    'INSTRUCTION: Preserve continuity with the thread and extract intent signals '
    '(exploration vs polish, WIP vs final). Use those signals to calibrate strictness '
    'while keeping objective standards.'
)

_NO_ARTWORK_SCORING_SECTION = (
    '\n\n---\n'
    'NO ARTWORK UPLOADED.\n'
    'INSTRUCTION: Because there is no image, do not assign a numeric artwork score. '
    'Return `"score": null` and focus feedback on the provided text context only.'
)

_CHAT_SYSTEM_PROMPT = """You are an experienced studio art mentor for learners.
Answer the user's question directly and usefully. Stay within visual art learning:
fundamentals, practice methods, books and courses, tools and materials, and constructive
study habits. You are not performing a structured artwork critique unless they uploaded an
image elsewhere in the product—here you only converse.

Use clear language; markdown lists and short headings are fine when they help readability.
If the question is ambiguous, ask one brief clarifying question. If you are unsure of a
fact, say so. Do not invent book titles or URLs; when web search is available, use it for
factual recommendations or references."""

_INTENT_CLASSIFIER_PROMPT = """You classify one user message for an art-mentoring conversation.

question_answering — General learning only: study methods, books, tools, materials, art history,
how a concept works, exercises explained in general, theory. The user is not asking for
structured feedback on their own specific artwork.

critique — They want feedback on THEIR work: something they made or are making (even if only
described in text), "what's wrong with this/my…", rate/review/roast my piece, how to improve
this drawing/painting they are working on, portfolio-style review of their execution.

Use RECENT CONVERSATION only to resolve pronouns ("it", "this") or when the thread is clearly
continuing feedback on the same piece — then prefer critique for short follow-ups.

If ambiguous, choose question_answering.

Respond only with the structured output fields."""

_SUGGESTION_ORDER = {
    'foundation': 0,
    'proportion_perspective': 1,
    'anatomy': 2,
    'style_detail': 3,
}

_SUGGESTION_STAGE_KEYWORDS = {
    'foundation': (
        'construction',
        'form',
        'gesture',
        'silhouette',
        'volume',
        'shape',
        'block-in',
        'block in',
    ),
    'proportion_perspective': (
        'proportion',
        'perspective',
        'foreshorten',
        'foreshortening',
        'horizon',
        'vanishing',
        'alignment',
        'measurement',
    ),
    'anatomy': (
        'anatomy',
        'muscle',
        'skeletal',
        'joint',
        'landmark',
        'ribcage',
        'pelvis',
        'limb',
        'torso',
    ),
    'style_detail': (
        'detail',
        'render',
        'rendering',
        'texture',
        'style',
        'stylization',
        'line weight',
        'shading',
        'polish',
        'finish',
    ),
}


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
        system_prompt = """You are a rigorous studio art instructor focused on fundamentals-first coaching.
                    Your job is objective diagnosis, fair scoring, and dependency-ordered next steps.

                    NON-NEGOTIABLE RULES:
                    1. Evaluate construction/form, proportion/perspective, anatomy, and finish quality.
                    2. Diagnose exactly: for each issue state what is wrong, why it breaks fundamentals,
                       and how the learner can verify it.
                    3. Score only from observable evidence and rubric anchors:
                       - 1-3: major foundational breakdowns
                       - 4-6: mixed fundamentals with clear blocking issues
                       - 7-8: solid fundamentals with limited high-impact errors
                       - 9-10: consistently strong fundamentals; 10 is allowed when justified
                    4. Use adaptive strictness:
                       - beginner/WIP intent: keep tone supportive, hold firm on fundamentals
                       - intermediate/advanced/polish intent: raise precision and tolerance thresholds
                    5. Sequence recommendations by dependency. Do not prescribe advanced anatomy/detail
                       before form/perspective readiness.
                    6. Be direct and respectful. No sugarcoating, no cruelty, no vague praise.
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
        self._register_web_search_tool(self.agent)

        chat_system = _CHAT_SYSTEM_PROMPT
        if config.web_search_enabled:
            chat_system += _WEB_SEARCH_SYSTEM_INSTRUCTIONS

        self.chat_agent = Agent(
            model=config.gemini.model_name,
            output_type=ConversationChatResponse,
            system_prompt=chat_system,
            retries=3,
        )
        self._register_web_search_tool(self.chat_agent)

        self.intent_agent = Agent(
            model=config.gemini.model_name,
            output_type=ConversationTurnIntent,
            system_prompt=_INTENT_CLASSIFIER_PROMPT,
            retries=2,
        )

        self.logger.info('AgentService initialized successfully')

    def _register_web_search_tool(self, target_agent: Agent) -> None:
        """Register a bounded web-search tool when enabled and configured."""
        if not self.config.web_search_enabled:
            return

        if not self.config.web_search_api_key:
            self.logger.warning(
                'Web-search tool enabled but WEB_SEARCH_API_KEY is missing; tool disabled.'
            )
            return

        tool_decorator: Any = getattr(target_agent, 'tool_plain', None)
        if tool_decorator is None:
            tool_decorator = getattr(target_agent, 'tool', None)
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

    @staticmethod
    def _build_chat_user_turn(
        user_input: str,
        profile_context: str | None,
        conversation_context: str | None,
    ) -> str:
        """User-side prompt for general Q&A (no artwork critique schema)."""
        prompt = (
            f'USER QUESTION:\n{user_input.strip()}\n\n'
            'Answer in the structured output; put the full answer in `reply`.'
        )
        if profile_context and profile_context.strip():
            prompt += _PROFILE_CONTEXT_SECTION.format(profile_context=profile_context.strip())
        if conversation_context and conversation_context.strip():
            prompt += _CONVERSATION_CONTEXT_SECTION.format(
                conversation_context=conversation_context.strip(),
            )
        return prompt

    @staticmethod
    def _build_intent_user_turn(
        user_input: str,
        conversation_context: str | None,
    ) -> str:
        parts = [f'MESSAGE TO CLASSIFY:\n{user_input.strip()}\n']
        if conversation_context and conversation_context.strip():
            parts.append(f'RECENT CONVERSATION:\n{conversation_context.strip()}\n')
        parts.append('Classify this message.')
        return '\n'.join(parts)

    @staticmethod
    def _infer_suggestion_stage(text: str) -> str:
        """Infer pedagogical stage from freeform issue/drill text."""
        lowered = text.lower()
        stage_order = (
            'foundation',
            'proportion_perspective',
            'anatomy',
            'style_detail',
        )
        best_stage = 'style_detail'
        best_count = 0
        for stage in stage_order:
            count = sum(1 for keyword in _SUGGESTION_STAGE_KEYWORDS[stage] if keyword in lowered)
            if count > best_count:
                best_stage = stage
                best_count = count
        if best_count > 0:
            return best_stage
        return 'style_detail'

    def _normalize_learning_dependency_order(
        self,
        analysis_data: AnalysisResponse,
    ) -> AnalysisResponse:
        """Reorder issues/drills to keep fundamentals-first learning progression."""
        prioritized_issues = list(analysis_data.prioritized_issues)
        targeted_drills = list(analysis_data.targeted_drills)
        issues_before = [issue.title for issue in prioritized_issues]
        drills_before = [drill.name for drill in targeted_drills]

        prioritized_issues.sort(
            key=lambda issue: (
                _SUGGESTION_ORDER[
                    self._infer_suggestion_stage(f'{issue.title} {issue.diagnosis}')
                ],
                issue.priority,
            )
        )
        for index, issue in enumerate(prioritized_issues, start=1):
            issue.priority = index

        targeted_drills.sort(
            key=lambda drill: _SUGGESTION_ORDER[
                self._infer_suggestion_stage(
                    f'{drill.name} {drill.objective} {drill.success_check}'
                )
            ]
        )

        issues_after = [issue.title for issue in prioritized_issues]
        drills_after = [drill.name for drill in targeted_drills]
        if issues_before != issues_after or drills_before != drills_after:
            self.logger.info(
                'Normalized critique ordering to fundamentals-first dependency sequence '
                '(issues_changed=%s, drills_changed=%s)',
                issues_before != issues_after,
                drills_before != drills_after,
            )

        analysis_data.prioritized_issues = prioritized_issues
        analysis_data.targeted_drills = targeted_drills
        return analysis_data

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

            analysis_data = self._normalize_learning_dependency_order(analysis_data)
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

    async def answer_conversation(
        self,
        user_input: str,
        profile_context: str | None = None,
        conversation_context: str | None = None,
    ) -> ConversationChatResponse:
        """Answer a general art-learning question (no structured critique output)."""
        try:
            self._search_calls_used = 0
            prompt = self._build_chat_user_turn(
                user_input,
                profile_context,
                conversation_context,
            )
            self.logger.info(
                'Starting conversation chat with Gemini %s',
                self.config.gemini.model_name,
            )
            result = await asyncio.wait_for(
                self.chat_agent.run(prompt),
                timeout=self._MODEL_RUN_TIMEOUT_SECONDS,
            )
            chat_data = result.output
            if not isinstance(chat_data, ConversationChatResponse):
                if isinstance(chat_data, dict):
                    chat_data = ConversationChatResponse(**chat_data)
                elif hasattr(chat_data, 'model_dump'):
                    chat_data = ConversationChatResponse(**chat_data.model_dump())
                else:
                    chat_data = ConversationChatResponse.model_validate(chat_data)
            if chat_data.analysis is not None:
                chat_data = chat_data.model_copy(update={'analysis': None})
            return chat_data  # noqa: TRY300
        except ModelHTTPError as e:
            self.logger.error('Gemini API error: %s (status=%s)', e.message, e.status_code)
            if e.status_code == 429:
                retry_after = self._extract_retry_delay(e.body)
                raise AIServiceError(
                    message='AI service quota exceeded. Please wait a moment before trying again.',
                    error_code='QUOTA_EXCEEDED',
                    retry_after=retry_after,
                ) from e
            if e.status_code == 503:
                raise AIServiceError(
                    message='AI service is temporarily unavailable. Please try again later.',
                    error_code='SERVICE_UNAVAILABLE',
                ) from e
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
            self.logger.exception('Error in conversation chat')
            msg = f'Gemini conversation error: {e!s}'
            raise ValueError(msg) from e

    async def classify_conversation_turn(
        self,
        user_input: str,
        conversation_context: str | None = None,
    ) -> ConversationTurnIntent:
        """Decide whether a text turn should use structured critique or general Q&A."""
        from ..utils.conversation_intent import is_text_only_critique_intent

        prompt = self._build_intent_user_turn(user_input, conversation_context)
        try:
            self.logger.info(
                'Classifying conversation turn with Gemini %s',
                self.config.gemini.model_name,
            )
            result = await asyncio.wait_for(
                self.intent_agent.run(prompt),
                timeout=self._MODEL_RUN_TIMEOUT_SECONDS,
            )
            data = result.output
            if not isinstance(data, ConversationTurnIntent):
                if isinstance(data, dict):
                    data = ConversationTurnIntent(**data)
                elif hasattr(data, 'model_dump'):
                    data = ConversationTurnIntent(**data.model_dump())
                else:
                    data = ConversationTurnIntent.model_validate(data)
            return data  # noqa: TRY300
        except Exception as e:
            self.logger.warning('Intent classification failed (%s); using keyword fallback', str(e))
            mode = 'critique' if is_text_only_critique_intent(user_input) else 'question_answering'
            return ConversationTurnIntent(mode=mode)

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
