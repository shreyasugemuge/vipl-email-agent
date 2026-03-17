---
created: 2026-03-17T16:01:53.356Z
title: Download email attachments from dashboard
area: emails
files:
  - apps/emails/models.py
  - apps/emails/services/gmail_poller.py
  - apps/emails/services/pdf_extractor.py
---

## Problem

Email attachments are tracked as `AttachmentMetadata` (filename, size, MIME type) but the actual file content is not stored or downloadable. Users viewing a thread in the dashboard can see that attachments exist but cannot download them. The Gmail API has the attachment data available during polling but it's only used for PDF text extraction, not persisted.

## Solution

- During Gmail polling, store attachment content (or a reference) — either in the database (for small files) or on disk/object storage
- Add a download endpoint: `/emails/threads/<pk>/attachments/<attachment_id>/download/`
- Show download links on thread detail next to each attachment metadata entry
- Consider size limits and security (content-type validation, virus scanning for production)
- Alternative: lazy-fetch from Gmail API on demand (avoids storage but requires API call per download)
