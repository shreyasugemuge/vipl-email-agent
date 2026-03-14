# Roadmap: VIPL Email Agent

## Milestones

- **v2.1 VIPL Email Agent v2** — Phases 1-6 (shipped 2026-03-14) — [archive](milestones/v2.1-ROADMAP.md)
- **v2.2 Polish & Hardening** — Phases 1-4 (active)

## Phases

### v2.2 — Polish & Hardening

- [ ] Phase 1: Google OAuth SSO (0/1 plans) — planned
  Plans:
  - [ ] 01-PLAN.md — allauth setup, domain adapter, login redesign, avatar, welcome toast
- [ ] Phase 2: Settings Page + Spam Whitelist (0/2 plans) — planned
  Plans:
  - [ ] 02-01-PLAN.md — SpamWhitelist model, pipeline whitelist integration, bool normalization, config editor improvements
  - [ ] 02-02-PLAN.md — Whitelist settings tab, whitelist sender button, SLA save feedback
- [ ] Phase 3: VIPL Branding (0/0 plans) — not started
- [ ] Phase 4: Chat Notification Polish (0/0 plans) — not started

<details>
<summary>v2.1 (Phases 1-6) — SHIPPED 2026-03-14</summary>

- [x] Phase 1: Foundation (2/2 plans) — completed 2026-03-09
- [x] Phase 2: Email Pipeline (3/3 plans) — completed 2026-03-11
- [x] Phase 3: Dashboard (3/3 plans) — completed 2026-03-11
- [x] Phase 4: Assignment Engine + SLA (3/3 plans) — completed 2026-03-11
- [x] Phase 4.5: Integration Fixes + Tech Debt (2/2 plans) — completed 2026-03-12
- [x] Phase 5: Reporting + Admin + Sheets Mirror (3/3 plans) — completed 2026-03-12
- [x] Phase 6: Migration + Cutover (2/2 plans) — completed 2026-03-14

</details>

## Phase Details

### Phase 1: Google OAuth SSO

**Goal:** Replace password-only auth with Google Sign-In, domain-locked to @vidarbhainfotech.com, while keeping password login as superuser fallback.

**Plans:** 1 plan

**Delivers:**
- `django-allauth[socialaccount]` integration with Google provider
- Custom `VIPLSocialAccountAdapter` enforcing @vidarbhainfotech.com server-side
- Auto-provision new users as `role=MEMBER` on first Google sign-in
- "Sign in with Google" button on login page alongside existing password form
- GCP OAuth credentials (Internal consent screen, utilities-vipl project)

**Key risks:**
- Non-VIPL Google accounts bypassing `hd` param (must enforce in adapter)
- Existing superuser with blank email field breaking allauth email validation
- `django.contrib.sites` + `SITE_ID = 1` setup (common allauth pitfall)

**Requirements:**
- R1.1: Install django-allauth[socialaccount], configure INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS
- R1.2: Custom SocialAccountAdapter with server-side @vidarbhainfotech.com domain enforcement
- R1.3: Google Sign-In button on login page, password form preserved
- R1.4: Auto-provision new Google users as MEMBER role
- R1.5: Data migration to set email on existing superuser accounts
- R1.6: GCP OAuth consent screen (Internal) + credentials in utilities-vipl project

**Pre-requisite (manual):** Create OAuth 2.0 credentials in GCP Console before testing.

---

### Phase 2: Settings Page + Spam Whitelist

**Goal:** Make settings page type-aware with pre-filled values, and add spam whitelist with "Not Spam" recovery path.

**Plans:** 2 plans

**Delivers:**
- Type-aware settings inputs (toggle for bool, number for int, text pre-filled)
- `SpamWhitelist` model (email + domain entries, added_by FK)
- `spam_filter.is_spam()` checks whitelist before regex (AI triage always runs)
- "Whitelist Sender" button in email detail panel (admin-only)
- Spam whitelist management tab in settings page
- Inline HTMX save feedback on all settings tabs

**Key risks:**
- Whitelisted senders must still go through AI triage (phishing via spoofed trusted addresses)
- Bool type coercion: unchecked checkbox sends no form field (interpret as "false")
- Existing SystemConfig bool values may be uppercase "True" — normalize via data migration

**Requirements:**
- R2.1: Type-aware input widgets in _config_editor.html (checkbox/number/text/textarea by value_type)
- R2.2: Pre-fill all settings inputs with current DB values
- R2.3: SpamWhitelist model with email/domain entry types, migration
- R2.4: spam_filter.is_spam() checks whitelist first, AI triage always runs regardless
- R2.5: "Whitelist Sender" button in email detail panel (admin-only POST endpoint)
- R2.6: Spam whitelist management tab in settings (add/remove entries, HTMX)
- R2.7: Data migration to normalize existing bool values to lowercase
- R2.8: Inline save feedback on SLA Config tab (currently silent)

---

### Phase 3: VIPL Branding

**Goal:** Replace placeholder icons with VIPL logo and apply brand identity across all pages.

**Delivers:**
- VIPL logo in sidebar and login page (from static/img/, not Drive link)
- Brand color palette in @theme block
- Consistent styling across all templates including HTMX partials

**Key risks:**
- @theme tokens in base.html unavailable to HTMX-swapped fragments — must update inline classes in partials
- Must audit all _*.html partials for hardcoded color classes

**Requirements:**
- R3.1: VIPL logo asset committed to static/img/
- R3.2: Logo rendered in sidebar and login page
- R3.3: Brand color palette applied in @theme block
- R3.4: All _*.html HTMX partials audited and updated for brand colors

**Pre-requisite:** Logo asset from Google Drive (fallback: text-based SVG).

---

### Phase 4: Chat Notification Polish

**Goal:** Improve Google Chat notification cards with direct email links and richer card structure.

**Delivers:**
- Per-email "Open" button in breach alert cards (direct link to specific email)
- Richer card structure using decoratedText with inline button
- Consistent SLA urgency display across all card types

**Key risks:**
- Card payload must validate in Card Builder before deploy
- Deploy outside business hours to avoid mixed old/new card formats

**Requirements:**
- R4.1: Add pk to breach data structure passed to notify_personal_breach()
- R4.2: Per-email "Open" direct link button in breach alert decoratedText
- R4.3: Consistent SLA urgency emoji/label display across all 4 notify methods
- R4.4: Validate card payloads in Google Chat Card Builder before merge

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Google OAuth SSO | v2.2 | 0/1 | Checkpoint pending | — |
| 2. Settings + Spam Whitelist | v2.2 | 0/2 | Planned | — |
| 3. VIPL Branding | v2.2 | 0/0 | Not started | — |
| 4. Chat Notification Polish | v2.2 | 0/0 | Not started | — |
| 1. Foundation | v2.1 | 2/2 | Complete | 2026-03-09 |
| 2. Email Pipeline | v2.1 | 3/3 | Complete | 2026-03-11 |
| 3. Dashboard | v2.1 | 3/3 | Complete | 2026-03-11 |
| 4. Assignment Engine + SLA | v2.1 | 3/3 | Complete | 2026-03-11 |
| 4.5. Integration Fixes | v2.1 | 2/2 | Complete | 2026-03-12 |
| 5. Reporting + Admin | v2.1 | 3/3 | Complete | 2026-03-12 |
| 6. Migration + Cutover | v2.1 | 2/2 | Complete | 2026-03-14 |
