import pytest

from pricewise_mcp import cli


def test_defaults_are_stdio_on_loopback():
    a = cli.build_parser().parse_args([])
    assert (a.transport, a.host, a.port) == ("stdio", "127.0.0.1", 8000)


def test_unknown_transport_is_rejected(capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--transport", "sse"])
    assert "invalid choice" in capsys.readouterr().err


def run_main(monkeypatch, argv):
    calls = []
    monkeypatch.setattr(cli.mcp, "run", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(cli.service, "warm", lambda: None)
    cli.main(argv)
    return calls


def test_http_is_stateless_json_on_loopback(monkeypatch, capsys):
    calls = run_main(monkeypatch, ["--transport", "http", "--port", "9123"])
    assert calls == [
        (
            ("streamable-http",),
            {"host": "127.0.0.1", "port": 9123, "stateless_http": True, "json_response": True},
        )
    ]
    assert capsys.readouterr().err == ""


def test_binding_beyond_loopback_warns(monkeypatch, capsys):
    run_main(monkeypatch, ["--transport", "http", "--host", "0.0.0.0"])
    assert "without authentication" in capsys.readouterr().err
