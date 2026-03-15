---
created: 2026-03-15T16:10:00.000Z
title: Remove background from logo on login page
area: ui
files:
  - static/img/vipl-logo-full.jpg
  - templates/account/login.html
  - templates/socialaccount/login.html
---

## Problem

The VIPL logo on the login and social login pages has a visible background (white/colored rectangle) instead of being transparent. Looks unprofessional against the gradient background.

## Solution

Replace `vipl-logo-full.jpg` with a transparent PNG version, or use CSS to remove the background. The image file is a JPG (no transparency support) — need to convert to PNG with transparent background or use a version without background.
