# Frontend chat

React + TypeScript, built with Vite. This app runs entirely in the browser: no API calls, AI runtime, backend proxy, authentication, or simulated AI replies.

## Boundaries

- `src/features/chat/state.ts`: typed conversation/message model, pure reducer, and validation for persisted state. State changes are explicit actions; UI components do not write to storage.
- `src/features/chat/useChat.ts`: owns the reducer and browser persistence (`hroont.chat.v1`). Handles unavailable/full storage without blocking the UI.
- `src/features/chat/ChatPage.tsx`: composes navigation, empty state, message history, and composer.
- `src/features/chat/components/`: independently replaceable sidebar, composer, and mascot slot.
- `src/components/Icon.tsx`: small shared SVG icon library, with no external asset requests.
- `src/index.css`: theme tokens and global defaults; `src/App.css`: responsive layout and component styles.

## Future mascot

`ChatPage` accepts an optional `mascot` render function. It receives `idle` or `composing` in the welcome area; the context type also reserves `conversation` for future placements. The default is a decorative bloom. Example:

```tsx
<ChatPage mascot={({ status }) => <MyMascot animation={status} />} />
```

The slot owns positioning; the mascot owns animation/assets. Supply accessible text or controls in the mascot renderer if it communicates meaningful information. Decorative artwork should be hidden from assistive technology.

## Future growth

Keep model/transport integration behind a dedicated hook or adapter, rather than importing a provider in presentation components. Add assistant messages, request status, cancellation, errors, and streaming when a provider is actually selected. The existing assistant-ui dependencies at repository root are intentionally not connected during this frontend-only phase.

Local storage is suitable for this preview, not unlimited history or multi-device persistence. For larger client-only histories, replace persistence with IndexedDB and add message pagination/virtualization. Preserve the reducer/component boundaries. Treat a future schema change as a new storage version with a migration.

## Local behavior

- New chats are created when their first nonempty message is sent.
- Enter sends; Shift+Enter adds a line. IME composition does not send.
- Drafts are isolated by conversation, including the unsent new-chat draft.
- Search matches chat titles. Chats can be renamed and deleted.
- Theme preference and conversation state persist on the current browser/device. Clearing browser data removes them.
- No AI messages are generated. The thread explains that replies are not connected.

Run `npm run dev`, `npm run build`, `npm run test`, or `npm run lint` from `frontend/`. Tests use Node's built-in runner (Node 22.18+ recommended), with no additional testing dependencies.
