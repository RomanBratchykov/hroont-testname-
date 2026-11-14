import type { ReactNode } from 'react';
export interface MascotContext {
    status: 'idle' | 'composing' | 'conversation';
}
export type MascotRenderer = (context: MascotContext) => ReactNode;
/** A future animated mascot can render here without coupling to chat state or layout. */
export function MascotSlot({ render, status }: MascotContext & {
    render?: MascotRenderer;
}) {
    return <div className="mascot-slot">{render ? render({ status }) : <svg className="brand-bloom" width="52" height="52" viewBox="0 0 60 60" aria-hidden="true">{Array.from({ length: 10 }, (_, i) => <ellipse key={i} cx="30" cy="16" rx="4.5" ry="14" fill="currentColor" transform={`rotate(${i * 36} 30 30)`}/>)}<circle cx="30" cy="30" r="8" fill="currentColor"/></svg>}</div>;
}
