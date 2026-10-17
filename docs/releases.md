# Versioning and releases

pyproject.toml is the single version source; the app reads installed metadata.
Start at `0.1.0.dev0`. Use semantic versions: PATCH for fixes, MINOR for features,
MAJOR for incompatible changes. During 0.x, breaking changes increment MINOR.
Previews use `0.1.0rc1`; Git tags have a v prefix (for example `v0.1.0`).

1. Prepare a release branch from dev; update project version and CHANGELOG.md,
   run `uv lock`, quality checks, and `uv build`; merge its PR into dev.
2. Open a release PR from dev to prod and require all checks; merge with a merge
   commit. Only release functionality actually validated on supported platforms.
3. From updated prod, create an annotated tag matching pyproject.toml:
   `git tag -a v0.1.0 -m "Release 0.1.0"`, then `git push origin v0.1.0`.
4. Create a GitHub release with notes and verified distribution assets. Do not
   relabel wheels as standalone installers. Desktop packaging is a later phase.

No release tag is created for the initial scaffold. Tags are immutable; fixes
get a new version. Dependency locks are committed, and CI uses `uv sync --locked`.
