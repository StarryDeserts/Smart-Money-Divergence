"""Offline tests for the ERC-8183 identity wiring. `_build_endpoints` is pure
(AgentEndpoint is a plain dataclass) — no key, no network. The actual on-chain
`set_agent_uri` update is a separate, user-gated demo step, not tested here."""
from __future__ import annotations


def test_build_endpoints_includes_erc8183_when_set(monkeypatch):
    monkeypatch.setenv("AGENT_ERC8183_URL", "https://prov.example/erc8183")
    import register_agent
    eps = register_agent._build_endpoints("https://repo.example/x")
    assert [e.name for e in eps] == ["web", "MCP", "ERC-8183"]
    assert eps[-1].endpoint == "https://prov.example/erc8183"


def test_build_endpoints_omits_erc8183_when_unset(monkeypatch):
    monkeypatch.delenv("AGENT_ERC8183_URL", raising=False)
    import register_agent
    eps = register_agent._build_endpoints("https://repo.example/x")
    assert [e.name for e in eps] == ["web", "MCP"]


def test_update_endpoints_flag_requires_url(monkeypatch, capsys):
    """--update-endpoints without AGENT_ERC8183_URL is rejected before any wallet
    or network work (returns exit code 2). `_load_env_local` is stubbed to a no-op
    so the guard's missing-URL precondition can't be re-populated from .env.local —
    this keeps the test (which calls main()) from ever reaching on-chain code."""
    monkeypatch.setattr("sys.argv", ["register_agent.py", "--update-endpoints"])
    monkeypatch.delenv("AGENT_ERC8183_URL", raising=False)
    monkeypatch.setenv("PRIVATE_KEY", "0x" + "11" * 32)
    import register_agent
    monkeypatch.setattr(register_agent, "_load_env_local", lambda: None)
    assert register_agent.main() == 2
    # Pin to the URL guard specifically — a missing PRIVATE_KEY would also return 2
    # but print a different message; assert we exited via the AGENT_ERC8183_URL path.
    assert "AGENT_ERC8183_URL" in capsys.readouterr().err
