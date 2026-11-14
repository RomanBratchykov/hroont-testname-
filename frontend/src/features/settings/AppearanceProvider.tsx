import { useEffect, useState } from 'react';
import { AppearanceContext } from './appearanceContext';
import type { ReactNode } from 'react';
import config from '../../config/appearance.json';
import { themes } from './themes';
import type { Theme } from './themes';

function readPreference(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function savePreference(key: string, value: string) {
  try { localStorage.setItem(key, value); } catch { /* Preferences still work for this session. */ }
}
export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [theme, updateTheme] = useState<Theme>(() => {
    const saved = readPreference('hroont.theme');
    return saved === 'light' || saved === 'dark' ? saved : window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  const [model, updateModel] = useState(() => {
    const saved = readPreference('hroont.model');
    return config.models.some(model => model.id === saved) ? saved! : config.models[0].id;
  });
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    for (const [token, color] of Object.entries(themes[theme])) root.style.setProperty(`--${token}`, color);
    for (const [role, font] of Object.entries(config.fonts)) root.style.setProperty(`--font-${role}`, font);
    root.style.setProperty('--serif', config.fonts.heading);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themes[theme].bg);
  }, [theme]);
  const setTheme = (next: Theme) => { updateTheme(next); savePreference('hroont.theme', next); };
  const setModel = (next: string) => {
    if (!config.models.some(model => model.id === next)) return;
    updateModel(next); savePreference('hroont.model', next);
  };
  return <AppearanceContext.Provider value={{ theme, setTheme, model, setModel }}>{children}</AppearanceContext.Provider>;
}
