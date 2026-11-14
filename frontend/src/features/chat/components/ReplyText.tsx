import { useEffect, useLayoutEffect, useState } from 'react';

/** Reveal new replies without altering the complete answer stored in chat history. */
export function ReplyText({ text, animate, onProgress }: {
    text: string;
    animate: boolean;
    onProgress: () => void;
}) {
    const [visible, setVisible] = useState(() => animate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : Array.from(text).length);
    const characters = Array.from(text);
    const writing = animate && visible < characters.length;
    useEffect(() => {
        if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        let frame: number;
        const start = performance.now();
        const length = Array.from(text).length;
        const rate = Math.max(80, length / 12);
        const tick = (now: number) => {
            const count = Math.min(length, Math.floor((now - start) * rate / 1000));
            setVisible(count);
            if (count < length) frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(frame);
    }, [animate, text]);
    useLayoutEffect(() => {
        if (animate) onProgress();
    }, [animate, visible, onProgress]);
    return <p className={writing ? 'reply-writing' : undefined}>
        <span aria-hidden={writing || undefined}>{writing ? characters.slice(0, visible).join('') : text}</span>
        {writing && <span className="sr-only">Soily is writing a reply.</span>}
    </p>;
}
