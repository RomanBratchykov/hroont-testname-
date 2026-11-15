import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { replyWordDelay, replyWords } from '../replyWords';

/** Reveal new replies without altering the complete answer stored in chat history. */
export function ReplyText({ text, animate, onProgress, writing = false }: {
    text: string;
    animate: boolean;
    onProgress: () => void;
    writing?: boolean;
}) {
    if (!animate) return <p className={writing ? 'reply-writing' : undefined}>{text}</p>;
    // Mount a fresh writer when a reply arrives or animation is enabled after hydration.
    return <WritingReply key={text} text={text} onProgress={onProgress}/>;
}

function WritingReply({ text, onProgress }: { text: string; onProgress: () => void }) {
    const [visible, setVisible] = useState(0);
    const words = useMemo(() => replyWords(text), [text]);
    const writing = visible < words.length;
    useEffect(() => {
        if (!words.length) return;
        let count = 0;
        let timer: number;
        const reveal = () => {
            count++;
            setVisible(count);
            if (count < words.length) timer = window.setTimeout(reveal, replyWordDelay(words[count - 1]));
        };
        timer = window.setTimeout(reveal, replyWordDelay(''));
        return () => clearTimeout(timer);
    }, [words]);
    useLayoutEffect(() => {
        onProgress();
    }, [visible, onProgress]);
    return <p className={writing ? 'reply-writing' : undefined}>
        <span aria-hidden={writing || undefined}>{writing ? words.slice(0, visible).join('') : text}</span>
        {writing && <span className="sr-only">Soily is writing a reply.</span>}
    </p>;
}
