import demo from '../../../config/showcase';
import { useState } from 'react';
import { Logo } from '../../../components/Logo';
import { Icon } from '../../../components/Icon';
import type { ChatAction, ChatState } from '../state';
import type { WorkspacePage } from '../../navigation/useWorkspacePage';
export function Sidebar({ state, dispatch, close, openSettings, page, navigate }: {
    state: ChatState;
    page: WorkspacePage;
    navigate: (page: WorkspacePage) => void;
    dispatch: (action: ChatAction) => void;
    close: () => void;
    openSettings: () => void;
}) {
    const [query, setQuery] = useState('');
    const choose = (action: ChatAction) => { dispatch(action); navigate('chat'); if (window.innerWidth <= 760)
        close(); };
    const chats = state.conversations.filter(c => c.title.toLowerCase().includes(query.toLowerCase()));
    return <aside className="sidebar" aria-label="Chat navigation">
    <div className="sidebar-brand"><a href="#" onClick={e => { e.preventDefault(); choose({ type: 'new' }); }}><Logo /></a><button className="icon-button" onClick={close} aria-label="Close sidebar"><Icon name="panel"/></button></div>
    <button className={`personal-state-button ${page === 'personal-state' ? 'active' : ''}`} aria-current={page === 'personal-state' ? 'page' : undefined} onClick={() => { navigate('personal-state'); if (window.innerWidth <= 760) close(); }}><Icon name="user" size={17} />Personal state</button>
    <button className={`personal-state-button ${page === 'dashboard' ? 'active' : ''}`} aria-current={page === 'dashboard' ? 'page' : undefined} onClick={() => { navigate('dashboard'); if (window.innerWidth <= 760) close(); }}><Icon name="panel" size={17}/>Field dashboard</button>
    <button className="new-chat" onClick={() => choose({ type: 'new' })}><span className="new-plus"><Icon name="plus" size={16}/></span>New chat<span className="key-hint">↗</span></button>
    <div className="search-field"><Icon name="search" size={17}/><input aria-label="Search conversations" placeholder="Search your chats" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button className="icon-button" onClick={() => setQuery('')} aria-label="Clear search"><Icon name="close" size={13}/></button>}</div>
    <div className="history-heading">Your conversations<span>{state.conversations.length || ''}</span></div>
    <nav className="chat-history" aria-label="Conversations">{chats.length ? chats.map(c => <div className={`history-row ${page === 'chat' && state.activeId === c.id ? 'active' : ''}`} key={c.id}><button onClick={() => choose({ type: 'select', id: c.id })} className="history-item" aria-current={page === 'chat' && state.activeId === c.id ? 'page' : undefined}><Icon name="chat" size={15}/><span>{c.title}</span></button><button className="delete-chat icon-button" aria-label={`Delete ${c.title}`} onClick={() => dispatch({ type: 'delete', id: c.id })}><Icon name="trash" size={14}/></button></div>) : <div className="history-empty"><Icon name={query ? 'search' : 'chat'} size={23}/><p>{query ? 'No conversations found' : 'A fresh page, a new idea.'}</p><span>{query ? 'Try a different search.' : 'Your chats will find a home here.'}</span></div>}</nav>
    <details className="account-menu" onKeyDown={event => { if (event.key === 'Escape') { event.currentTarget.open = false; event.currentTarget.querySelector('summary')?.focus(); } }} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) event.currentTarget.open = false; }}>
      <summary className="account-trigger" aria-label="Account"><span className="account-name">{demo.accountName}<span>{demo.accountType}</span></span><Icon name="chevron" size={16} /></summary>
      <div className="account-options"><button className="quiet-button" aria-current={page === 'settings' ? 'page' : undefined} onClick={event => { event.currentTarget.closest('details')?.removeAttribute('open'); openSettings(); if (window.innerWidth <= 760) close(); }}>Settings</button></div>
    </details>
  </aside>;
}
