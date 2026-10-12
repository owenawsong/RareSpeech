# Security

Do not place credentials in command arguments or config literals. Speech API
keys are read from named environment variables. Configurations are trusted local
code configuration; Python adapters and executables run with your privileges.

Portable reports can contain input text, transcripts, audio, and reviewer
pseudonyms. Inspect them before publishing. The local server binds to localhost;
use static hosting for public reports rather than exposing that server.

Report a vulnerability privately to the maintainer using GitHub private
vulnerability reporting if enabled, or the contact on the maintainer’s profile.
Avoid putting exploit secrets or private audio in a public issue.
