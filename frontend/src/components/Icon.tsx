import type { CSSProperties } from 'react';
const paths = {
  paperclip: 'm21 11-8.5 8.5a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8L15 6',
  user: 'M20 21v-2a6 6 0 0 0-6-6h-4a6 6 0 0 0-6 6v2M16 5a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    panel: 'M9 3v18M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z',
    plus: 'M12 5v14M5 12h14', search: 'm21 21-4.3-4.3M19 10.5a8.5 8.5 0 1 1-17 0 8.5 8.5 0 0 1 17 0',
    chat: 'M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z',
    arrow: 'M12 19V5m-6 6 6-6 6 6', chevron: 'm8 10 4 4 4-4', close: 'm6 6 12 12M6 18 18 6',
    pen: 'm16 3 5 5M4 20l5-1L21 7a2 2 0 0 0-5-5L4 14l-1 7Z',
    bulb: 'M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z',
    code: 'm8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18',
    compass: 'm16 8-3 5-5 3 3-5 5-3Zm6 4a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
    copy: 'M9 9h12v12H9V9ZM5 15H3V3h12v2',
    trash: 'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7',
    check: 'm5 12 4 4L19 6', moon: 'M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z', sun: 'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    leaf: 'M20 3C8 2 2 8 5 15s16 7 15-12ZM4 21 15 10',
} as const;
export type IconName = keyof typeof paths;
export function Icon({ name, size = 18, style }: {
    name: IconName;
    size?: number;
    style?: CSSProperties;
}) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}><path d={paths[name]}/></svg>;
}
