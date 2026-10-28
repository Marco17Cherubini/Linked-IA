"""Comandi operativi: nessuno usa servizi a pagamento, nessuno cancella dati."""

from __future__ import annotations

import io
import sqlite3

from argon2 import PasswordHasher
from helpers import Operator, client_for, make_app

from linkedia import cli


def env_for(monkeypatch, settings):
    monkeypatch.setenv("LIA_DATABASE_PATH", str(settings.database_path))
    monkeypatch.setattr("linkedia.config.PROJECT_ROOT", settings.database_path.parent)


def test_hash_password_reads_stdin_and_never_echoes_it(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("una-password-lunga\n"))
    assert cli.main(["hash-password"]) == 0
    out = capsys.readouterr().out.strip()
    assert "una-password-lunga" not in out
    assert PasswordHasher().verify(out, "una-password-lunga")


def test_hash_password_rejects_short_passwords(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("corta\n"))
    assert cli.main(["hash-password"]) == 2


def test_revoke_sessions(settings, monkeypatch):
    app = make_app(settings)
    op = Operator(client_for(app))
    env_for(monkeypatch, settings)
    assert cli.main(["revoke-sessions"]) == 0
    assert op.client.get("/api/auth/session").get_json()["authenticated"] is False


def test_backup_is_a_consistent_copy(settings, monkeypatch, tmp_path):
    make_app(settings)
    env_for(monkeypatch, settings)
    assert cli.main(["backup", "--dir", str(tmp_path / "bk")]) == 0
    [copy] = list((tmp_path / "bk").glob("lia-*.sqlite3"))
    with sqlite3.connect(copy) as conn:
        assert conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] == "3"


def test_init_does_not_download_when_public_cases_exist(settings, monkeypatch):
    app = make_app(settings)
    analysis = app.extensions["lia"]["analysis"]
    analysis.import_catalogue()
    store = app.extensions["lia"]["store"]
    for event in store.all_events():
        analysis_id = store.create_analysis(event.id, "2.0.0")
        store.finish_analysis(analysis_id, {"fixture": True})
    before = len(store.all_events())
    env_for(monkeypatch, settings)
    # La rete è bloccata dai test: se init provasse a scaricare prezzi fallirebbe.
    assert cli.main(["init"]) == 0
    assert len(store.all_events()) == before
    assert list((settings.database_path.parent / "backups").glob("lia-*.sqlite3"))
