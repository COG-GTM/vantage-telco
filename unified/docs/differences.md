# Differentiated logic

What each estate does, why it does it, and where the merged engine keeps the
difference. Everything below was read out of the two source repositories; the
"why" is the reasoning the original code and comments record.

Every difference is an option on `EstatePolicy` in `oss/policy.py`, chosen per
estate. Nothing is decided implicitly.

---

## Billing

### Rating — `RatingBasis`

| | Meridian | Vantage |
| --- | --- | --- |
| Basis | whole gigabytes, partial rounds up | exact megabytes |
| Rate | $10.00 / GB | $0.012 / MB |

Meridian's mediation only ever delivered whole-gigabyte buckets, so the rate
card was written per gigabyte and a partial gigabyte is billed as a whole one.
Vantage rates the mediated megabyte directly. On 1 MB of overage that is $10.00
against $0.01, so this rule dominates the variance report.

`oss/billing/rating.py`. The overage line is rounded to cents on both estates
before it reaches the subtotal.

### Proration — `ProrationBasis`

Meridian's billing month is always 30 days, whatever the calendar says; a
mid-cycle plan change splits on that fixed month. Vantage uses the real length
of the month. February is where they diverge most: a $300 plan is $10/day on
Meridian and $10.71/day on Vantage.

`oss/billing/proration.py`.

### Promo expiry — `PromoExpiry`

Meridian honours a promo credit only in the cycle it was issued in — the check
is a year/month comparison, so a promo issued on the 28th is worth one cycle
and a promo issued on the 1st is worth the same cycle. Vantage gives the credit
a 30-day life from the issue date, so a late-month promo carries into the next
cycle.

`oss/billing/promo.py`.

### Suspension credit — `SuspensionCredit`

Meridian bills a suspended line the full month and credits nothing; the
function exists and returns zero deliberately. Vantage credits the daily rate
for each suspended day, on the estate's own day count, so the same suspension
is free on one estate and a credit on the other.

`oss/billing/suspension.py`.

### Tax base — `TaxBase`

Both estates charge GST/HST on the amount **before** the loyalty credit: the
CRA treats the credit as goodwill and not a reduction of consideration, and
that part is settled.

The provincial component is where they differ. Meridian's finance team ruled
locally that PST and QST are assessed on what the customer actually pays, so
the loyalty credit comes off the base first. Vantage assesses PST/QST on the
invoiced amount, credit and all. On a BC invoice with a $100 credit that is a
$7.00 difference before anything else.

`oss/billing/tax.py`. Province rates (BC, AB, ON, QC) are identical on both
estates and are defined once.

### Loyalty credit stage — `LoyaltyStage`

Both live services take the loyalty credit off the subtotal, before tax. The
archived `java/vantage-report` module takes it off the **taxed** amount, which
makes the credit larger for the same percentage. That module still produces the
NOC report, so its ordering is preserved as the `vantage-report` estate rather
than being corrected into agreement.

`oss/billing/discounts.py`.

### Rounding and arithmetic — `Rounding`, `Arithmetic`

Meridian rounds every charge line to cents as it is produced and the total is
the sum of rounded lines. Vantage carries full precision and rounds once, at
the total.

Meridian's register is also a C++ **double** register, rounding with
`floor(x * 100 + 0.5) / 100`. On a half cent the binary value decides the
direction, and it does not always agree with rounding the decimal value:
`143.325` rounds down and `125.445` rounds up. Reproducing the legacy register
exactly needs the same arithmetic, so the Meridian policy evaluates rates and
rounding in binary64 and Vantage stays in decimal.

`oss/billing/money.py`. Without this, a handful of invoices per cycle land a
cent away from the legacy register — enough to fail reconciliation.

### Shared billing rules

Multi-line discounts (3–9 lines 5% off recurring, 10+ 10%) and late fees
(10-day grace after the due date, then 1.5% of the balance) are the same on
both estates and exist once, in `oss/billing/lines.py` and
`oss/billing/latefee.py`.

---

## Inventory

### Maintenance buffer

Meridian answers "what is left" with `total - allocated`; the dashboard says so
explicitly. Vantage also withholds the maintenance buffer, because capacity
reserved for a maintenance window is not sellable. Both estates carry the
buffer on the record; the policy decides whether it is subtracted. The sales
desk can get "yes" from one estate and "no" from the other on the same
location, which is the point of exposing which rule answered.

`oss/inventory/capacity.py`, `oss/inventory/locations.py`.

### Standby circuits

Meridian counts every circuit it owns as active, standby included — the fibre
is lit and it is on the books. Vantage counts only the roles carrying customer
traffic and excludes `STANDBY` and `FAILOVER`. Neither counts a circuit that is
not in `ACTIVE` lifecycle state.

`oss/inventory/circuits.py`.

---

## Network addressing

Not a divergence: both estates number the management plane out of
`10.20.0.0/16` with `10.20.250.0/24` held as the growth pool, and devices
flagged `external_bgp` must not be renumbered.

The difference is coverage. Meridian only ever reported on its assignment file,
while Vantage keeps generated artifacts (routing, firewall, DNS, monitoring)
and can find every config file referencing an address, plus references to
addresses no device owns. The merged engine runs the Vantage checks against
either estate's device list.

`oss/network/addressing.py`.

---

## Source formats

Meridian keeps one flat `.rec` file per account plus CSV telemetry exports;
Vantage keeps JSON collections mirroring its Mongo database. The adapters in
`oss/adapters/` normalise both into `oss/model.py`, so no rule above ever sees
a source format. Both books are carried in `data/` unchanged.

Mediated usage carrying no billing account is kept and never invoiced;
`Estate.unlinked_usage()` reports it.
