<!--
  blast framework — Claude Code instructions (auto-loaded).

  This file lives in `.claude/` on purpose: Claude Code auto-loads BOTH
  `./CLAUDE.md` (yours) and `./.claude/CLAUDE.md` (this one) additively, so
  blast drops into any existing project WITHOUT colliding with your own root
  `CLAUDE.md`. Keep YOUR project-specific notes in your root `CLAUDE.md`.

  The framework rules themselves are the single source of truth in
  `.blast/CLAUDE.snippet.md` and are pulled in via the `@` import below. That
  keeps a `git pull` of blast updating them cleanly without touching your files.

  NOTE on `@` paths: Claude Code resolves a relative import relative to THIS
  file's directory (`.claude/`), so reaching `.blast/` needs the `../` prefix.
-->

@../.blast/CLAUDE.snippet.md
