# No Symlinks in AgentOS-Managed Files

AgentOS-managed files and directories outside `personal/` should be concrete filesystem entries, not symbolic links. The validator rejects symlinks anywhere in the AgentOS checkout except under top-level `personal/`, and public export must reject symlinks rather than preserving or following them.

The same rule applies when AgentOS scripts perform managed reads or writes. If a script is asked to read from, copy from, write to, update, prune, or validate an AgentOS-managed file tree, it must not silently follow symlinks in that source or destination tree. When a symlink is encountered, the script should fail closed with a clear diagnostic instead of treating the linked target as part of the managed file set.

The Personal Overlay is different because it is private, ignored, and machine-local. AgentOS cannot globally enforce that every user's `personal/os/` tree is symlink-free, and it should not claim that private local state is portable or publication-safe by default. However, once a Personal Overlay path is used as canonical AgentOS-managed input or output for a script, the managed operation should apply the same no-symlink rule to the relevant files and directories.

This policy keeps AgentOS easier to audit. A reviewer should be able to inspect the visible tree and understand which files an AgentOS operation may read or modify without also resolving filesystem shortcuts into arbitrary machine-local locations. It also reduces the executable complexity needed in trusted scripts, because tools can reject surprising filesystem shapes instead of implementing broad symlink traversal policy.

The cost is losing symlink-based convenience for sharing one physical file across multiple AgentOS-managed paths or redirecting old paths to new paths. Prefer Markdown links, explicit config paths, or small migration notes for those cases, because they are visible in ordinary text review and do not redirect filesystem reads or writes.
