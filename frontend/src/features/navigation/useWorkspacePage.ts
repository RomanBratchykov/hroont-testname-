import { useSyncExternalStore } from 'react';
export type WorkspacePage = 'chat' | 'settings' | 'personal-state' | 'dashboard';
function subscribe(callback: () => void) {
  window.addEventListener('hashchange', callback);
  return () => window.removeEventListener('hashchange', callback);
}
function snapshot(): WorkspacePage {
  const page = window.location.hash.slice(2);
  return page === 'settings' || page === 'personal-state' || page === 'dashboard' ? page : 'chat';
}
export function useWorkspacePage() {
  const page = useSyncExternalStore(subscribe, snapshot, () => 'chat' as const);
  const navigate = (next: WorkspacePage) => { window.location.hash = `/${next}`; };
  return { page, navigate };
}
