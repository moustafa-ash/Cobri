# Cobri learner app

React, TypeScript, and Vite learner client. Copy `.env.example` to `.env.local`, configure the
Auth0 SPA values, then run `npm install` and `npm run dev`.

The development server uses `http://localhost:5173` with a strict port. Configure that exact URL
as the Auth0 callback, logout URL, and allowed web origin.

Generate API types while the backend is running on port 8000 with `npm run generate:api`.
