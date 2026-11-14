import { useEffect, useRef } from 'react';
import { Icon } from '../../components/Icon';
import { useAppearance } from './appearanceContext';
export function SettingsDialog({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { theme, setTheme } = useAppearance();
  useEffect(() => {
    const element = dialog.current;
    if (element && !element.open) element.showModal();
  }, []);
  return <dialog ref={dialog} className="settings-dialog" aria-labelledby="settings-title" onClose={onClose} onClick={event => {
    if (event.target === event.currentTarget) {
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.current?.close();
    }
  }}>
    <div className="settings-heading"><h2 id="settings-title">Settings</h2><button className="icon-button" aria-label="Close settings" onClick={() => dialog.current?.close()}><Icon name="close" /></button></div>
    <fieldset className="theme-options"><legend>Appearance</legend><p>Choose your color theme.</p>{(['light', 'dark'] as const).map(option => <label className={`theme-option ${theme === option ? 'selected' : ''}`} key={option}>
      <input type="radio" name="theme" value={option} checked={theme === option} onChange={() => setTheme(option)} />
      <Icon name={option === 'light' ? 'sun' : 'moon'} />{option === 'light' ? 'Light' : 'Dark'}
    </label>)}</fieldset>
    <button className="primary-button settings-done" onClick={() => dialog.current?.close()}>Done</button>
  </dialog>;
}
