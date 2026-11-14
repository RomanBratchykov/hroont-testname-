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
- `src/features/settings/SettingsPage.tsx`: dedicated settings page with persistent appearance controls.
- `src/features/personal-state/PersonalStatePage.tsx`: empty interview-data page and a read-only `PersonalStateData` presentation contract for a future server adapter. No data fetching is connected and no personal information is invented.
- `src/features/navigation/useWorkspacePage.ts`: browser hash navigation for `#/chat`, `#/settings`, and `#/personal-state`, with browser back/forward support. The workspace stays mounted across these views, preserving chat state and drafts.
- `src/features/onboarding/`: greeting GIF and frontend login/register screens. The greeting advances after the configured delay or Continue; reduced-motion users see the PNG. The app starts at the greeting on reload.
- `src/index.css`: full-width reset and global defaults; `src/App.css`: responsive chat layout; feature CSS files own onboarding and settings.

## Mascot

`src/components/Mascot.tsx` uses the supplied `../assets/Hi_soil.gif` (repository-root
`assets/Hi_soil.gif`). Vite bundles that original asset for development and production.
`src/assets/mascot-still.png` is its first frame, used for reduced motion and older messages.

The startup greeting plays the supplied animation. Every new chat displays it centered
above the composer; submitting the first message animates the mascot shrinking into the
message's right margin. Every message has a small mascot, with only the newest message
animated. Small screens use a narrower mascot gutter.

`MascotSlot` still accepts a custom renderer; otherwise it renders the shared mascot.
The animation uses measured bounds and the browser's animation API, with an immediate
placement fallback when reduced motion is enabled or animation is unsupported. Existing
translation-status settings remain independent of the artwork.

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

The supplied greeting/mascot asset is `assets/Hi_soil.gif`; its still frame is `src/assets/mascot-still.png`. Startup duration is configured in `src/config/appearance.json`.

## Workspace pages and palette

“Personal state” sits directly above “New chat” in the sidebar. Settings is a full workspace page, not a dialog; it is also available as a standalone page before entering the preview. Each page moves keyboard focus to its heading when opened. Chat and theme state stay in their existing owners.

`themes.ts` preserves every named light/dark palette color from `AGENTS/APP.md`. Semantic aliases (`bg`, `sidebar`, `text`, `muted`, `accent`, `accent-soft`, and `hover-text`) keep existing components decoupled from the source palette naming. Light-theme dark hover surfaces use white text for contrast. Special buttons use the specified normal/hover/text tokens, and avatars use the specified avatar token.
