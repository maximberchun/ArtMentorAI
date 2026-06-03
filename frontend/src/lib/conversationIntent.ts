/**
 * Keyword heuristics for critique-shaped text (mirrors server fallback).
 * Routing in the app is done by the API classifier; this module is optional for clients.
 */
const CRITIQUE_HINT_PATTERNS: RegExp[] = [
  /\b(critique|criticize|criticise)\b/i,
  /\b(rate|review|roast)\s+my\b/i,
  /\bfeedback\s+on\s+(my|this|the|it)\b/i,
  /\bwhat(?:'s| is)\s+wrong\s+with\s+(my|this|these|it)\b/i,
  /\bhow\s+can\s+i\s+improve\s+(this|it|my|the)\b/i,
  /\bplease\s+(critique|criticize|criticise|review)\b/i,
  /\b(look|check)\s+at\s+my\b/i,
]

export function isTextOnlyCritiqueIntent(message: string): boolean {
  const normalized = message.trim().replace(/\s+/g, ' ')
  if (!normalized) return false
  return CRITIQUE_HINT_PATTERNS.some((re) => re.test(normalized))
}
