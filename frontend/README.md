# Nexus Career frontend

React + TypeScript frontend built with Vite and React Router.

## Current functionality

- Home page and opportunities discovery UI
- Opportunity search, filters, sorting, pagination, and detail pages
- Save-opportunity state in browser local storage
- Placeholder pages for saved jobs, applications, profile, and settings

## Run locally

Install Node.js 24, then from this directory run:

```bash
npm ci
npm run dev
```

Open the URL printed by Vite (normally http://localhost:5173/).

## Checks

```bash
npm run lint
npm run build
```

## Integration status

The opportunity list currently uses mock data from `src/mocks/opportunities.ts`. The sign-in button is a local UI demo and does not authenticate against Django. Backend API integration, real student authentication, saved-job persistence, and application submission are not yet implemented in this frontend.


## Appearance preferences

- A light/dark theme toggle is available in the application sidebar, including on sign-in and registration screens.
- The selected theme is saved in browser local storage and restored on the next visit.
- On the first visit, the application follows the operating system's color-scheme preference.
