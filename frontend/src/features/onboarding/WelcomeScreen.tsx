import { useEffect } from 'react';
import config from '../../config/appearance.json';
import { Logo } from '../../components/Logo';
import { Mascot } from '../../components/Mascot';
export function WelcomeScreen({ onContinue }: { onContinue: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onContinue, config.greeting.durationMs);
    return () => window.clearTimeout(timer);
  }, [onContinue]);
  return <main className="greeting-screen"><div className="entry-logo"><Logo /></div>
    <div className="greeting-center"><div className="greeting-mascot"><Mascot /></div><button className="quiet-button" onClick={onContinue}>Continue</button></div>
  </main>;
}
