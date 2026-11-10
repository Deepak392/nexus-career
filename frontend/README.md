# Nexus Career frontend

React + TypeScript frontend built with Vite and React Router.

## Current functionality

- Home page and opportunities discovery UI
- Opportunity search, filters, sorting, pagination, and detail pages
- Save-opportunity state in browser local storage
- Student academic profile and private PDF resume upload
- Eligibility breakdown on opportunity details
- Platform application submission and student status tracking
- Light/dark theme preference

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

The opportunity list, detail, student profile, eligibility, login, and application workflows are integrated with the Django API. Saved-opportunity state remains browser-local. External applications open the URL provided by the recruiter and are not marked as submitted inside Nexus Career.


## Appearance preferences

- A light/dark theme toggle is available in the application sidebar, including on sign-in and registration screens.
- The selected theme is saved in browser local storage and restored on the next visit.
- On the first visit, the application follows the operating system's color-scheme preference.
