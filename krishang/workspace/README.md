# Workspace contract

Runtime contents are disposable and must remain untracked. Each task receives an isolated namespace:

```text
workspace/<repository-hash>/<task-id>/
  repo/
  artifacts/
  logs/
  state/
```

Repository identity is part of the namespace so colliding issue numbers and paths cannot cross tenants.
Artifacts are immutable JSON records. Deep-lane mutations occur only in isolated git worktrees.

