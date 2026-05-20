# Publishable Core With Personal Overlay

AgentOS will split reusable scaffolding from private user-specific state by keeping publishable AgentOS Core files under `$root/os/` and private Personal Overlay files under `$root/personal/os/`. Core and Personal Overlay use the same layer shape, Core is read first, and matching Personal Overlay files are read afterward so private details can extend or override user-specific facts without making the publishable system depend on hidden files.

This preserves AgentOS as a reusable Markdown control plane while avoiding a sanitized snapshot of the user's private workspace. The v1 overlay root is fixed at `$root/personal/os/`; optional external overlay discovery is deferred until there is a real need.
