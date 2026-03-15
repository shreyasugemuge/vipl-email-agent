---
created: 2026-03-15T10:35:34.389Z
title: Fix Gmail profile picture import
area: auth
files:
  - apps/accounts/adapters.py
  - apps/accounts/models.py
---

## Problem

Google profile pictures are not being imported/displayed correctly when users log in via Google OAuth SSO. Phase 8 (OAuth Hardening) added `_update_avatar()` helper and structured OAuth logging, but the avatar fetch is currently not working — users don't see their Gmail profile picture in the app.

## Solution

- Debug the `_update_avatar()` flow in `VIPLSocialAccountAdapter` — check if the Google People API / userinfo endpoint is returning the picture URL
- Verify the avatar URL is being stored on the User model and rendered in templates
- Check if the issue is CORS, URL expiry, or a missing scope (`profile` / `userinfo.profile`)
- Consider caching/proxying the avatar to avoid broken images if Google URLs expire
- Test with real Google OAuth login flow
