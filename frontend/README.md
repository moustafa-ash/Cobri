# Cobri learner app

React, TypeScript, and Vite learner client. Copy `.env.example` to `.env.local`, configure the
Auth0 SPA values, then run `npm ci` and `npm run dev`.

The development server uses `http://localhost:5173` with a strict port. Configure that exact URL
as the Auth0 callback, logout URL, and allowed web origin.

Generate API types while the backend is running on port 8000 with `npm run generate:api`.

For credential-free browser coverage, use the root command `npx playwright test --project=chromium`.
It starts this Vite app and opens `visual.html`, which mounts the real learner UI with deterministic
test doubles. The fixture does not exercise Auth0 or external providers.
