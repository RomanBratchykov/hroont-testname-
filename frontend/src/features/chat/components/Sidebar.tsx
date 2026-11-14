import { useRef, useState } from 'react';
import { Icon } from '../../../components/Icon';
import type { ChatAction, ChatState } from '../state';
export function Sidebar({ state, dispatch, close, dark, toggleTheme }: {
    state: ChatState;
    dispatch: (action: ChatAction) => void;
    close: () => void;
    dark: boolean;
    toggleTheme: () => void;
}) {
    const [query, setQuery] = useState('');
    const search = useRef<HTMLInputElement>(null);
    const choose = (action: ChatAction) => { dispatch(action); if (window.innerWidth <= 760)
        close(); };
    const chats = state.conversations.filter(c => c.title.toLowerCase().includes(query.toLowerCase()));
    return <aside className="sidebar" aria-label="Chat navigation">
    <div className="sidebar-brand"><a href="#" onClick={e => { e.preventDefault(); choose({ type: 'new' }); }}>hroont<span>✳</span></a><button className="icon-button" onClick={close} aria-label="Close sidebar"><Icon name="panel"/></button></div>
    <button className="new-chat" onClick={() => choose({ type: 'new' })}><span className="new-plus"><Icon name="plus" size={16}/></span>New chat<span className="key-hint">↗</span></button>
    <div className="search-field"><Icon name="search" size={17}/><input ref={search} aria-label="Search conversations" placeholder="Search your chats" value={query} onChange={e => setQuery(e.target.value)}/>{query && <button className="icon-button" onClick={() => setQuery('')} aria-label="Clear search"><Icon name="close" size={13}/></button>}</div>
    <div className="history-heading">Your conversations<span>{state.conversations.length || ''}</span></div>
    <nav className="chat-history" aria-label="Conversations">{chats.length ? chats.map(c => <div className={`history-row ${state.activeId === c.id ? 'active' : ''}`} key={c.id}><button onClick={() => choose({ type: 'select', id: c.id })} className="history-item" aria-current={state.activeId === c.id ? 'page' : undefined}><Icon name="chat" size={15}/><span>{c.title}</span></button><button className="delete-chat icon-button" aria-label={`Delete ${c.title}`} onClick={() => dispatch({ type: 'delete', id: c.id })}><Icon name="trash" size={14}/></button></div>) : <div className="history-empty"><Icon name={query ? 'search' : 'chat'} size={23}/><p>{query ? 'No conversations found' : 'A fresh page, a new idea.'}</p><span>{query ? 'Try a different search.' : 'Your chats will find a home here.'}</span></div>}</nav>
    <div className="sidebar-note"><span className="small-star">✳</span><p>A space for your next big idea.<span>Make yourself at home.</span></p></div>
    <div className="profile"><span className="avatar">Y</span><div>You<span>Personal workspace</span></div><button className="icon-button" onClick={toggleTheme} aria-label={`Switch to ${dark ? 'light' : 'dark'} theme`}><Icon name={dark ? 'sun' : 'moon'}/></button></div>
  </aside>;
}
