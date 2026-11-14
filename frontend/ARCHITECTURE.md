# Frontend chat

React + TypeScript, built with Vite. This app runs entirely in the browser: no API calls, AI runtime, backend proxy, authentication, or simulated AI replies.

## Boundaries

- `src/features/chat/state.ts`: typed conversation/message model, pure reducer, and validation for persisted state. State changes are explicit actions; UI components do not write to storage.
- `src/features/chat/useChat.ts`: owns the reducer and browser persistence (`hroont.chat.v1`). Handles unavailable/full storage without blocking the UI.
- `src/features/chat/ChatPage.tsx`: composes navigation, empty state, message history, and composer.
- `src/features/chat/components/`: independently replaceable sidebar, composer, and mascot slot.
- `src/components/Icon.tsx`: small shared SVG icon library, with no external asset requests.
- `src/config/appearance.json`: developer-configured font stacks, greeting asset paths and duration, and preview model choices. JSON changes take effect after Vite reload/rebuild. No remote fonts are requested; use an installed font or add a local `@font-face` asset.
- `src/features/settings/themes.ts`: complete light/dark color token sets.
- `src/features/settings/AppearanceProvider.tsx`: applies global appearance and persists theme/model preferences. Components access it through `appearanceContext.ts`.
- `src/features/settings/SettingsDialog.tsx`: native modal with theme controls, keyboard dismissal, and native focus handling.
- `src/features/onboarding/`: greeting GIF and frontend login/register screens. The greeting advances after the configured delay or Continue; reduced-motion users see the PNG. The app starts at the greeting on reload.
- `src/index.css`: full-width reset and global defaults; `src/App.css`: responsive chat layout; feature CSS files own onboarding and settings.

## Future mascot

`ChatPage` accepts an optional `mascot` render function. It receives `idle` or `composing` in the welcome area; the context type also reserves `conversation` for future placements. Without a supplied renderer the slot renders nothing. Branding uses the literal “place logo here” placeholder. Example:

```tsx
<ChatPage
  openSettings={openSettings}
  onLeave={showAuth}
  mascot={({ status }) => <MyMascot animation={status} />}
/>
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

## Preview account and model controls

The greeting leads to login/register. These forms validate input locally and only enter the preview; they never create an account, check identity, send credentials, or store passwords/emails. “Explore without an account” provides direct preview access. “Leave preview” returns to the account screen. Chats belong to the local browser workspace, not an authenticated user.

The composer model selector offers configurable preview modes. Selection persists, but it does not select a real provider or generate responses. Theme controls live in Settings, available from both the account screen and chat. There are no suggestion cards.

The bundled greeting is a simple temporary text GIF. Replace `public/media/greeting.gif` and its static PNG fallback, or change their paths in the JSON, when final greeting artwork is provided.
