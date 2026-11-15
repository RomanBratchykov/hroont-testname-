import { useCallback, useEffect, useRef } from 'react';

/** Gently follow growing replies; scrolling up lets the reader keep their place. */
export function useReplyScroll(enabled = true) {
    const end = useRef<HTMLDivElement>(null);
    const frame = useRef<number | null>(null);
    const following = useRef(true);
    const followReply = useCallback(() => {
        if (!enabled || !following.current || frame.current !== null) return;
        const tick = () => {
            if (!following.current || !end.current) { frame.current = null; return; }
            const remaining = end.current.getBoundingClientRect().bottom - window.innerHeight + 16;
            const available = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
            if (remaining <= 1 || available <= 1) { frame.current = null; return; }
            window.scrollBy({ top: Math.min(8, Math.max(1, remaining * .08), available), behavior: 'instant' });
            frame.current = requestAnimationFrame(tick);
        };
        frame.current = requestAnimationFrame(tick);
    }, [enabled]);
    useEffect(() => {
        if (!enabled) return;
        let lastY = window.scrollY;
        const scroll = () => {
            if (window.scrollY < lastY - 2) following.current = false;
            else if (document.documentElement.scrollHeight - window.innerHeight - window.scrollY < 100) following.current = true;
            lastY = window.scrollY;
        };
        const wheel = (event: WheelEvent) => { if (event.deltaY < 0) following.current = false; };
        window.addEventListener('scroll', scroll, { passive: true });
        window.addEventListener('wheel', wheel, { passive: true });
        return () => {
            window.removeEventListener('scroll', scroll); window.removeEventListener('wheel', wheel);
            if (frame.current !== null) cancelAnimationFrame(frame.current);
            frame.current = null;
        };
    }, [enabled]);
    const resumeFollowing = useCallback(() => { following.current = true; followReply(); }, [followReply]);
    return { end, followReply, resumeFollowing };
}
