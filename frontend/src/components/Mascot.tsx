import { useState } from 'react';
import animation from '../../../assets/Hi_soil.gif';
import still from '../assets/mascot-still.png';

/** Reuse the supplied artwork; a static frame also supports reduced motion. */
export function Mascot({ animated = true, status = 'idle' }: {
  animated?: boolean;
  status?: 'idle' | 'composing' | 'conversation' | 'thinking';
}) {
  const [thinkingUnavailable, setThinkingUnavailable] = useState(false);
  const useThinking = animated && status === 'thinking' && !thinkingUnavailable;
  const source = useThinking ? '/media/thinking.gif' : animated ? animation : still;
  return <picture className="soily-mascot" aria-hidden="true">
    <source media="(prefers-reduced-motion: reduce)" srcSet={still} />
    <img src={source} onError={useThinking ? () => setThinkingUnavailable(true) : undefined} alt="" width={500} height={650} draggable={false} />
  </picture>;
}
