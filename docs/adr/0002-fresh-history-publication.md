# Fresh-History Publication

AgentOS must not make a formerly private repository public when that repository's history has contained private personal state. The publication path is to keep the current private repository private until the migration is complete, build a sanitized public export from AgentOS Core plus the tracked Personal Overlay skeleton, and create the public GitHub repository from a fresh initial commit.

This avoids relying on ordinary file deletion, moves, or `.gitignore` rules to protect old commits. Before deleting or replacing the current private GitHub repository, preserve any GitHub issue, ADR, PR, settings, or planning text worth keeping in a private Personal Overlay archive.
