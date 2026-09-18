# Security

## What this is

A local teaching application. It binds to 127.0.0.1 only, keeps state in memory, and calls a provider only after the account owner pastes a key and ticks a consent box for the run. It is not designed to be exposed to a network, shared between users, or fed real company data.

## Reporting

If you find a way for a key to leave the server process, for content in a case to reach the server as instructions, for the loopback boundary to be crossed, or for a response to be presented as something it is not, please open a private security advisory on the repository rather than a public issue. Include the steps to reproduce. There is no bounty.

## Handling keys

Keys are held in the server process's memory, pasted through the Connect screen or exported in the terminal that starts the server. They are never written to disk, never logged, never placed in a URL or a page, and shown only as their last four characters. If a key has appeared anywhere else, rotate it at the provider.

## Scope notes

- The session token that protects the local API is per process and is sent only to the page served from the same origin.
- The Content Security Policy allows same-origin scripts and styles only. Inline styles set through the CSSOM are permitted by design.
- The `claude` command arm runs the user's own signed-in CLI with tools disallowed. It is opt-out with `JEV_ALLOW_CLAUDE_CODE=0`.
