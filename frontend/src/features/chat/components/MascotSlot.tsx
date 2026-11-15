import type { ReactNode } from 'react';
import { Mascot } from '../../../components/Mascot';
import type { MascotStatus } from '../../../components/Mascot';
export interface MascotContext {
    status: MascotStatus;
}
export type MascotRenderer = (context: MascotContext) => ReactNode;
/** Keep custom renderers optional while supplying Soily in every normal run mode. */
export function MascotSlot({ render, status, animated = true }: MascotContext & {
    render?: MascotRenderer;
    animated?: boolean;
}) {
    return <div className="mascot-slot" data-state={status}>{render ? render({ status }) : <Mascot animated={animated} status={status} />}</div>;
}
