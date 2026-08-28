# Changelog

## Unreleased

### Breaking

- Renamed the package from `notemovie` to `funmovie` to match the repository name (`note*` → `fun*` cleanup, part of farfarfun/todo-list#298). The import name and the PyPI package name declared in `pyproject.toml` both changed:
  - `import notemovie...` -> `import funmovie...`
  - PyPI package name `notemovie` -> `funmovie`
  - Checked `pip index versions notemovie`: no distribution was ever published under the old name, so there is nothing to forward. If that changes, publishing a final forwarding release of `notemovie` that points users to `funmovie` is a manual follow-up for the repo owner, not automated here.
