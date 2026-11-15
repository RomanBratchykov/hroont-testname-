import { createContext, useContext } from 'react';
import type { Theme } from './themes';
export interface Appearance {
  avatar: string;
  setAvatar: (avatar: string) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  showTranslationStatus: boolean;
  setShowTranslationStatus: (show: boolean) => void;
  model: string;
  setModel: (model: string) => void;
}
export const AppearanceContext = createContext<Appearance | null>(null);
export function useAppearance() {
  const context = useContext(AppearanceContext);
  if (!context) throw new Error('useAppearance must be used inside AppearanceProvider');
  return context;
}
