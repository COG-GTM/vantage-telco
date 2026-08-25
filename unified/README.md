# unified-telco-oss

Meridian and Vantage OSS merged into one codebase: a single billing, inventory
and addressing engine, and one **estate policy** per legacy estate that says
which rule the engine applies.

The two estates bill the same customer book by different rules, and both sets
of rules are in force. Merging them is therefore not a matter of picking a
winner — the engine has to be able to produce either answer, on demand, and say
which rule produced it.

```bash
pip install -r requirements.txt
make test                       # includes byte-for-byte parity with both legacy registers
make run                        # http://localhost:8000/docs
make parity PERIOD=2026-07      # where the two estates disagree, and why
```

## Layout

| Path | What it holds |
| --- | --- |
| `oss/policy.py` | Every rule the estates disagree on, as options; `MERIDIAN`, `VANTAGE`, `VANTAGE_REPORT` |
| `oss/billing/` | One implementation of each billing rule, reading the option off the policy |
| `oss/inventory/` | Capacity, circuit roll-ups, serviceable locations |
| `oss/network/` | Management addressing (`10.20.0.0/16`), config references, orphan checks |
| `oss/adapters/` | Meridian `.rec`/CSV and Vantage JSON normalised to `oss/model.py` |
| `oss/service.py` | An estate: its source book bound to its policy |
| `oss/api/main.py` | HTTP surface; every endpoint takes `?estate=` |
| `tools/parity.py` | Rates one book under two policies and attributes the variance |
| `data/` | The source books, carried over unchanged |

## The differences that were preserved

Full detail, with the reasoning each estate recorded, is in
[docs/differences.md](docs/differences.md).

| Rule | Meridian | Vantage |
| --- | --- | --- |
| Rating | whole GB, partial rounds up, $10/GB | exact MB, $0.012/MB |
| Proration | fixed 30-day month | calendar month |
| Promo expiry | end of the issuing cycle | 30 days from issue |
| Suspension | no credit, full month billed | daily rate for each suspended day |
| PST/QST base | after the loyalty credit | before it |
| Loyalty credit | off the subtotal | off the subtotal (archived report: after tax) |
| Rounding | every line, as a C++ double | once, at the total, in decimal |
| Maintenance buffer | sellable | withheld |
| Standby circuits | counted as active | excluded |

GST/HST is charged pre-discount on both estates, the multi-line schedule
(3–9 lines 5%, 10+ 10%) and the late fee (10-day grace, then 1.5%) are shared,
and both number the management plane the same way. Those rules exist once.

## Estates

- `meridian` — the legacy C++ register's rules over the Meridian book.
- `vantage` — the FastAPI service's rules over the Vantage book.
- `vantage-report` — the Vantage book rated the way the archived
  `java/vantage-report` module rates it, which takes the loyalty credit after
  tax. Kept as its own estate so the NOC report can be reproduced instead of
  quietly disagreeing with the service.

## Parity

`make parity` joins the two registers on `billing_ref` and prints each account
whose total disagrees, the rules implicated, and the variance by rule and by
province. It exits non-zero when anything disagrees, so it can be used as a
reconciliation gate.

## Tests

`tests/golden/` holds the output of the original systems — the C++
`bin/billing-run --json` and the Vantage `list_invoices()` — captured
unchanged. `tests/test_meridian_parity.py` and `tests/test_vantage_parity.py`
rate the whole book through the merged engine and require every charge line on
every account to match to the cent. The rule-level differences are pinned from
both sides in `tests/test_billing_rules.py`.
