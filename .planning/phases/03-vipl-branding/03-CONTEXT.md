# Phase 3: VIPL Branding - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace placeholder indigo theme with VIPL brand identity. Logo placement, color palette, and consistent styling across all templates including HTMX partials. No new features — pure visual branding pass.

</domain>

<decisions>
## Implementation Decisions

### Logo placement
- **Sidebar**: 1.jpg (Vi mark icon — black V + purple i) in sidebar header
- **Login page**: 2.jpg (full logo with "VIDARBHA INFOTECH PVT. LTD" + tagline "TELECOMMUNICATIONS & I.T. SOLUTION") centered on login card
- **Favicon**: Generate 32x32 favicon.ico from 1.jpg Vi mark icon
- Logo source files: `/Users/uge/Library/CloudStorage/GoogleDrive-shreyas@vidarbhainfotech.com/Other computers/Laptop/Downloads/vipl logo/` (1.jpg, 2.jpg, 3.jpg white version for dark backgrounds)
- Commit logos to `static/img/` — do not hotlink from Drive

### Brand colors
- Claude picks the right colors derived from the logo (dark purple/plum ~#7B2D5F + black #2D2D2D)
- Replace the indigo @theme palette in base.html with a brand-derived purple/plum palette
- Sidebar background: Claude's discretion (light or dark, whichever works best with brand)

### Color scope
- **Functional status colors stay as-is**: priority badges (red=CRITICAL, amber=HIGH, green=LOW), status dots, SLA countdown colors, spam badges — all unchanged
- Only brand/accent colors change (buttons, active states, links, focus rings, gradients)
- Google OAuth button stays Google-standard (white + Google logo) — don't rebrand

### Login page
- Full branded login card: 2.jpg logo, tagline, Google sign-in button
- Clean white background with brand accent on card border
- No split layout — centered card

### Browser tab
- Page title format: "VIPL Triage | {Page}" (e.g., "VIPL Triage | Emails", "VIPL Triage | Settings")
- Favicon from Vi mark icon

### Google Chat cards
- Add VIPL icon image in card header
- Add "Sent by VIPL Email Triage" footer text on all card types
- Keep cards functional — branding is additive, not replacing content

### Footer
- Subtle bottom bar on dashboard: "© 2026 Vidarbha Infotech Pvt. Ltd." in small gray text
- Not distracting — just a presence indicator

### Claude's Discretion
- Exact purple/plum palette values (50-900 scale)
- Sidebar light vs dark background
- Spacing and typography adjustments for logo placement
- Dev inspector (/emails/inspect/) — leave as-is or update, Claude decides
- How to handle 3.jpg (white version) — use on dark backgrounds if applicable

</decisions>

<specifics>
## Specific Ideas

- Logo has two distinct colors: black for the "V" stroke, plum/purple for the "i" stroke with dot
- The plum color from the logo should drive the primary palette
- "INFOTECH" in the full logo text is italicized — this is a brand detail
- 3.jpg appears to be a white-on-white version (for dark backgrounds)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `base.html`: Has `@theme` block with `--color-primary-50` through `--color-primary-900` (currently indigo) — single source for primary palette
- `templates/registration/login.html`: Existing login page template to add logo to
- `templates/registration/dev_login.html`: Dev login page (role picker) — also needs branding

### Established Patterns
- Tailwind CSS v4 via CDN play script — all styling is utility classes in templates
- `@theme` custom properties in base.html `<style>` block — centralized color definition
- HTMX partials (`_*.html`) use hardcoded Tailwind color classes (e.g., `bg-indigo-600`) — NOT @theme vars
- 295 color class occurrences across 18 template files need auditing
- Priority/status colors use separate Tailwind classes (`priority_base`, `status_base` template tags) — won't conflict with brand change

### Integration Points
- `base.html` `<style>` block: @theme palette swap
- `base.html` `<title>` tag: page title update
- `base.html` header/sidebar: logo image insertion
- All `_*.html` partials: indigo → brand color class replacement
- `config/settings/base.py`: STATIC_URL and STATICFILES_DIRS for serving logo
- `apps/emails/services/chat_notifier.py`: Google Chat card templates for logo + footer

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-vipl-branding*
*Context gathered: 2026-03-14*
