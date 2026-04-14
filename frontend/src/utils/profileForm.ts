export function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

export function toMultiline(values: string[]): string {
  return values.join('\n')
}
