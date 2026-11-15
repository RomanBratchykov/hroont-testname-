import { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { replyWords } from '../replyWords';

/** Reveal new replies without altering the complete answer stored in chat history. */
export function ReplyText({ text, animate, onProgress }: {
    text: string;
    animate: boolean;
    onProgress: () => void;
}) {
    if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return <p>{text}</p>;
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
        const timer = window.setInterval(() => {
            count++;
            setVisible(count);
            if (count >= words.length) clearInterval(timer);
        }, 45);
        return () => clearInterval(timer);
    }, [words]);
    useLayoutEffect(() => {
        onProgress();
    }, [visible, onProgress]);
    return <p className={writing ? 'reply-writing' : undefined}>
        <span aria-hidden={writing || undefined}>{writing ? words.slice(0, visible).join('') : text}</span>
        {writing && <span className="sr-only">Soily is writing a reply.</span>}
    </p>;
}
