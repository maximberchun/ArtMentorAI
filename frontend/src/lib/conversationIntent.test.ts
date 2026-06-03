import { describe, expect, it } from 'vitest'

import { isTextOnlyCritiqueIntent } from './conversationIntent'

describe('isTextOnlyCritiqueIntent', () => {
  it('treats book-style questions as chat', () => {
    expect(isTextOnlyCritiqueIntent('What book do you recommend for learning drawing?')).toBe(false)
  })

  it('treats critique phrasing as critique', () => {
    expect(isTextOnlyCritiqueIntent('Please critique this artwork')).toBe(true)
    expect(isTextOnlyCritiqueIntent("What's wrong with my proportions?")).toBe(true)
  })
})
