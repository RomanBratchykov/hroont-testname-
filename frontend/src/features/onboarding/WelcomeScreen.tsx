import { useEffect } from 'react';
import config from '../../config/appearance.json';
import { Logo } from '../../components/Logo';
export function WelcomeScreen({ onContinue }: { onContinue: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onContinue, config.greeting.durationMs);
    return () => window.clearTimeout(timer);
  }, [onContinue]);
  return <main className="greeting-screen"><div className="entry-logo"><Logo /></div>
    <div className="greeting-center"><picture><source media="(prefers-reduced-motion: reduce)" srcSet={config.greeting.still} /><img className="greeting-animation" src={config.greeting.animation} alt="Hello! Welcome." width="320" height="240" /></picture><button className="quiet-button" onClick={onContinue}>Continue</button></div>
  </main>;
}
