# Changelog

## 1.0.0 - unreleased

First public release.

- One self-contained theme file: the textures are SVGs embedded as data URIs, so HACS needs nothing in `www/`.
- `tools/build_theme.py` generates the theme; `--check` (run in CI) fails when the YAML is out of date.
