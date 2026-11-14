import { test } from 'node:test';
import assert from 'node:assert/strict';
import { chatReducer, initialState, parseSavedState } from './state.ts';
test('sending creates a conversation, preserves other chats, and clears its draft', () => {
    const first = chatReducer(initialState, { type: 'send', text: '  Hello world  ', id: 'one', messageId: 'm1', now: 1 });
    assert.equal(first.conversations[0].title, 'Hello world');
    assert.equal(first.conversations[0].messages[0].content, 'Hello world');
    const next = chatReducer(chatReducer(first, { type: 'new' }), { type: 'send', text: 'Second', id: 'two', messageId: 'm2', now: 2 });
    assert.equal(next.conversations.length, 2);
    assert.equal(next.activeId, 'two');
    assert.equal(next.drafts.new, '');
});
test('empty messages do not create conversations', () => {
    assert.equal(chatReducer(initialState, { type: 'send', text: '  ', id: 'one', messageId: 'm1', now: 1 }), initialState);
});
test('deleting the active chat resets selection and leaves other chats intact', () => {
    const state = chatReducer(initialState, { type: 'send', text: 'Hello', id: 'one', messageId: 'm1', now: 1 });
    const deleted = chatReducer(state, { type: 'delete', id: 'one' });
    assert.equal(deleted.activeId, null);
    assert.equal(deleted.conversations.length, 0);
});
test('invalid persisted data safely falls back to an empty workspace', () => {
    for (const raw of ['bad json', '{"conversations":[{}]}', '{"conversations":[],"drafts":null}', 'null']) {
        assert.deepEqual(parseSavedState(raw), initialState);
    }
});
test('drafts survive reload and remain independent between chats', () => {
    let state = chatReducer(initialState, { type: 'draft', text: 'Unsent idea' });
    state = chatReducer(state, { type: 'send', text: 'Hello', id: 'one', messageId: 'm1', now: 1 });
    state = chatReducer(state, { type: 'draft', text: 'Follow up' });
    state = chatReducer(state, { type: 'new' });
    state = chatReducer(state, { type: 'draft', text: 'A different idea' });
    const restored = parseSavedState(JSON.stringify(state));
    assert.equal(restored.drafts.one, 'Follow up');
    assert.equal(restored.drafts.new, 'A different idea');
});

test('follow-up messages stay in the selected chat and preserve its renamed title', () => {
    let state = chatReducer(initialState, { type: 'send', text: 'First topic', id: 'one', messageId: 'm1', now: 1 });
    state = chatReducer(state, { type: 'rename', id: 'one', title: 'My project' });
    state = chatReducer(state, { type: 'new' });
    state = chatReducer(state, { type: 'send', text: 'Second topic', id: 'two', messageId: 'm2', now: 2 });
    state = chatReducer(state, { type: 'select', id: 'one' });
    state = chatReducer(state, { type: 'send', text: 'A follow up', id: 'unused', messageId: 'm3', now: 3 });
    assert.equal(state.conversations.length, 2);
    assert.equal(state.conversations[0].id, 'one');
    assert.equal(state.conversations[0].title, 'My project');
    assert.deepEqual(state.conversations[0].messages.map(m => m.content), ['First topic', 'A follow up']);
    assert.equal(state.conversations[1].messages.length, 1);
});

test('server history and replies stay in the originating chat', () => {
    let state = chatReducer(initialState, { type: 'send', text: 'First', id: 'one', messageId: 'm1', now: 1 });
    state = chatReducer(state, { type: 'new' });
    state = chatReducer(state, { type: 'send', text: 'Second', id: 'two', messageId: 'm2', now: 2 });
    state = chatReducer(state, { type: 'answer', conversationId: 'one', messageId: 'a1', text: 'Reply', now: 3 });
    assert.equal(state.activeId, 'two');
    assert.equal(state.conversations.find(c => c.id === 'one')?.messages[1].role, 'assistant');
    assert.equal(state.conversations.find(c => c.id === 'two')?.messages.length, 1);
    assert.deepEqual(parseSavedState(JSON.stringify(state)), state);
});

test('a delayed history snapshot cannot overwrite messages received after it started', () => {
    let state = chatReducer(initialState, { type: 'send', text: 'First', id: 'one', messageId: 'm1', now: 1 });
    const oldSnapshot = state.conversations[0];
    state = chatReducer(state, { type: 'send', text: 'New', id: 'ignored', messageId: 'm2', now: 2 });
    state = chatReducer(state, { type: 'answer', conversationId: 'one', messageId: 'a1', text: 'Reply', now: 3 });
    state = chatReducer(state, { type: 'hydrate', conversation: oldSnapshot });
    assert.deepEqual(state.conversations[0].messages.map(message => message.content), ['First', 'New', 'Reply']);
});

test('an answer already received in history is not duplicated by its stream event', () => {
    let state = chatReducer(initialState, { type: 'send', text: 'Hello', id: 'one', messageId: 'm1', now: 1 });
    const answer = { type: 'answer', conversationId: 'one', messageId: 'm1:answer', text: 'Reply', now: 2 } as const;
    state = chatReducer(state, { type: 'hydrate', conversation: { ...state.conversations[0], messages: [...state.conversations[0].messages,
        { id: 'm1:answer', role: 'assistant', content: 'Reply', createdAt: 2 }] } });
    state = chatReducer(state, answer);
    assert.equal(state.conversations[0].messages.length, 2);
    assert.equal(new Set(state.conversations[0].messages.map(message => message.id)).size, 2);
});
