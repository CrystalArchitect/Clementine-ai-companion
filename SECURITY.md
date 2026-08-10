# Security Policy

## Supported versions

Rolling: the latest `main` is the supported version.

## Reporting a vulnerability

Please report privately via GitHub → **Security** tab → **Report a vulnerability**
(private vulnerability reporting). If that is unavailable, open an issue titled
"security contact request" **without details** and a private channel will be arranged.
You can expect an acknowledgement within 7 days. Please do not disclose publicly
until a fix has shipped.

## Safety measures in this repo

- **Clementine is local-first** (`clementine/`): the companion runs on the
  user's own device via Ollama by default; memory and profiles stay on disk.
- **Cloud is opt-in only**: the xAI provider requires an explicit `/optin` and can
  be revoked with `/optout`; opt-in state is recorded locally.
- **No telemetry** — the app phones home to no one.
- **No secrets committed** — `.gitignore` blocks `.env`, keys, and credentials;
  `XAI_API_KEY` is read from the environment only.

## Scope

Reports about the Clementine companion app, the SvelteKit site, memory/privacy
handling, or leaked credentials are all in scope.
