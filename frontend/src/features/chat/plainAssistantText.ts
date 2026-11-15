/** Remove model emphasis markers without changing the words or numeric values. */
export function plainAssistantText(text: string): string {
    return text.replaceAll('**', '');
}
