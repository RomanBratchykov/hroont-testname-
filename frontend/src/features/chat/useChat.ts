import { useCallback, useEffect, useRef, useState } from 'react';
import { chatReducer, initialState, parseSavedState, STORAGE_KEY } from './state';
import type { ChatAction, Conversation, Message } from './state';
import { command, encodeFiles, readEvents } from './api';
import type { ChatEvent } from './api';
import { useAppearance } from '../settings/appearanceContext';

const connected = import.meta.env.VITE_CHAT_BACKEND === 'on';

function fromServer(value: unknown): Conversation {
    if (!value || typeof value !== 'object' || !('id' in value) || typeof value.id !== 'string' ||
        !('title' in value) || typeof value.title !== 'string' || !('updated_at' in value) || typeof value.updated_at !== 'number') {
        throw new Error('Invalid conversation from server.');
    }
    const messages = 'messages' in value && Array.isArray(value.messages) ? value.messages.map((message: unknown): Message => {
        if (!message || typeof message !== 'object' || !('id' in message) || typeof message.id !== 'string' ||
            !('role' in message) || (message.role !== 'user' && message.role !== 'assistant') ||
            !('content' in message) || typeof message.content !== 'string' ||
            !('created_at' in message) || typeof message.created_at !== 'number') throw new Error('Invalid message from server.');
        return { id: message.id, role: message.role, content: message.content, createdAt: message.created_at * 1000 };
    }) : [];
    return { id: value.id, title: value.title, updatedAt: value.updated_at * 1000, messages };
}

export function useChat() {
    const { model } = useAppearance();
    const [storageError, setStorageError] = useState(false);
    const [error, setError] = useState('');
    const [busy, setBusy] = useState(false);
    const [revealingMessageId, setRevealingMessageId] = useState<string | null>(null);
    const [ready, setReady] = useState(!connected);
    const [status, setStatus] = useState<ChatEvent | null>(null);
    const [evidence, setEvidence] = useState<unknown[]>([]);
    const [state, setState] = useState(() => {
        if (connected) return initialState;
        try { return parseSavedState(localStorage.getItem(STORAGE_KEY)); }
        catch { return initialState; }
    });
    const latest = useRef(state);
    const controller = useRef<AbortController | null>(null);
    const historyController = useRef<AbortController | null>(null);
    const apply = useCallback((action: ChatAction) => {
        const next = chatReducer(latest.current, action);
        latest.current = next;
        setState(next);
        if (!connected) {
            try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); setStorageError(false); }
            catch { setStorageError(true); }
        }
    }, []);
    const showError = useCallback((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Request failed.'), []);
    useEffect(() => {
        if (!connected) return;
        const abort = new AbortController();
        void command({ action: 'list' }, abort.signal).then(data => {
            if (!data || typeof data !== 'object' || !('conversations' in data) || !Array.isArray(data.conversations)) throw new Error('Invalid server history.');
            apply({ type: 'replace', state: { conversations: data.conversations.map(fromServer), activeId: null, drafts: {} } });
            setReady(true);
        }).catch(reason => { if (!abort.signal.aborted) showError(reason); });
        return () => abort.abort();
    }, [apply, showError]);
    useEffect(() => {
        const abort = () => { controller.current?.abort(); historyController.current?.abort(); };
        window.addEventListener('pagehide', abort);
        return () => { window.removeEventListener('pagehide', abort); abort(); };
    }, []);

    const dispatch = (action: ChatAction) => {
        if (['new', 'select', 'delete'].includes(action.type)) setRevealingMessageId(null);
        if (!connected || !['select', 'delete', 'rename', 'new'].includes(action.type)) { apply(action); return; }
        if (action.type !== 'rename') { controller.current?.abort(); historyController.current?.abort(); setEvidence([]); }
        if (action.type === 'new') { apply(action); setStatus(null); return; }
        if (action.type === 'select') {
            apply(action); setStatus(null);
            const abort = new AbortController();
            historyController.current = abort;
            void command({ action: 'read', conversation_id: action.id }, abort.signal).then(data => {
                if (!abort.signal.aborted) apply({ type: 'hydrate', conversation: fromServer(data) });
            }).catch(reason => { if (!abort.signal.aborted) showError(reason); });
        } else if (action.type === 'delete' || action.type === 'rename') {
            void command({ action: action.type, conversation_id: action.id, ...(action.type === 'rename' ? { title: action.title } : {}) }).then(() => apply(action)).catch(showError);
        }
    };
    const stop = () => { controller.current?.abort(); };
    const send = async (text: string, files: File[] = []) => {
        if (!connected) { apply({ type: 'send', text, id: crypto.randomUUID(), messageId: crypto.randomUUID(), now: Date.now() }); return; }
        if (controller.current || !ready) return;
        const abort = new AbortController();
        controller.current = abort;
        const chat = latest.current.activeId ?? crypto.randomUUID();
        const request = crypto.randomUUID();
        setBusy(true); setError(''); setEvidence([]);
        setStatus({ type: 'status', stage: 'preparing', message: 'Reading input…' });
        try {
            const encoded = await encodeFiles(files);
            if (abort.signal.aborted) return;
            const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'send', conversation_id: chat, request_id: request, message: text,
                    mode: model === 'reasoning' ? 'thinking' : model === 'fast' ? 'fast' : 'auto', files: encoded }), signal: abort.signal });
            if (abort.signal.aborted) return;
            if (response.ok) apply({ type: 'send', text: text || files.map(file => file.name).join(', '), id: chat, messageId: request, now: Date.now() });
            for await (const event of readEvents(response)) {
                if (abort.signal.aborted) break;
                if (event.type === 'status') setStatus(event);
                if (event.type === 'error') { setStatus(null); setError(event.message ?? 'Processing failed.'); }
                if (event.type === 'answer') {
                    setRevealingMessageId(`${request}:answer`);
                    apply({ type: 'answer', conversationId: chat, messageId: `${request}:answer`, text: event.content!, now: Date.now() });
                    setEvidence(event.evidence ?? []); setStatus(null);
                }
            }
        } catch (reason) {
            if (abort.signal.aborted) setStatus({ type: 'status', stage: 'cancelled', message: 'Stopped. Send a new message to retry.' });
            else { showError(reason); setStatus(null); }
        } finally { controller.current = null; setBusy(false); }
    };
    const clear = async () => {
        controller.current?.abort(); historyController.current?.abort();
        try {
            if (connected) await command({ action: 'clear' });
            apply({ type: 'replace', state: initialState }); setStatus(null); setEvidence([]);
        } catch (reason) { showError(reason); }
    };
    const conversation = state.conversations.find(c => c.id === state.activeId);
    return { state, dispatch, revealingMessageId, conversation, storageError, connected, busy, ready, error, status, evidence, stop, clear,
        draft: state.drafts[state.activeId ?? 'new'] ?? '', send };
}
