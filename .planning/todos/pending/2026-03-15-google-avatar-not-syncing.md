---
created: 2026-03-15T16:30:00.000Z
title: Google profile photo not syncing — shows initial instead of avatar
area: auth
files:
  - apps/accounts/adapters.py
  - apps/accounts/models.py
  - config/settings/base.py
---

## Problem

Google profile picture still shows the colored initial circle (S) instead of the actual Google avatar photo. The `_update_avatar()` helper exists but the avatar URL isn't being fetched/stored. User asks if re-signup is needed or if there's a setting.

No re-signup needed — the adapter should fetch the photo URL on each login. Issues may be:
1. Google People API scope not included (`profile` or `userinfo.profile`)
2. The avatar URL from Google's `extra_data` not being extracted correctly
3. `avatar_url` field not rendered in the sidebar template

## Solution

1. Check `SOCIALACCOUNT_PROVIDERS` Google config for correct scopes (need `profile` or `userinfo.profile`)
2. Debug `_update_avatar()` in VIPLSocialAccountAdapter — log what Google returns in `extra_data`
3. Verify `user.avatar_url` is rendered in sidebar template with `<img>` fallback
4. May need to add `AUTH_PARAMS: {"access_type": "online"}` and ensure `picture` field is in Google's response
5. Consider adding a "Sync Avatar" button in settings or auto-sync on every login
