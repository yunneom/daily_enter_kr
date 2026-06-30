/**
 * Brand safety — enforce on any OG/share copy generation.
 *
 * Mirrors the Python pipeline's SUMMARY_PROMPT guardrails:
 *   - No clickbait / sensational vocabulary (BANNED_WORDS).
 *   - No emoji.
 *   - Numbers are allowed.
 *   - Source "한국기업평판연구소" must remain attributable.
 */

export const BANNED_WORDS = [
  "충격",
  "발칵",
  "경악",
  "오열",
  "폭로",
  "이럴 수가",
  "결국",
  "도대체",
  "역대급",
  "안 본 사람 손해",
  "당신만 모름",
] as const;

export const SOURCE_ATTRIBUTION = "한국기업평판연구소";

// Emoji detection. Covers the common emoji & pictograph ranges plus
// variation selectors / ZWJ sequences used to build composite emoji.
const EMOJI_REGEX =
  /[\u{1F1E6}-\u{1F1FF}\u{1F300}-\u{1F5FF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}\u{FE0F}\u{200D}]/u;

function findBannedWord(text: string): string | null {
  for (const w of BANNED_WORDS) {
    if (text.includes(w)) return w;
  }
  return null;
}

export function isSafeCopy(text: string): boolean {
  if (!text) return true;
  if (findBannedWord(text)) return false;
  if (EMOJI_REGEX.test(text)) return false;
  return true;
}

/**
 * Throws Error if copy violates brand safety. Use before rendering any
 * dynamic text into OG cards / share messages.
 */
export function assertSafeCopy(text: string): void {
  const banned = findBannedWord(text);
  if (banned) {
    throw new Error(`unsafe copy: contains banned word "${banned}"`);
  }
  if (EMOJI_REGEX.test(text)) {
    throw new Error("unsafe copy: contains emoji");
  }
}
