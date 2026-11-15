import { useState } from 'react';
import animation from '../../../assets/Hi_soil.gif';
import question from '../../../assets/question.gif';
import idea from '../../../assets/idea.gif';
import still from '../assets/mascot-still.png';

export type MascotStatus = 'idle' | 'composing' | 'conversation' | 'thinking' | 'question' | 'idea';

/** Supplied GIF states, with a static fallback and reduced-motion support. */
export function Mascot({ animated = true, status = 'idle', onReady }: {
  animated?: boolean;
  status?: MascotStatus;
  onReady?: () => void;
}) {
  const [failedSource, setFailedSource] = useState<string | null>(null);
  const requestedSource = !animated ? still : status === 'question' || status === 'thinking' ? question : status === 'idea' ? idea : animation;
  const source = failedSource === requestedSource ? still : requestedSource;
  return <picture className="soily-mascot" aria-hidden="true">
    <source media="(prefers-reduced-motion: reduce)" srcSet={still} />
    <img key={source} src={source} onLoad={onReady} onError={() => { setFailedSource(source); onReady?.(); }} alt="" width={500} height={650} draggable={false} />
  </picture>;
}
