# Development workflow

The existing branches are retained: `dev` integrates reviewed work; `prod` holds
released code. Start each card from updated `dev`:

```sh
git switch dev
git pull --ff-only
git switch -c feat/9-song-entry-model
```

Use `feat/<card-number>-<slug>`, `fix/<card-number>-<slug>`, or
`chore/<slug>`. Keep one coherent change per branch. Link the Trello card in the
PR and describe its acceptance criteria and validation. Use commit subjects like
`feat(domain): add song entry model` or `chore: establish project foundation`.

Before opening a PR to `dev`, run `uv run python scripts/check.py` and `uv build`.
Keep tests offline and use sanitized fixtures. Update CHANGELOG.md for visible
changes. Commit pyproject.toml and uv.lock together when dependencies change.
Use `uv add` / `uv add --dev` and review the lockfile diff; upgrades are deliberate.

Trello flow: Planned → WorkingOn → Testing → Review → Done. Move a card to Done
only after its acceptance criteria pass and the PR is merged. The board is the
backlog; GitHub PRs hold code review. Board updates are manual.

Squash feature PRs into dev and delete merged feature branches. Release PRs from
dev to prod use merge commits to retain shared ancestry. After a prod hotfix,
merge prod back to dev so subsequent releases do not lose the fix.

Recommended GitHub rules for both dev and prod: require PRs, passing `quality`
and `test (ubuntu-latest)` / `test (windows-latest)` checks, resolved conversations,
and block force pushes/deletions. For a solo maintainer, do not require another
person's approval. These are instructions; remote protection is not yet enabled.
