from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.inventory.locations import (
    AVAILABILITY_RULE,
    buffer_total_mbps,
    get_location,
    list_locations,
)

router = APIRouter(tags=["capacity"])


@router.get("/capacity/locations")
def get_locations(
    requested_mbps: int = Query(default=0, ge=0),
    market_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    locations = list_locations(requested_mbps=requested_mbps, market_id=market_id, search=search)
    return {
        "rule": AVAILABILITY_RULE,
        "requested_mbps": requested_mbps,
        "count": len(locations),
        "serviceable_count": sum(1 for location in locations if location["can_support"]),
        "available_mbps": sum(location["available_mbps"] for location in locations),
        "maintenance_buffer_mbps": sum(
            location["maintenance_buffer_mbps"] for location in locations
        ),
        "locations": locations,
    }


@router.get("/capacity/locations/{location_code}")
def get_single_location(location_code: str, requested_mbps: int = Query(default=0, ge=0)):
    location = get_location(location_code, requested_mbps=requested_mbps)
    if location is None:
        raise HTTPException(status_code=404, detail="location not found")
    return location


@router.get("/capacity", response_class=HTMLResponse)
def capacity_check(requested_mbps: int = Query(default=350, ge=0)):
    locations = list_locations(requested_mbps=requested_mbps)
    markets = sorted({location["market_id"] for location in locations})
    market_options = "".join(f'<option value="{m}">{m}</option>' for m in markets)
    payload = "".join(
        _row(location, index) for index, location in enumerate(locations)
    )
    return _PAGE.format(
        rule=AVAILABILITY_RULE,
        requested=requested_mbps,
        market_options=market_options,
        rows=payload,
        location_count=len(locations),
        serviceable=sum(1 for location in locations if location["can_support"]),
        available=f"{sum(location['available_mbps'] for location in locations):,}",
        buffer_total=f"{buffer_total_mbps():,}",
    )


def _row(location: dict, index: int) -> str:
    verdict = "yes" if location["can_support"] else "no"
    verdict_label = "Serviceable" if location["can_support"] else "Not serviceable"
    return f"""
      <tr data-market="{location['market_id']}" data-available="{location['available_mbps']}"
          data-search="{location['customer_name'].lower()} {location['location_name'].lower()} {location['location_code'].lower()}"
          class="{'lead' if index == 0 else ''}">
        <td class="code">{location['location_code']}</td>
        <td class="customer">{location['customer_name']}</td>
        <td class="site">{location['location_name']}</td>
        <td><span class="chip">{location['market_id']}</span></td>
        <td class="num">{location['total_capacity_mbps']:,}</td>
        <td class="num">{location['allocated_mbps']:,}</td>
        <td class="num buffer">{location['maintenance_buffer_mbps']:,}</td>
        <td class="num available">
          {location['available_mbps']:,}
          <div class="calc">{location['total_capacity_mbps']:,} &minus; {location['allocated_mbps']:,} &minus; {location['maintenance_buffer_mbps']:,}</div>
        </td>
        <td class="num">
          {location['utilization_pct']}%
          <div class="meter"><span style="width:{min(location['utilization_pct'], 100)}%"></span></div>
        </td>
        <td><span class="verdict {verdict}">{verdict_label}</span></td>
      </tr>"""


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vantage · Capacity Check</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #f4f7fb;
    --card: #ffffff;
    --ink: #0f1b2d;
    --muted: #64748b;
    --line: #e6ecf4;
    --violet: #5b5bd6;
    --violet-soft: #eeeefc;
    --teal: #0d9488;
    --amber: #b45309;
    --amber-soft: #fef3c7;
    --ok: #0f766e;
    --no: #be123c;
    --no-soft: #ffe4e9;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: Inter, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--ink);
    font-size: 14px;
  }}
  header {{
    background: linear-gradient(120deg, #1e1b4b 0%, #4338ca 55%, #0d9488 100%);
    color: #fff;
    padding: 30px 44px 34px;
  }}
  .eyebrow {{ font-size: 11px; letter-spacing: .22em; text-transform: uppercase; opacity: .78; }}
  h1 {{ font-family: "Space Grotesk", Inter, sans-serif; font-size: 30px; margin: 10px 0 8px; font-weight: 700; }}
  header p {{ margin: 0; max-width: 660px; line-height: 1.6; opacity: .9; }}
  main {{ padding: 0 44px 64px; margin-top: -20px; }}
  .panel {{
    background: var(--card);
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(15,27,45,.08);
    padding: 22px 26px;
    margin-bottom: 22px;
  }}
  th.avail-head {{ position: relative; cursor: help; }}
  th.avail-head .label {{ border-bottom: 1px dashed #a5b4fc; }}
  .tip {{
    position: absolute;
    right: 0;
    top: calc(100% + 10px);
    width: 330px;
    z-index: 5;
    display: none;
    text-align: left;
    text-transform: none;
    letter-spacing: 0;
    white-space: normal;
    background: var(--card);
    color: var(--ink);
    border-radius: 14px;
    box-shadow: 0 12px 34px rgba(15,27,45,.18);
    padding: 16px 18px;
  }}
  th.avail-head:hover .tip, th.avail-head:focus .tip {{ display: block; }}
  .tip h3 {{ font-family: "Space Grotesk", Inter, sans-serif; font-size: 14px; margin: 0 0 9px; }}
  .formula {{
    font-family: "Space Grotesk", Inter, sans-serif;
    font-size: 14px;
    font-weight: 600;
    background: var(--violet-soft);
    color: #3730a3;
    padding: 10px 13px;
    border-radius: 10px;
  }}
  .tip p {{ margin: 11px 0 0; color: var(--muted); line-height: 1.6; font-size: 13px; font-weight: 400; }}
  .buffer-pill {{
    background: var(--amber-soft);
    color: var(--amber);
    border-radius: 999px;
    padding: 8px 16px;
    font-weight: 600;
    white-space: nowrap;
  }}
  .controls {{ display: flex; gap: 18px; flex-wrap: wrap; align-items: flex-end; }}
  label {{ display: block; font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin-bottom: 7px; font-weight: 600; }}
  input, select {{
    font-family: inherit; font-size: 14px; padding: 10px 13px;
    border: 1px solid var(--line); border-radius: 10px; background: #fbfdff; color: var(--ink); min-width: 210px;
  }}
  input:focus, select:focus {{ outline: none; border-color: var(--violet); box-shadow: 0 0 0 3px var(--violet-soft); }}
  .tiles {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 22px; }}
  .tile {{ background: var(--card); border-radius: 14px; padding: 16px 20px; min-width: 178px; box-shadow: 0 4px 16px rgba(15,27,45,.06); }}
  .tile .v {{ font-family: "Space Grotesk", Inter, sans-serif; font-size: 26px; font-weight: 700; }}
  .tile .k {{ font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); margin-top: 4px; }}
  .tile.buffer .v {{ color: var(--amber); }}
  .table-wrap {{ background: var(--card); border-radius: 16px; box-shadow: 0 8px 30px rgba(15,27,45,.08); }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{
    text-align: left; font-size: 11px; letter-spacing: .08em; text-transform: uppercase;
    color: var(--muted); padding: 14px 16px; background: #f8fafc; border-bottom: 1px solid var(--line); white-space: nowrap;
  }}
  thead th:first-child {{ border-top-left-radius: 16px; }}
  thead th:last-child {{ border-top-right-radius: 16px; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  th.num, td.num {{ text-align: right; }}
  th.buffer, td.buffer {{ background: #fffbeb; }}
  tbody td {{ padding: 13px 16px; border-bottom: 1px solid #f1f5f9; }}
  tbody tr:hover td {{ background: #f7f9ff; }}
  tbody tr:hover td.buffer {{ background: #fef6e0; }}
  tr.lead td {{ box-shadow: inset 0 0 0 9999px rgba(91,91,214,.04); }}
  .code {{ font-weight: 600; color: var(--violet); }}
  .customer {{ font-weight: 600; }}
  .site {{ color: var(--muted); }}
  .chip {{ background: #f1f5f9; border-radius: 999px; padding: 4px 10px; font-size: 12px; color: #475569; }}
  td.buffer {{ color: var(--amber); font-weight: 600; }}
  .available {{ font-weight: 700; }}
  .calc {{ font-size: 11px; color: #94a3b8; font-weight: 400; margin-top: 3px; }}
  .meter {{ height: 5px; border-radius: 999px; background: #eef2f7; margin-top: 6px; }}
  .meter span {{ display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--teal), var(--violet)); }}
  .verdict {{ font-size: 12px; font-weight: 600; padding: 5px 11px; border-radius: 999px; white-space: nowrap; }}
  .verdict.yes {{ background: #ccfbf1; color: var(--ok); }}
  .verdict.no {{ background: var(--no-soft); color: var(--no); }}
  footer {{ color: var(--muted); margin-top: 20px; line-height: 1.6; }}
  code {{ background: #eef2f7; border-radius: 5px; padding: 1px 6px; }}
</style>
</head>
<body>
<header>
  <div class="eyebrow">Vantage Networks · Sales Engineering</div>
  <h1>Capacity Check</h1>
  <p>Check whether a customer location can carry the bandwidth being quoted. Availability
     excludes capacity Vantage holds back for maintenance windows, so what you see here is
     what is actually sellable today.</p>
</header>
<main>
  <section class="panel controls">
    <div>
      <label for="requested">Requested bandwidth (Mbps)</label>
      <input id="requested" type="number" min="0" step="50" value="{requested}">
    </div>
    <div>
      <label for="market">Market</label>
      <select id="market"><option value="">All markets</option>{market_options}</select>
    </div>
    <div>
      <label for="search">Search customer or location</label>
      <input id="search" type="search" placeholder="e.g. Beacon, Riverside, RIV-01">
    </div>
    <div class="buffer-pill">{buffer_total} Mbps held as maintenance buffer</div>
  </section>

  <div class="tiles">
    <div class="tile"><div class="v" id="tileLocations">{location_count}</div><div class="k">Locations</div></div>
    <div class="tile"><div class="v" id="tileServiceable">{serviceable}</div><div class="k">Serviceable</div></div>
    <div class="tile"><div class="v" id="tileAvailable">{available}</div><div class="k">Available Mbps</div></div>
    <div class="tile buffer"><div class="v">{buffer_total}</div><div class="k">Maintenance buffer</div></div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Location</th>
          <th>Customer</th>
          <th>Site</th>
          <th>Market</th>
          <th class="num">Total</th>
          <th class="num">Allocated</th>
          <th class="num buffer">Maint. buffer</th>
          <th class="num avail-head" tabindex="0">
            <span class="label">Available</span>
            <div class="tip">
              <h3>How availability is calculated</h3>
              <div class="formula">available = total &minus; allocated &minus; maintenance buffer</div>
              <p>The maintenance buffer is capacity reserved for planned work and failover
                 headroom. It is never offered to customers, so it is subtracted before we quote.</p>
            </div>
          </th>
          <th class="num">Utilization</th>
          <th>Verdict</th>
        </tr>
      </thead>
      <tbody id="rows">{rows}</tbody>
    </table>
  </div>
  <footer>
    Rule: <code>{rule}</code> · implemented in <code>app/inventory/capacity.py</code> ·
    data from <code>GET /capacity/locations</code> · figures in Mbps.
  </footer>
</main>
<script>
  var rows = Array.prototype.slice.call(document.querySelectorAll("#rows tr"));
  var requested = document.getElementById("requested");
  var market = document.getElementById("market");
  var search = document.getElementById("search");

  function apply() {{
    var need = parseInt(requested.value, 10) || 0;
    var mkt = market.value;
    var q = search.value.trim().toLowerCase();
    var shown = 0, serviceable = 0, available = 0;
    rows.forEach(function (row) {{
      var visible = (!mkt || row.dataset.market === mkt) &&
                    (!q || row.dataset.search.indexOf(q) !== -1);
      row.style.display = visible ? "" : "none";
      if (!visible) return;
      shown++;
      var avail = parseInt(row.dataset.available, 10);
      available += avail;
      var badge = row.querySelector(".verdict");
      var ok = avail >= need;
      if (ok) serviceable++;
      badge.className = "verdict " + (ok ? "yes" : "no");
      badge.textContent = ok ? "Serviceable" : "Not serviceable";
    }});
    document.getElementById("tileLocations").textContent = shown;
    document.getElementById("tileServiceable").textContent = serviceable;
    document.getElementById("tileAvailable").textContent = available.toLocaleString();
  }}

  [requested, market, search].forEach(function (el) {{
    el.addEventListener("input", apply);
    el.addEventListener("change", apply);
  }});
  apply();
</script>
</body>
</html>
"""
