export interface Message {
    id: string;
    role: 'user';
    content: string;
    createdAt: number;
}
export interface Conversation {
    id: string;
    title: string;
    messages: Message[];
    updatedAt: number;
}
export interface ChatState {
    conversations: Conversation[];
    activeId: string | null;
    drafts: Record<string, string>;
}
export type ChatAction = {
    type: 'new';
} | {
    type: 'select';
    id: string;
} | {
    type: 'draft';
    text: string;
} | {
    type: 'delete';
    id: string;
} | {
    type: 'rename';
    id: string;
    title: string;
} | {
    type: 'send';
    text: string;
    id: string;
    messageId: string;
    now: number;
};
export const initialState: ChatState = { conversations: [], activeId: null, drafts: {} };
export const STORAGE_KEY = 'hroont.chat.v1';
export function chatReducer(state: ChatState, action: ChatAction): ChatState {
    const key = state.activeId ?? 'new';
    switch (action.type) {
        case 'new': return { ...state, activeId: null };
        case 'select': return state.conversations.some(c => c.id === action.id) ? { ...state, activeId: action.id } : state;
        case 'draft': return { ...state, drafts: { ...state.drafts, [key]: action.text } };
        case 'delete': {
            const drafts = { ...state.drafts };
            delete drafts[action.id];
            return { ...state, drafts, conversations: state.conversations.filter(c => c.id !== action.id), activeId: state.activeId === action.id ? null : state.activeId };
        }
        case 'rename': return { ...state, conversations: state.conversations.map(c => c.id === action.id && action.title.trim() ? { ...c, title: action.title.trim().slice(0, 100) } : c) };
        case 'send': {
            const content = action.text.trim();
            if (!content)
                return state;
            const message: Message = { id: action.messageId, role: 'user', content, createdAt: action.now };
            const existing = state.conversations.find(c => c.id === state.activeId);
            const conversation: Conversation = existing
                ? { ...existing, messages: [...existing.messages, message], updatedAt: action.now }
                : { id: action.id, title: content.slice(0, 60), messages: [message], updatedAt: action.now };
            return { conversations: [conversation, ...state.conversations.filter(c => c.id !== conversation.id)], activeId: conversation.id, drafts: { ...state.drafts, [key]: '' } };
        }
    }
}
export function parseSavedState(raw: string | null): ChatState {
    try {
        if (!raw)
            return initialState;
        const data = JSON.parse(raw) as ChatState;
        if (!data || !Array.isArray(data.conversations) || !data.drafts || typeof data.drafts !== 'object' || Array.isArray(data.drafts))
            return initialState;
        if (!Object.values(data.drafts).every(d => typeof d === 'string'))
            return initialState;
        if (!data.conversations.every(c => typeof c.id === 'string' && typeof c.title === 'string' && typeof c.updatedAt === 'number' && Array.isArray(c.messages) && c.messages.every(m => typeof m.id === 'string' && m.role === 'user' && typeof m.content === 'string' && typeof m.createdAt === 'number')))
            return initialState;
        return { ...data, activeId: data.conversations.some(c => c.id === data.activeId) ? data.activeId : null };
    }
    catch {
        return initialState;
    }
}
