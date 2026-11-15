import { useEffect, useState } from 'react';
import demo from '../../config/showcase';
import { DemoDashboard } from '../personal-state/DemoDashboard';
import { UserAvatar } from '../../components/UserAvatar';
import { Icon } from '../../components/Icon';
import { ReplyText } from './components/ReplyText';
import { Composer } from './components/Composer';
import { Sidebar } from './components/Sidebar';
import { MascotSlot } from './components/MascotSlot';
import type { MascotRenderer } from './components/MascotSlot';
import { useChat } from './useChat';
import { useReplyScroll } from './useReplyScroll';
import { BoundaryPreview } from '../field-dashboard/BoundaryPreview';
import { useAppearance } from '../settings/appearanceContext';
import { SettingsPage } from '../settings/SettingsPage';
import { PersonalStatePage } from '../personal-state/PersonalStatePage';
import type { WorkspacePage } from '../navigation/useWorkspacePage';
export function ChatPage({ mascot, openSettings, page, navigate }: {
    mascot?: MascotRenderer;
    page: WorkspacePage;
    navigate: (page: WorkspacePage) => void;
    openSettings: () => void;
}) {
    const { state, dispatch, conversation, revealingMessageId, finalizedMessageId, storageError, draft, send, connected, busy, ready, retry, error, reportError, status, evidence, stop, clear } = useChat();
    const { showTranslationStatus } = useAppearance();
    const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 760);
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [showIntroduction, setShowIntroduction] = useState(page === 'chat');
    const navigatePage = (next: WorkspacePage) => { setShowIntroduction(false); navigate(next); };
    const [copied, setCopied] = useState<string | null>(null);
    const { end, followReply, resumeFollowing } = useReplyScroll(page === 'chat');
    const sendMessage = (text: string, files?: File[]) => { setShowIntroduction(false); resumeFollowing(); void send(text, files); };
    const latestText = conversation?.messages.at(-1)?.content;
    useEffect(() => { if (page === 'chat') followReply(); }, [latestText, state.activeId, busy, page, followReply]);
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') {
            setSidebarOpen(false);
            setRenamingId(null);
        } };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    return <div className={`app-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
    {sidebarOpen && <><button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/><Sidebar state={state} dispatch={dispatch} close={() => setSidebarOpen(false)} openSettings={() => { setShowIntroduction(false); openSettings(); }} page={page} navigate={navigatePage}/></>}
    <main className="main-panel">
      <header className="topbar"><div className="topbar-left">{!sidebarOpen && <button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="panel"/></button>}<details className="workspace-menu" onKeyDown={event => { if (event.key === 'Escape') event.currentTarget.open = false; }} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false; }}><summary className="workspace-name">John’s test workspace <Icon name="chevron" size={14}/></summary><div className="workspace-options"><button className="quiet-button" disabled={busy} onClick={event => { event.currentTarget.closest('details')?.removeAttribute('open'); if (window.confirm("Delete all saved chats and their tool findings? Your saved profile will remain.")) void clear(); }}>Clear history</button></div></details><span className="header-slash">/</span><span className="page-name">{page === 'settings' ? 'Settings' : page === 'personal-state' ? 'Personal state' : page === 'dashboard' ? 'Example dashboard' : conversation ? 'Chat' : 'New chat'}</span></div></header>
      {connected && status && (status.stage !== 'translating' || showTranslationStatus) && <div className="processing-status" role="status"><span>{status.message}</span></div>}
      {showIntroduction && page === 'chat' && !conversation && <section className="demo-introduction" aria-label="Welcome from Soily"><div className="message-row message-row-assistant"><div className="message-mascot"><MascotSlot render={mascot} status="idle" animated={true}/></div><article className="message message-assistant"><div className="message-label">Soily</div><ReplyText text={demo.introduction} animate={true} onProgress={followReply}/><div className="demo-actions"><button className="quiet-button" onClick={() => navigatePage('dashboard')}>Explore example dashboard →</button><button className="quiet-button" onClick={() => setShowIntroduction(false)}>Got it</button></div></article></div></section>}
      {page === 'dashboard' ? <DemoDashboard onAsk={question => { dispatch({ type: 'draft', text: question }); navigatePage('chat'); setShowIntroduction(false); }}/> : page === 'settings' ? <SettingsPage onBack={() => navigatePage('chat')} /> : page === 'personal-state' ? <PersonalStatePage onBack={() => navigatePage('chat')} /> : conversation ? <>
        <div className="conversation-heading">{renamingId === conversation.id ? <form key={conversation.id} onSubmit={e => { e.preventDefault(); const title = new FormData(e.currentTarget).get('title'); if (typeof title === 'string')
            dispatch({ type: 'rename', id: conversation.id, title }); setRenamingId(null); }}><input name="title" aria-label="Conversation title" defaultValue={conversation.title} autoFocus maxLength={100}/><button className="icon-button" aria-label="Save title"><Icon name="check"/></button></form> : <><h1>{conversation.title}</h1><button className="icon-button" aria-label="Rename conversation" onClick={() => setRenamingId(conversation.id)}><Icon name="pen" size={16}/></button></>}</div>
        <div className="messages" role="log" aria-label="Conversation messages" aria-live="polite">{conversation.messages.map((message, index) => <div className={`message-row message-row-${message.role}`} key={message.id}><article className={`message message-${message.role}`}><div className="message-label">{message.role === "assistant" ? "Soily" : "You"}</div><BoundaryPreview text={message.content}/><ReplyText text={message.content} animate={false} writing={message.role === "assistant" && message.id === revealingMessageId} onProgress={followReply} /><button className="copy-message icon-button" aria-label={copied === message.id ? 'Message copied' : 'Copy message'} onClick={async () => { try {
            await navigator.clipboard.writeText(message.content);
            setCopied(message.id);
        }
        catch {
            setCopied(null);
            reportError("I couldn’t copy that message. Please try selecting and copying the text.");
        } }}><Icon name={copied === message.id ? 'check' : 'copy'} size={15}/></button></article>{message.role === "user" && <div className="message-user-avatar" aria-hidden="true"><UserAvatar/></div>}{message.role === "assistant" && <div className="message-mascot"><MascotSlot render={mascot} status={message.id === revealingMessageId || message.id === finalizedMessageId ? "idea" : "conversation"} animated={index === conversation.messages.length - 1}/></div>}</div>)}{busy && conversation.messages.at(-1)?.role !== "assistant" && <div className="message-row message-row-assistant"><div className="message-mascot"><MascotSlot render={mascot} status="question" /></div><article className="message message-assistant"><div className="message-label">Soily</div><p>Thinking…</p></article></div>}{!connected && <div className="offline-notice"><Icon name="leaf" size={20}/><div><strong>Test preview</strong><p>This preview saves messages on this device. Replies will be available when an AI provider is connected.</p></div></div>}{evidence.length > 0 && <details className="tool-evidence"><summary>Tool findings</summary><pre>{JSON.stringify(evidence, null, 2)}</pre></details>}</div>
        <div className="conversation-composer"><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={sendMessage} busy={busy} disabled={!ready} connected={connected} onStop={stop} /></div>
      </> : <div className="welcome-area"><div className="welcome-content"><h1>How can I help?</h1><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={sendMessage} busy={busy} disabled={!ready} connected={connected} onStop={stop}/></div></div>}
      {(error || storageError) && <div className="soily-notices" aria-live="polite">{[error, storageError ? "I can’t save your chats because browser storage is unavailable or full. Your current chats are only saved for this session." : ''].filter(Boolean).map(text => <div className="message-row message-row-assistant" key={text}><div className="message-mascot"><MascotSlot render={mascot} status="conversation" animated={false}/></div><article className="message message-assistant" role="alert"><div className="message-label">Soily</div><ReplyText text={text} animate={false} onProgress={followReply}/>{!ready && <button className="quiet-button" onClick={retry}>Try again</button>}</article></div>)}</div>}
      <footer className="app-footer"><span>Soily can make mistakes, check important information.</span></footer><div ref={end} className="conversation-end" aria-hidden="true"/>
    </main>
  </div>;
}
