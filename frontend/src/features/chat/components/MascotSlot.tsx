import type { ReactNode } from 'react';
export interface MascotContext {
    status: 'idle' | 'composing' | 'conversation';
}
export type MascotRenderer = (context: MascotContext) => ReactNode;
/** A future animated mascot can render here without coupling to chat state or layout. */
export function MascotSlot({ render, status }: MascotContext & {
    render?: MascotRenderer;
}) {
    if (!render) return null;
    return <div className="mascot-slot">{render({ status })}</div>;
}
