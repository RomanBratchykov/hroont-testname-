import { useEffect, useRef, useState } from 'react';
import { Icon } from '../../components/Icon';
import { Composer } from './components/Composer';
import { Sidebar } from './components/Sidebar';
import { MascotSlot } from './components/MascotSlot';
import type { MascotRenderer } from './components/MascotSlot';
import { useChat } from './useChat';
import { useAppearance } from '../settings/appearanceContext';
import { SettingsPage } from '../settings/SettingsPage';
import { PersonalStatePage } from '../personal-state/PersonalStatePage';
import type { WorkspacePage } from '../navigation/useWorkspacePage';
export function ChatPage({ mascot, openSettings, onLeave, page, navigate }: {
    mascot?: MascotRenderer;
    page: WorkspacePage;
    navigate: (page: WorkspacePage) => void;
    openSettings: () => void;
    onLeave: () => void;
}) {
    const { state, dispatch, conversation, storageError, draft, send, connected, busy, ready, error, status, evidence, stop, clear } = useChat();
    const { showTranslationStatus } = useAppearance();
    const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 760);
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [copied, setCopied] = useState<string | null>(null);
    const end = useRef<HTMLDivElement>(null);
    useEffect(() => { if (page !== 'chat') return; end.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'end' }); }, [conversation?.messages.length, state.activeId, page]);
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') {
            setSidebarOpen(false);
            setRenamingId(null);
        } };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    return <div className={`app-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
    {sidebarOpen && <><button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/><Sidebar state={state} dispatch={dispatch} close={() => setSidebarOpen(false)} openSettings={openSettings} onLeave={onLeave} page={page} navigate={navigate}/></>}
    <main className="main-panel">
      <header className="topbar"><div className="topbar-left">{!sidebarOpen && <button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="panel"/></button>}<span className="workspace-name">Personal workspace</span><span className="header-slash">/</span><span className="page-name">{page === 'settings' ? 'Settings' : page === 'personal-state' ? 'Personal state' : conversation ? 'Chat' : 'New chat'}</span></div><button className="quiet-button" onClick={openSettings}>Settings</button></header>
      {connected && <div className="processing-status" role="status"><MascotSlot render={mascot ?? (() => <img src="/media/greeting.gif" alt="Soily" />)} status="conversation"/><span>{status && (status.stage !== "translating" || showTranslationStatus) ? status.message : "Local demo workspace"}</span><button className="quiet-button" onClick={() => { if (window.confirm("Delete all saved chats and associated information?")) void clear(); }}>Clear history</button></div>}
      {error && <div className="storage-warning" role="alert">{error}</div>}
      {page === 'settings' ? <SettingsPage onBack={() => navigate('chat')} /> : page === 'personal-state' ? <PersonalStatePage onBack={() => navigate('chat')} /> : conversation ? <>
        <div className="conversation-heading">{renamingId === conversation.id ? <form key={conversation.id} onSubmit={e => { e.preventDefault(); const title = new FormData(e.currentTarget).get('title'); if (typeof title === 'string')
            dispatch({ type: 'rename', id: conversation.id, title }); setRenamingId(null); }}><input name="title" aria-label="Conversation title" defaultValue={conversation.title} autoFocus maxLength={100}/><button className="icon-button" aria-label="Save title"><Icon name="check"/></button></form> : <><h1>{conversation.title}</h1><button className="icon-button" aria-label="Rename conversation" onClick={() => setRenamingId(conversation.id)}><Icon name="pen" size={16}/></button></>}</div>
        <div className="messages" role="log" aria-label="Conversation messages" aria-live="polite">{conversation.messages.map(message => <article className="message" key={message.id}><div className="message-label"><span className="message-avatar">{message.role === "assistant" ? "S" : "Y"}</span>{message.role === "assistant" ? "Soily" : "You"}</div><p>{message.content}</p><button className="copy-message icon-button" aria-label={copied === message.id ? 'Message copied' : 'Copy message'} onClick={async () => { try {
            await navigator.clipboard.writeText(message.content);
            setCopied(message.id);
        }
        catch {
            setCopied(null);
        } }}><Icon name={copied === message.id ? 'check' : 'copy'} size={15}/></button></article>)}{!connected && <div className="offline-notice"><Icon name="leaf" size={20}/><div><strong>Test preview</strong><p>This preview saves messages on this device. Replies will be available when an AI provider is connected.</p></div></div>}{evidence.length > 0 && <details className="tool-evidence"><summary>Tool findings</summary><pre>{JSON.stringify(evidence, null, 2)}</pre></details>}<div ref={end}/></div>
        <div className="conversation-composer"><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={send} busy={busy} disabled={!ready} connected={connected} onStop={stop} /></div>
      </> : <div className="welcome-area"><div className="welcome-content"><MascotSlot render={mascot} status={draft ? 'composing' : 'idle'}/><h1>How can I help?</h1><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={send} busy={busy} disabled={!ready} connected={connected} onStop={stop}/></div></div>}
      {storageError && <div className="storage-warning" role="alert">Browser storage is unavailable or full. Your current chats are only saved for this session.</div>}
      <footer className="app-footer"><span>Soily can make mistakes, check important information.</span></footer>
    </main>
  </div>;
}
