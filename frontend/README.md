# Forum Frontend

React SPA for the Real-Time Discussion Forum.

## Tech Stack

- **React 19** with functional components & hooks
- **Vite 8** — dev server with HMR + proxy to API gateway
- **Tailwind CSS 4.2** — utility-first styling
- **React Router v7** — client-side routing
- **Axios** — HTTP client with auto token refresh
- **WebSocket** — real-time comments, likes & notifications

## Quick Start

```bash
npm install
npm run dev        # http://localhost:5173
```

Requires the backend Docker stack running on port 8000 (see root README).

## Project Structure

```
src/
├── components/     # Reusable components (Navbar, CommentTree, ErrorBoundary)
│   └── ui/         # Design system primitives (Button, Input, Badge, etc.)
├── context/        # AuthContext (JWT state management)
├── hooks/          # useAuth, useWebSocket, useClickOutside
├── lib/            # api.js (Axios instance), constants, utils
└── pages/          # Route-level page components
```

## Scripts

| Command          | Description                |
|------------------|----------------------------|
| `npm run dev`    | Start Vite dev server      |
| `npm run build`  | Production build to dist/  |
| `npm run lint`   | ESLint check               |
| `npm run preview`| Preview production build   |
