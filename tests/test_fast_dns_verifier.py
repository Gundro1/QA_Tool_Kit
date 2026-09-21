import socket

from conftest import load_tool

dns = load_tool("fast-dns-verifier.py")


def fake_getaddrinfo(outcome):
    def _fake(host, timeout):
        if outcome == "ok":
            return "ok", [("addr",)]
        if outcome == "timeout":
            return "timeout", None
        return "error", socket.gaierror(socket.EAI_NONAME, "Name or service not known")
    return _fake


def test_local_resolver_failure_is_not_dead_when_doh_resolves(monkeypatch):
    monkeypatch.setattr(dns, "_getaddrinfo", fake_getaddrinfo("timeout"))
    monkeypatch.setattr(dns.time, "sleep", lambda s: None)
    monkeypatch.setattr(dns, "doh_lookup", lambda h, timeout=5.0: ("resolves", "dns.google A"))
    assert dns.verify_domain_dns("mercator.si")[1] == "resolves"


def test_dead_only_when_doh_confirms_nxdomain(monkeypatch):
    monkeypatch.setattr(dns, "_getaddrinfo", fake_getaddrinfo("nxdomain"))
    monkeypatch.setattr(dns, "doh_lookup", lambda h, timeout=5.0: ("nxdomain", "dns.google: NXDOMAIN"))
    assert dns.verify_domain_dns("adidas.si")[1] == "nxdomain"


def test_unreachable_resolvers_give_unknown(monkeypatch):
    monkeypatch.setattr(dns, "_getaddrinfo", fake_getaddrinfo("timeout"))
    monkeypatch.setattr(dns.time, "sleep", lambda s: None)
    monkeypatch.setattr(dns, "doh_lookup", lambda h, timeout=5.0: ("unknown", "ConnectionError"))
    assert dns.verify_domain_dns("example.si")[1] == "unknown"
    assert dns.verify_domain_dns("example.si", use_doh=False)[1] == "unknown"


def test_bare_domain_without_address_falls_back_to_www(monkeypatch):
    monkeypatch.setattr(dns, "_getaddrinfo", fake_getaddrinfo("nxdomain"))
    answers = {"tlscontact.com": ("no_address", "no A"), "www.tlscontact.com": ("resolves", "A")}
    monkeypatch.setattr(dns, "doh_lookup", lambda h, timeout=5.0: answers[h])
    assert dns.verify_domain_dns("tlscontact.com")[1] == "resolves"


def test_getaddrinfo_timeout_is_enforced(monkeypatch):
    import time
    monkeypatch.setattr(dns.socket, "getaddrinfo", lambda *a: time.sleep(2))
    start = time.perf_counter()
    assert dns._getaddrinfo("slow.example", 0.2)[0] == "timeout"
    assert time.perf_counter() - start < 1
