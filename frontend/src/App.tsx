import { useCallback, useState } from 'react';
import { ChatPage } from './features/chat/ChatPage';
import { AppearanceProvider } from './features/settings/AppearanceProvider';
import { SettingsDialog } from './features/settings/SettingsDialog';
import { WelcomeScreen } from './features/onboarding/WelcomeScreen';
import { AuthScreen } from './features/onboarding/AuthScreen';
import './App.css';
import './features/onboarding/onboarding.css';
import './features/settings/settings.css';
export default function App() {
  const [screen, setScreen] = useState<'greeting' | 'auth' | 'chat'>('greeting');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const showAuth = useCallback(() => setScreen('auth'), []);
  return <AppearanceProvider>
    {screen === 'greeting' && <WelcomeScreen onContinue={showAuth} />}
    {screen === 'auth' && <AuthScreen onContinue={() => setScreen('chat')} openSettings={() => setSettingsOpen(true)} />}
    {screen === 'chat' && <ChatPage openSettings={() => setSettingsOpen(true)} onLeave={() => setScreen('auth')} />}
    {settingsOpen && <SettingsDialog onClose={() => setSettingsOpen(false)} />}
  </AppearanceProvider>;
}
