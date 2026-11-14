import { useCallback, useState } from 'react';
import { ChatPage } from './features/chat/ChatPage';
import { AppearanceProvider } from './features/settings/AppearanceProvider';
import { SettingsPage } from './features/settings/SettingsPage';
import { useWorkspacePage } from './features/navigation/useWorkspacePage';
import { WelcomeScreen } from './features/onboarding/WelcomeScreen';
import { AuthScreen } from './features/onboarding/AuthScreen';
import './App.css';
import './features/onboarding/onboarding.css';
import './features/settings/settings.css';
export default function App() {
  const [screen, setScreen] = useState<'greeting' | 'auth' | 'chat' | 'settings'>('greeting');
  const { page, navigate } = useWorkspacePage();
  const showAuth = useCallback(() => setScreen('auth'), []);
  return <AppearanceProvider>
    {screen === 'greeting' && <WelcomeScreen onContinue={showAuth} />}
    {screen === 'auth' && <AuthScreen onContinue={() => setScreen('chat')} openSettings={() => setScreen('settings')} />}
    {screen === 'chat' && <ChatPage page={page} navigate={navigate} openSettings={() => navigate('settings')} onLeave={() => setScreen('auth')} />}
    {screen === 'settings' && <main className="standalone-settings"><SettingsPage onBack={() => setScreen('auth')} /></main>}
  </AppearanceProvider>;
}
