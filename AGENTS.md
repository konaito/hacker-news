# Repository Guidelines

## Project Structure & Module Organization

This repository builds ALLALARM Cyber Journal, a Japanese static cybersecurity news dashboard.

- `data/incidents.json`: stable incident records; `data/sources.json`: source registry; `data/monthly-digests.json`: editorial digests.
- `ai-content.html`: detailed AI-related report fragments.
- `build.py`: standard-library Python generator that produces `public/index.html`.
- `public/app.js` and `public/style.css`: search, filters, sorting, dialogs, and responsive styling.
- `public/assets/`, `public/fonts/`, and `public/icons/`: self-hosted visual assets and licenses.
- `public/_headers`, `robots.txt`, and `sitemap.xml`: hosting and discovery configuration.
- `ASSET_NOTES.txt`: image provenance and asset details.

Edit source content and templates, then regenerate the page; direct edits to `public/index.html` are overwritten by the build. No tests directory or package manifest is present.

## Build, Test, and Development Commands

Run commands from the repository root:

- `python3 build.py`: regenerate the dashboard; requires no third-party Python packages.
- `python3 -m http.server 4173 --directory public`: preview at `http://localhost:4173`.
- `node --check public/app.js`: check JavaScript syntax when Node.js is available.
- `npx wrangler pages deploy public --project-name allalarm-hackernews --branch main`: publish to the documented Cloudflare Pages project when deployment is intended.

## Coding Style & Naming Conventions

Use four-space indentation for Python and two spaces for JavaScript, following nearby code. Python names use `snake_case`; JavaScript uses `camelCase`; CSS classes and HTML IDs use hyphenated names such as `filter-tab`. Keep Japanese editorial copy consistent. Preserve HTML escaping in generated markup and accessible labels, keyboard focus, and reduced-motion support. No formatter or linter is configured; avoid unrelated reformatting of compact CSS and templates.

## Testing Guidelines

No automated testing framework or coverage threshold is configured. Rebuild and inspect the preview before submitting changes. Check search, combined filters, sorting, pagination, empty results, dialog opening/closing, and mobile layouts. Run `python3 scripts/validate.py`. Published records require a primary source or two independent reporting publishers; single-source candidates remain pending. Counts and month filters derive from JSON.

## Commit & Pull Request Guidelines

Hourly auditing uses local Git commits; push runs only when an origin remote is configured. Use concise imperative subjects, such as `Fix region filter reset`. Describe the change and validation in each PR; link relevant issues and include screenshots for visual changes.

## Content & Configuration

Verify primary announcements before updating incident claims. Distinguish confirmed leaks, possible exposure, disruption, and AI capability assessments. Keep the information cutoff and sitemap modification date consistent. Preserve asset licenses. Configure `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` securely; never store credentials in source or `public/`.
