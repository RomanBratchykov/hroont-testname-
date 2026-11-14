import { useEffect, useRef, useState } from 'react';
import { Icon } from '../../components/Icon';
import { Composer } from './components/Composer';
import { Sidebar } from './components/Sidebar';
import { MascotSlot } from './components/MascotSlot';
import type { MascotRenderer } from './components/MascotSlot';
import { useChat } from './useChat';
export function ChatPage({ mascot, openSettings, onLeave }: {
    mascot?: MascotRenderer;
    openSettings: () => void;
    onLeave: () => void;
}) {
    const { state, dispatch, conversation, storageError, draft, send } = useChat();
    const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 760);
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [copied, setCopied] = useState<string | null>(null);
    const end = useRef<HTMLDivElement>(null);
    useEffect(() => { end.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'end' }); }, [conversation?.messages.length, state.activeId]);
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') {
            setSidebarOpen(false);
            setRenamingId(null);
        } };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    return <div className={`app-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
    {sidebarOpen && <><button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/><Sidebar state={state} dispatch={dispatch} close={() => setSidebarOpen(false)} openSettings={openSettings} onLeave={onLeave}/></>}
    <main className="main-panel">
      <header className="topbar"><div className="topbar-left">{!sidebarOpen && <button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="panel"/></button>}<span className="workspace-name">Personal workspace</span><span className="header-slash">/</span><span className="page-name">{conversation ? 'Chat' : 'New chat'}</span></div><button className="quiet-button" onClick={openSettings}>Settings</button></header>
      {conversation ? <>
        <div className="conversation-heading">{renamingId === conversation.id ? <form key={conversation.id} onSubmit={e => { e.preventDefault(); const title = new FormData(e.currentTarget).get('title'); if (typeof title === 'string')
            dispatch({ type: 'rename', id: conversation.id, title }); setRenamingId(null); }}><input name="title" aria-label="Conversation title" defaultValue={conversation.title} autoFocus maxLength={100}/><button className="icon-button" aria-label="Save title"><Icon name="check"/></button></form> : <><h1>{conversation.title}</h1><button className="icon-button" aria-label="Rename conversation" onClick={() => setRenamingId(conversation.id)}><Icon name="pen" size={16}/></button></>}</div>
        <div className="messages" role="log" aria-label="Conversation messages" aria-live="polite">{conversation.messages.map(message => <article className="message" key={message.id}><div className="message-label"><span className="message-avatar">Y</span>You</div><p>{message.content}</p><button className="copy-message icon-button" aria-label={copied === message.id ? 'Message copied' : 'Copy message'} onClick={async () => { try {
            await navigator.clipboard.writeText(message.content);
            setCopied(message.id);
        }
        catch {
            setCopied(null);
        } }}><Icon name={copied === message.id ? 'check' : 'copy'} size={15}/></button></article>)}<div className="offline-notice"><Icon name="leaf" size={20}/><div><strong>Test preview</strong><p>This preview saves messages on this device. Replies will be available when an AI provider is connected.</p></div></div><div ref={end}/></div>
      </> : <div className="welcome-area"><div className="welcome-content"><MascotSlot render={mascot} status={draft ? 'composing' : 'idle'}/><h1>How can I help?</h1><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={send}/></div></div>}
      {storageError && <div className="storage-warning" role="alert">Browser storage is unavailable or full. Your current chats are only saved for this session.</div>}
      <footer className="app-footer"><span>Soily can make mistakes, check important information.</span></footer>
    </main>
  </div>;
}
