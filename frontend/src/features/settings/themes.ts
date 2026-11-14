export type Theme = 'light' | 'dark';
export const themes: Record<Theme, Record<string, string>> = {
  light: {
    bg: '#f8f7f3', sidebar: '#eeede7', surface: '#fffefa', text: '#35352f',
    muted: '#74746b', border: '#deddd4', hover: '#e6e5dd', accent: '#a6553a',
    'accent-soft': '#f2e6de',
  },
  dark: {
    bg: '#262723', sidebar: '#20211e', surface: '#30312c', text: '#e9e7dd',
    muted: '#b1b1a5', border: '#45463e', hover: '#36372f', accent: '#e39b7e',
    'accent-soft': '#45342b',
  },
};
