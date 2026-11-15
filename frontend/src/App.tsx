import { useCallback, useState } from 'react';
import { WelcomeScreen } from './features/onboarding/WelcomeScreen';
import { ChatPage } from './features/chat/ChatPage';
import { AppearanceProvider } from './features/settings/AppearanceProvider';
import { useWorkspacePage } from './features/navigation/useWorkspacePage';
import './App.css';
import './features/onboarding/onboarding.css';
import './features/settings/settings.css';
export default function App() {
  const [greeting, setGreeting] = useState(true);
  const enterWorkspace = useCallback(() => setGreeting(false), []);
  const { page, navigate } = useWorkspacePage();
  return <AppearanceProvider>
    {greeting ? <WelcomeScreen onContinue={enterWorkspace}/> : <ChatPage page={page} navigate={navigate} openSettings={() => navigate('settings')} />}
  </AppearanceProvider>;
}
