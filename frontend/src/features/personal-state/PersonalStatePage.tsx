import { useEffect, useRef } from 'react';
import { SavedUserProfile } from './SavedUserProfile';

export function PersonalStatePage({ onBack }: { onBack: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  return <section className="workspace-page" aria-labelledby="personal-state-title">
    <button className="quiet-button page-back" onClick={onBack}>Back to chat</button>
    <header className="page-heading"><p className="page-eyebrow">Your workspace</p><h1 ref={heading} tabIndex={-1} id="personal-state-title">Personal state</h1><p>Your current farm details. Edit them or clear all information below.</p></header>
    <SavedUserProfile />
  </section>;
}
