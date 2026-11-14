export type Theme = 'light' | 'dark';

/** Product palette from AGENTS/APP.md. Keep these source colors unchanged. */
export const palettes = {
  dark: {
    background: '#141922', surface: '#1a2130', button: '#101828',
    buttonSpecial: '#1b199c', buttonSpecialHover: '#151473', buttonSpecialText: '#ffffff',
    selected: '#324461', outline: '#2a3347', avatar: '#3b82f6', hover: '#1f2a3c',
    primaryText: '#d4dbe8', secondaryText: '#7e8fa8', highlight: '#1f2a3c',
    border: '#1f2a3c', transparent: '#00000000',
  },
  light: {
    background: '#ffffff', surface: '#f9fafb', button: '#e2e8f0',
    buttonSpecial: '#155dfc', buttonSpecialHover: '#0c43f7', buttonSpecialText: '#ffffff',
    selected: '#dbdbdb', outline: '#e5e7eb', avatar: '#2b7fff', hover: '#1f2937',
    primaryText: '#101828', secondaryText: '#6a7282', highlight: '#f3f4f6',
    border: '#e5e7eb', transparent: '#00000000',
  },
} satisfies Record<Theme, Record<string, string>>;

function tokens(theme: Theme): Record<string, string> {
  const palette = palettes[theme];
  return {
    ...palette,
    bg: palette.background,
    sidebar: palette.surface,
    text: palette.primaryText,
    muted: palette.secondaryText,
    accent: palette.buttonSpecial,
    'accent-soft': palette.highlight,
    'hover-text': theme === 'light' ? palette.buttonSpecialText : palette.primaryText,
  };
}
export const themes: Record<Theme, Record<string, string>> = {
  light: tokens('light'),
  dark: tokens('dark'),
};
