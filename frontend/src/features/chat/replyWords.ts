/** Preserve every character while revealing only complete words. */
export function replyWords(text: string): string[] {
    return text.match(/\s*\S+\s*|\s+/gu) ?? [];
}

/** Reading pauses apply after the current word, including its trailing whitespace. */
export function replyWordDelay(word: string): number {
    if (/\n\s*\n/u.test(word)) return 550;
    if (/[.!?…]["'”’)]*\s*$/u.test(word)) return 400;
    if (/[,;:]["'”’)]*\s*$/u.test(word)) return 240;
    return 150;
}
