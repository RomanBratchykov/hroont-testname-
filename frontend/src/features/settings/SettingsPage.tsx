import { useEffect, useRef } from 'react';
import { Icon } from '../../components/Icon';
import { useAppearance } from './appearanceContext';

export function SettingsPage({ onBack }: { onBack: () => void }) {
  const { theme, setTheme } = useAppearance();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);

  return <section className="workspace-page" aria-labelledby="settings-title">
    <button className="quiet-button page-back" onClick={onBack}>← Back</button>
    <header className="page-heading"><p className="page-eyebrow">Your workspace</p><h1 ref={heading} tabIndex={-1} id="settings-title">Settings</h1><p>Make this space feel right for you.</p></header>
    <div className="settings-section">
      <fieldset className="theme-options"><legend>Appearance</legend><p>Choose the color theme for your workspace.</p>
        <div className="theme-grid">{(['light', 'dark'] as const).map(option => <label className={`theme-option ${theme === option ? 'selected' : ''}`} key={option}>
          <span className={`theme-swatch theme-swatch-${option}`} aria-hidden="true"><span /><span /><span /></span>
          <span className="theme-option-label"><Icon name={option === 'light' ? 'sun' : 'moon'} />{option === 'light' ? 'Light' : 'Dark'}<input type="radio" name="theme" value={option} checked={theme === option} onChange={() => setTheme(option)} /></span>
        </label>)}</div>
      </fieldset>
      <p className="settings-saved" role="status">Your appearance preference is saved on this device when browser storage is available.</p>
    </div>
  </section>;
}
