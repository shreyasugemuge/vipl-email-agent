---
created: 2026-03-17T10:26:00.000Z
title: Tender notification module with scraping and auto-forwarding
area: general
files: []
---

## Problem

Need a fully automated, real-time tender notification system that:
- Receives tender notifications from various portals (email-based and web-scraped)
- Forwards relevant tenders to the right team/group based on category/keywords
- Scrapes tender portals for corrigendums (amendments/addendums) and alerts the team
- Breaks CAPTCHAs on tender portals for automated access
- Avoids bot detection (anti-scraping measures, rate limiting, fingerprinting)
- Maintains high accuracy in tender matching and categorization

This is a major new module — potentially a separate service or a large feature within the email agent.

## Solution

Architecture considerations:
- **Scraping layer**: Headless browser (Playwright/Puppeteer) with anti-detection (stealth plugins, rotating proxies, realistic fingerprints, human-like delays)
- **CAPTCHA solving**: Integration with CAPTCHA solving services (2Captcha, Anti-Captcha) or ML-based OCR (Tesseract + custom model)
- **Tender parsing**: NLP/AI-based extraction of tender details (deadline, category, value, eligibility)
- **Corrigendum tracking**: Diff-based monitoring of tender pages for amendments
- **Routing engine**: Rule-based + AI categorization to forward tenders to correct groups (Google Chat, email, or internal)
- **Real-time pipeline**: Scheduler polling portals at intervals + webhook receivers for email-based notifications
- **Portal targets**: GEM, CPPP, state e-procurement portals, sector-specific portals
- **Storage**: Tender model with dedup (tender ID + portal), version history for corrigendums
- **Notifications**: Google Chat cards, email digests, priority alerts for deadlines

This is a large initiative — likely needs its own milestone with multiple phases (research, architecture, portal integrations, CAPTCHA handling, routing, notifications).
