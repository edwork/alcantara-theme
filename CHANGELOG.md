# Changelog

## Unreleased

- README: install by searching HACS (Marketplace); adding a custom repository is now the fallback. The badge now says HACS Default.

## 1.0.0 - 2026-11-11

First public release.

- One self-contained theme file: the textures are SVGs embedded as data URIs, so HACS needs nothing in `www/`.
- `tools/build_theme.py` generates the theme; `--check` (run in CI) fails when the YAML is out of date.
