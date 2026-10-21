import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parity = _load("parity", "tools/parity/parity.py")
fixtures = _load("generate_fixtures", "tools/fixtures/generate_fixtures.py")

PERIOD = "2026-07"


def _meridian_mirror(refs):
    vantage = parity.vantage_invoices_by_ref(PERIOD)
    return {
        ref: {
            "billing_ref": ref,
            "total": vantage[ref]["invoice_total"],
            "province": "ON",
            "cust_nm": "x",
        }
        for ref in refs
    }


@pytest.fixture
def meridian(monkeypatch):
    def use(records):
        monkeypatch.setattr(parity, "meridian_invoices", lambda *a, **k: records)

    return use


def test_parity_ok_when_every_account_joins_and_agrees(meridian, capsys):
    meridian(_meridian_mirror(parity.vantage_invoices_by_ref(PERIOD)))
    assert parity.compare(PERIOD, ROOT, build=False) == 0
    assert "PARITY OK" in capsys.readouterr().out


def test_parity_fails_when_no_accounts_join(meridian, capsys):
    mirror = _meridian_mirror(parity.vantage_invoices_by_ref(PERIOD))
    meridian({ref.replace("-", "0"): row for ref, row in mirror.items()})
    assert parity.compare(PERIOD, ROOT, build=False) == 1
    assert "0 accounts joined" in capsys.readouterr().out


def test_parity_fails_when_some_accounts_do_not_join(meridian, capsys):
    refs = sorted(parity.vantage_invoices_by_ref(PERIOD))
    meridian(_meridian_mirror(refs[1:]))
    assert parity.compare(PERIOD, ROOT, build=False) == 1
    assert "1 present in only one system" in capsys.readouterr().out


def test_meridian_export_keeps_vantage_billing_refs(tmp_path):
    (tmp_path / "data").mkdir()
    built = fixtures.build_fixtures()
    fixtures.write_meridian(built, tmp_path)
    exported = {
        line.split("=", 1)[1]
        for rec in (tmp_path / "billing" / "accounts").glob("*.rec")
        for line in rec.read_text().splitlines()
        if line.startswith("BILLING_REF=")
    }
    assert exported == {a["billing_ref"] for a in built["accounts"]}
