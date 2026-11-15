/** Preserve every character while revealing only complete words. */
export function replyWords(text: string): string[] {
    return text.match(/\s*\S+\s*|\s+/gu) ?? [];
}
