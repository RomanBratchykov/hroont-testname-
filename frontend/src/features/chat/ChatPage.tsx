import { useEffect, useRef, useState } from 'react';
import { Icon } from '../../components/Icon';
import type { IconName } from '../../components/Icon';
import { Composer } from './components/Composer';
import { Sidebar } from './components/Sidebar';
import { MascotSlot } from './components/MascotSlot';
import type { MascotRenderer } from './components/MascotSlot';
import { useChat } from './useChat';
const suggestions: {
    icon: IconName;
    label: string;
    prompt: string;
    detail: string;
}[] = [
    { icon: 'pen', label: 'Write something', detail: 'Find the right words', prompt: 'Help me find the right words for ' },
    { icon: 'bulb', label: 'Explore an idea', detail: 'Follow your curiosity', prompt: 'I have an idea I’d like to explore: ' },
    { icon: 'code', label: 'Build something', detail: 'Turn a thought into a plan', prompt: 'Help me plan how to build ' },
    { icon: 'compass', label: 'Learn something', detail: 'Make room for discovery', prompt: 'I’d like to understand more about ' },
];
export function ChatPage({ mascot }: {
    mascot?: MascotRenderer;
}) {
    const { state, dispatch, conversation, storageError, draft, send } = useChat();
    const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 760);
    const [dark, setDark] = useState(() => { try {
        return localStorage.getItem('hroont.theme') === 'dark';
    }
    catch {
        return false;
    } });
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [copied, setCopied] = useState<string | null>(null);
    const end = useRef<HTMLDivElement>(null);
    useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; try {
        localStorage.setItem('hroont.theme', dark ? 'dark' : 'light');
    }
    catch { /* Theme still works in memory. */ } }, [dark]);
    useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [conversation?.messages.length, state.activeId]);
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') {
            setSidebarOpen(false);
            setRenamingId(null);
        } };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);
    return <div className={`app-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
    {sidebarOpen && <><button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/><Sidebar state={state} dispatch={dispatch} close={() => setSidebarOpen(false)} dark={dark} toggleTheme={() => setDark(!dark)}/></>}
    <main className="main-panel">
      <header className="topbar"><div className="topbar-left">{!sidebarOpen && <button className="icon-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="panel"/></button>}<span className="workspace-name">Personal workspace</span><span className="header-slash">/</span><span className="page-name">{conversation ? 'Chat' : 'New chat'}</span></div><span className="local-badge"><span />Local preview</span></header>
      {conversation ? <>
        <div className="conversation-heading">{renamingId === conversation.id ? <form key={conversation.id} onSubmit={e => { e.preventDefault(); const title = new FormData(e.currentTarget).get('title'); if (typeof title === 'string')
            dispatch({ type: 'rename', id: conversation.id, title }); setRenamingId(null); }}><input name="title" aria-label="Conversation title" defaultValue={conversation.title} autoFocus maxLength={100}/><button className="icon-button" aria-label="Save title"><Icon name="check"/></button></form> : <><h1>{conversation.title}</h1><button className="icon-button" aria-label="Rename conversation" onClick={() => setRenamingId(conversation.id)}><Icon name="pen" size={16}/></button></>}</div>
        <div className="messages" role="log" aria-label="Conversation messages" aria-live="polite">{conversation.messages.map(message => <article className="message" key={message.id}><div className="message-label"><span className="message-avatar">Y</span>You</div><p>{message.content}</p><button className="copy-message icon-button" aria-label={copied === message.id ? 'Message copied' : 'Copy message'} onClick={async () => { try {
            await navigator.clipboard.writeText(message.content);
            setCopied(message.id);
        }
        catch {
            setCopied(null);
        } }}><Icon name={copied === message.id ? 'check' : 'copy'} size={15}/></button></article>)}<div className="offline-notice"><Icon name="leaf" size={20}/><div><strong>Your thoughts have a place here.</strong><p>This preview saves messages on this device. Replies will be available when an AI provider is connected.</p></div></div><div ref={end}/></div>
        <div className="conversation-composer"><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={send}/><p className="composer-caption">Your conversations stay in this browser.</p></div>
      </> : <div className="welcome-area"><div className="welcome-content"><div className="welcome-eyebrow"><span />A LITTLE SPACE FOR POSSIBILITY</div><MascotSlot render={mascot} status={draft ? 'composing' : 'idle'}/><h1>Good things start<br />with a conversation.</h1><p className="welcome-description">A thought, a question, a spark of something.<br className="mobile-break"/> Let’s see where it takes you.</p><Composer value={draft} onChange={text => dispatch({ type: 'draft', text })} onSend={send}/><div className="suggestion-grid">{suggestions.map(s => <button className="suggestion" key={s.label} onClick={() => { dispatch({ type: 'draft', text: s.prompt }); document.querySelector<HTMLTextAreaElement>('textarea')?.focus(); }}><Icon name={s.icon} size={19}/><strong>{s.label}</strong><span>{s.detail}</span></button>)}</div><p className="welcome-footnote"><span />Your space. Your pace. Your next idea.</p></div></div>}
      {storageError && <div className="storage-warning" role="alert">Browser storage is unavailable or full. Your current chats are only saved for this session.</div>}
      <footer className="app-footer"><span>Made for a curious mind.</span><span>Frontend preview <span className="footer-dot">·</span> No AI connected</span></footer>
    </main>
  </div>;
}
