# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately to **shreyas@vidarbhainfotech.com**.

Do not open a public issue for security vulnerabilities.

## Supported Versions

| Version | Supported |
|---------|-----------|
| v2.x (v2 branch) | Active development |
| v1.x (main branch) | No longer maintained |

## Security Practices

- All secrets managed via GCP Secret Manager
- Service account keys never committed to the repository
- Input sanitization on all user-facing endpoints
- AI prompt injection defense in system prompts
- Domain-restricted authentication (@vidarbhainfotech.com only)
- Non-root Docker containers
- Dependabot enabled for dependency updates
