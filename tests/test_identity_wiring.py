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


class _FakeSDK:
    """Stand-in for ERC8004Agent — no key, no network. Lets the resolver tests
    exercise every branch of the indexer-miss fallback without touching chain."""

    def __init__(self, *, local=None, on_chain=None, wallet="0xAa"):
        self._local = local
        self._on_chain = on_chain or {}
        self.wallet_address = wallet

    def get_local_agent_info(self, name):
        return self._local

    def get_agent_info(self, agent_id):
        if agent_id not in self._on_chain:
            raise RuntimeError("nonexistent token")
        return self._on_chain[agent_id]


def _point_evidence_at(tmp_path, monkeypatch, agent_id):
    ev = tmp_path / "agent_registration.json"
    ev.write_text(__import__("json").dumps({"agent_id": agent_id}))
    import register_agent
    monkeypatch.setattr(register_agent, "EVIDENCE", ev)


def test_resolve_prefers_indexer_hit(tmp_path, monkeypatch):
    """When the SDK's name lookup finds the agent, use it directly — no fallback,
    no on-chain read, no _source tag."""
    import register_agent
    _point_evidence_at(tmp_path, monkeypatch, 1395)
    sdk = _FakeSDK(local={"agent_id": 1395, "name": "x"})
    out = register_agent._resolve_existing_agent(sdk, "x")
    assert out == {"agent_id": 1395, "name": "x"}
    assert "_source" not in out


def test_resolve_falls_back_to_tracked_id_when_owner_matches(tmp_path, monkeypatch):
    """Indexer miss -> tracked id -> on-chain ownerOf matches this wallet (case-
    insensitively) -> resolved, tagged with its provenance."""
    import register_agent
    _point_evidence_at(tmp_path, monkeypatch, 1395)
    sdk = _FakeSDK(
        local=None,
        on_chain={1395: {"owner": "0xAa", "agentURI": "data:foo"}},
        wallet="0xAA",
    )
    out = register_agent._resolve_existing_agent(sdk, "smart-money-divergence")
    assert out["agent_id"] == 1395
    assert out["owner_address"] == "0xAa"
    assert "ownerOf" in out["_source"]


def test_resolve_returns_none_when_tracked_id_owned_by_another_wallet(tmp_path, monkeypatch):
    """The safety case: the tracked id exists on-chain but is owned by a DIFFERENT
    wallet (e.g. the throwaway 1403 wallet). Must return None so --update-endpoints
    refuses to update rather than minting a fresh throwaway agent."""
    import register_agent
    _point_evidence_at(tmp_path, monkeypatch, 1403)
    sdk = _FakeSDK(
        local=None,
        on_chain={1403: {"owner": "0x19E7", "agentURI": "data:foo"}},
        wallet="0x4727",
    )
    assert register_agent._resolve_existing_agent(sdk, "smart-money-divergence") is None


def test_resolve_returns_none_when_no_evidence_file(tmp_path, monkeypatch):
    """No indexer hit and no tracked record -> None (caller then refuses to send)."""
    import register_agent
    monkeypatch.setattr(register_agent, "EVIDENCE", tmp_path / "missing.json")
    sdk = _FakeSDK(local=None, wallet="0x4727")
    assert register_agent._resolve_existing_agent(sdk, "smart-money-divergence") is None
