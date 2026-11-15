import { replyWordDelay, replyWords } from './replyWords.ts';

function pause(milliseconds: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve, reject) => {
        signal.throwIfAborted();
        const abort = () => { clearTimeout(timer); reject(signal.reason); };
        const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve(); }, milliseconds);
        signal.addEventListener('abort', abort, { once: true });
    });
}

/** Publish actual visible prefixes, never the complete reply before its final word. */
export async function revealReply(
    text: string,
    publish: (visible: string) => void,
    signal: AbortSignal,
    wait: (milliseconds: number, signal: AbortSignal) => Promise<void> = pause,
): Promise<void> {
    const words = replyWords(text);
    let visible = '';
    for (let index = 0; index < words.length; index++) {
        signal.throwIfAborted();
        await wait(index ? replyWordDelay(words[index - 1]) : replyWordDelay(''), signal);
        signal.throwIfAborted();
        visible += words[index];
        publish(visible);
    }
}
