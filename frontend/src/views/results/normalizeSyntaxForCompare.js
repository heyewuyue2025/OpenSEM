export function normalizeSyntaxForCompare(s) {
  return String(s || '')
    .split('\n')
    .map((row) => row.trim())
    .filter(Boolean)
    .join('\n')
}
