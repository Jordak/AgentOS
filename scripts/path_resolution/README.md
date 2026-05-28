# Path Resolution

This package contains reusable path-resolution modules for trusted AgentOS scripts.

The declared root passed to a public module is the trust boundary. Managed-path checks reject the declared root itself if it is a symlink and reject symlink traversal beneath that root; they do not try to authenticate ancestor directories or reject symlinks in those ancestors.

Public callers should import a path-resolution module that matches the policy they need, such as:

```python
from path_resolution import managed_path_problem_text
```

or:

```python
from path_resolution.managed import managed_path_problem_text
```

The `_primitives.py` module is private implementation shared by path-resolution modules. Callers outside this package must not import or compose `_primitives.py` directly. If a caller needs behavior that is only available as a primitive, add or deepen a public path-resolution module instead.

This keeps the public modules deep: callers ask a policy-shaped question, while lexical path normalization, containment checks, `lstat()` facts, and no-follow component walking stay behind the package seam.

Run the managed-path self-test with:

```bash
python3 scripts/path_resolution/managed.py --self-test
```
