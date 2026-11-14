import { useCallback, useRef, useState } from 'react';
import { chatReducer, initialState, parseSavedState, STORAGE_KEY } from './state';
import type { ChatAction } from './state';

export function useChat() {
    const [storageError, setStorageError] = useState(false);
    const [state, setState] = useState(() => {
        try {
            return parseSavedState(localStorage.getItem(STORAGE_KEY));
        } catch {
            return initialState;
        }
    });
    // Keep sequential actions in the same event working against the latest state.
    const latest = useRef(state);
    const dispatch = useCallback((action: ChatAction) => {
        const next = chatReducer(latest.current, action);
        latest.current = next;
        setState(next);
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
            setStorageError(false);
        } catch {
            setStorageError(true);
        }
    }, []);
    const conversation = state.conversations.find(c => c.id === state.activeId);
    return {
        state, dispatch, conversation, storageError,
        draft: state.drafts[state.activeId ?? 'new'] ?? '',
        send: (text: string) => dispatch({ type: 'send', text, id: crypto.randomUUID(), messageId: crypto.randomUUID(), now: Date.now() }),
    };
}
