"""
ParkSight · Parking-Induced Congestion Intelligence
Run:  streamlit run app.py     (after  python build_all.py)
"""
import sys, os, json, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from src.analytics import patrol_route, optimize_coverage
from src.assistant import answer as ask_parksight
from src.briefing import build_pdf
from src.routing import road_route
from src.config import (SEVERITY, DELAY_MIN_FULL_BLOCK, VALUE_OF_TIME_PER_HR, H3_RES,
                        CITY_CENTER, CITY_ZOOM, CITY_NAME, MAPPLS_TILE_URL, MAPPLS_REST_KEY,
                        MAPPLS_CLIENT_ID, MAPPLS_CLIENT_SECRET)
from src.mappls import get_token

OUT = Path(__file__).parent / "outputs"
st.set_page_config(page_title="ParkSight", layout="wide", page_icon="🅿️",
                   initial_sidebar_state="expanded")

# ── design tokens (professional LIGHT theme) ─────────────────────────────────
BG, PANEL, BORDER = "#f6f8fb", "#ffffff", "#e6eaf0"
INK, MUTE = "#1f2937", "#64748b"
SKY, GRN, AMB, RED, VIO = "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed"
PLOTBG = "rgba(0,0,0,0)"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@500;600&display=swap');
html,body,[class*="css"],.stApp{{font-family:'Inter',sans-serif;}}
.stApp{{background:{BG};color:{INK};}}
#MainMenu,footer,header{{visibility:hidden;}}
.block-container{{padding:1.0rem 1.4rem 2rem;max-width:1560px;}}
/* header */
.top{{display:flex;align-items:center;gap:13px;margin-bottom:2px;}}
.logo{{width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);
  display:flex;align-items:center;justify-content:center;font-weight:800;font-size:19px;color:#fff;
  box-shadow:0 4px 12px rgba(37,99,235,.28);}}
.title{{font-size:21px;font-weight:800;color:{INK};letter-spacing:.2px;}}
.title span{{color:{SKY};}}
.sub{{color:{MUTE};font-size:13px;margin:1px 0 14px 51px;}}
hr.sep{{border:0;border-top:1px solid {BORDER};margin:12px 0 16px;}}
/* kpi */
.kpi{{background:{PANEL};border:1px solid {BORDER};border-radius:12px;padding:14px 16px;height:100%;
  box-shadow:0 1px 3px rgba(16,24,40,.06);}}
.kpi .l{{color:{MUTE};font-size:10.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;}}
.kpi .v{{font-size:25px;font-weight:700;color:{INK};margin-top:5px;font-family:'Roboto Mono',monospace;}}
.kpi .s{{color:{MUTE};font-size:11.5px;margin-top:4px;}}
.kpi .dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle;}}
/* tabs */
.stTabs [data-baseweb="tab-list"]{{gap:2px;border-bottom:1px solid {BORDER};}}
.stTabs [data-baseweb="tab"]{{background:transparent;color:{MUTE};font-weight:600;font-size:13.5px;padding:9px 16px;}}
.stTabs [aria-selected="true"]{{color:{SKY}!important;border-bottom:2px solid {SKY}!important;}}
section[data-testid="stSidebar"]{{background:#0f1d35;border-right:1px solid #16233c;}}
section[data-testid="stSidebar"] *{{color:#dbe5f3!important;}}
section[data-testid="stSidebar"] div[data-baseweb="select"] *{{color:#1f2937!important;}}
section[data-testid="stSidebar"] [data-testid="stTooltipIcon"] svg,
section[data-testid="stSidebar"] label svg{{fill:#9fb2cf!important;color:#9fb2cf!important;}}
div[data-baseweb="popover"] li, div[data-baseweb="menu"] *{{color:#1f2937!important;}}
[data-testid="stSidebarCollapsedControl"]{{display:flex!important;visibility:visible!important;
  opacity:1!important;align-items:center!important;z-index:1000000!important;background:#2563eb!important;
  border-radius:10px!important;padding:5px 12px!important;cursor:pointer!important;
  box-shadow:0 3px 12px rgba(2,12,30,.40)!important;}}
[data-testid="stSidebarCollapsedControl"]:hover{{background:#1d4ed8!important;}}
[data-testid="stSidebarCollapsedControl"] svg{{fill:#ffffff!important;color:#ffffff!important;
  width:1.45rem!important;height:1.45rem!important;}}
[data-testid="stSidebarCollapsedControl"]::after{{content:"Open filters";color:#ffffff;font-weight:700;
  font-size:13px;margin-left:7px;white-space:nowrap;}}
section[data-testid="stSidebar"] .block-container{{padding-top:1.2rem;}}
.stDataFrame{{border:1px solid {BORDER};border-radius:10px;}}
h2,h3{{letter-spacing:.2px;font-weight:700;color:{INK};}}
.cap{{color:{MUTE};font-size:12.5px;margin:-4px 0 10px;}}
.badge{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600;
  background:{GRN}14;color:{GRN};border:1px solid {GRN}33;}}
.stButton>button, .stDownloadButton>button{{border-radius:9px;font-weight:600;}}
section[data-testid="stSidebar"] .stButton>button, section[data-testid="stSidebar"] .stDownloadButton>button{{
  background:#22304d!important;border:1px solid #33466b!important;}}
section[data-testid="stSidebar"] .stButton>button *, section[data-testid="stSidebar"] .stDownloadButton>button *,
section[data-testid="stSidebar"] .stButton>button p, section[data-testid="stSidebar"] .stDownloadButton>button p{{color:#eaf1fb!important;}}
section[data-testid="stSidebar"] .stButton>button:hover, section[data-testid="stSidebar"] .stDownloadButton>button:hover{{
  background:#2c3d61!important;border-color:#46608f!important;}}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    M = json.load(open(OUT / "metrics.json"))
    D = {f.stem: pd.read_csv(f) for f in OUT.glob("*.csv")}
    SLOT = pd.read_parquet(OUT / "slot_risk.parquet") if (OUT / "slot_risk.parquet").exists() else None
    GEO = json.load(open(OUT / "cells_hex.geojson")) if (OUT / "cells_hex.geojson").exists() else None
    return M, D, SLOT, GEO


if not (OUT / "metrics.json").exists():
    st.error("Run `python build_all.py` first."); st.stop()
M, D, SLOT, GEO = load()
# clean sequential palette for the impact choropleth on a LIGHT basemap (cream → orange → red)
IMPACT_SCALE = [[0.0, "#fff7ec"], [0.3, "#fdbb84"], [0.6, "#ef6548"], [1.0, "#990000"]]
cells, zones = D["cells"], D["zones"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def kpi(col, label, val, sub="", color=SKY):
    col.markdown(f"""<div class="kpi"><div class="l">{label}</div>
      <div class="v"><span class="dot" style="background:{color}"></span>{val}</div>
      <div class="s">{sub}</div></div>""", unsafe_allow_html=True)


ESRI_SAT = ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
            "MapServer/tile/{z}/{y}/{x}")
BASEMAPS = {"Mappls": "mappls", "Streets": "open-street-map",
            "Light": "carto-positron", "Satellite": "satellite"}
def _cred(name, fallback=""):
    """Read a credential from Streamlit Secrets (Cloud) -> env var -> config file (local)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name) or fallback


REST_KEY = _cred("MAPPLS_REST_KEY", MAPPLS_REST_KEY)
CID = _cred("MAPPLS_CLIENT_ID", MAPPLS_CLIENT_ID)
SEC = _cred("MAPPLS_CLIENT_SECRET", MAPPLS_CLIENT_SECRET)
MK = REST_KEY                                              # REST key for Mappls map tiles


@st.cache_data(ttl=3000, show_spinner=False)
def mappls_token(cid, sec):                               # OAuth token for routing (cached ~hourly)
    return get_token(cid, sec) or ""
ROUTE_TOK = mappls_token(CID, SEC)


def smap(fig, h=560, zoom=CITY_ZOOM, basemap="Light"):
    style = BASEMAPS.get(basemap, "carto-positron")
    mb = dict(center=dict(lat=CITY_CENTER[0], lon=CITY_CENTER[1]), zoom=zoom)
    if style == "mappls" and MK:        # MapmyIndia partner tiles
        mb["style"] = "white-bg"
        mb["layers"] = [dict(below="traces", sourcetype="raster", sourceattribution="MapmyIndia",
                             source=[MAPPLS_TILE_URL.replace("{key}", MK)], opacity=1.0)]
    elif style == "satellite":
        mb["style"] = "white-bg"
        mb["layers"] = [dict(below="traces", sourcetype="raster", sourceattribution="Esri",
                             source=[ESRI_SAT], opacity=1.0)]
    else:
        mb["style"] = "carto-positron" if style == "mappls" else style
    fig.update_layout(mapbox=mb, height=h, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=PLOTBG,
                      uirevision="keep", font=dict(color=INK),
                      legend=dict(bgcolor="rgba(255,255,255,.82)", bordercolor=BORDER,
                                  borderwidth=1, x=0.01, y=0.99, font=dict(color=INK)))
    return fig


def sfig(fig, h=350, title=""):
    fig.update_layout(template="plotly_white", height=h, paper_bgcolor=PLOTBG, plot_bgcolor=PLOTBG,
                      margin=dict(l=12, r=12, t=42 if title else 14, b=12), title=title,
                      font=dict(family="Inter", color=INK, size=12),
                      legend=dict(bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor=BORDER, zeroline=False)
    fig.update_yaxes(gridcolor=BORDER, zeroline=False)
    return fig


_NORM = mcolors.Normalize(0, 100)
try:                                  # matplotlib >= 3.6 (Streamlit Cloud)
    import matplotlib as _mpl
    _CMAP = _mpl.colormaps["YlOrRd"]
except Exception:                     # older matplotlib fallback
    _CMAP = cm.get_cmap("YlOrRd")
def cis_rgb(v):
    r, g, b, _ = _CMAP(_NORM(v)); return [int(r * 255), int(g * 255), int(b * 255)]


@st.cache_data
def make_pdf(n):
    ch = zones.sort_values("CIS", ascending=False).head(n)
    rt, _, _ = patrol_route(ch)
    return build_pdf(M, cells, zones, rt, D["ward_rollup"])


@st.cache_data(show_spinner=False)
def get_road(coords_tuple, key=""):
    return road_route(list(coords_tuple), key)


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="top"><div class="logo">P</div>'
                f'<div class="title">Park<span>Sight</span></div></div>'
                f'<div style="color:{MUTE};font-size:11px;letter-spacing:.18em;'
                f'text-transform:uppercase;margin:6px 0 2px 1px;">Command Center</div>',
                unsafe_allow_html=True)
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("**Filters**")
    stations = sorted(zones.police_station.dropna().unique().tolist())
    sel = st.multiselect("Police station", stations, default=[], placeholder="All stations",
                         help="Pick one or more stations · leave empty for the whole city")
    min_cis = st.slider("Minimum impact score", 0, 100, 0, 5)
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("**Deploy & Simulate**")
    n_units = st.slider("Patrol units", 1, min(40, len(zones)), 15)
    eff = st.slider("Enforcement effectiveness", 10, 60, 35, 5,
                    help="Assumed % reduction in violations at enforced zones") / 100.0
    st.caption("Allocates units to the highest-impact zones; coverage, route & ROI update live.")
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.markdown("**MapmyIndia (Mappls)**")
    if MK:
        st.caption("✅ Maps: **Mappls** tiles" + (" · Routing: **Mappls**" if ROUTE_TOK
                                                  else " · Routing: OSRM"))
    else:
        st.caption("Using OpenStreetMap / OSRM (no Mappls credentials)")
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    if "ward_rollup" in D:
        st.download_button("📄 Commander's briefing (PDF)", make_pdf(n_units),
                           "parksight_briefing.pdf", "application/pdf", use_container_width=True)
    st.caption(f"{M['rows_total']:,} violations · {M['days']} days · {CITY_NAME}")

fz = zones.copy()
if sel: fz = fz[fz.police_station.isin(sel)]
fz = fz[fz.CIS_100 >= min_cis].reset_index(drop=True)
if len(fz) == 0:                       # guard: never let filters empty the app mid-demo
    st.toast("No zones match the filters · showing all zones.")
    fz = zones.copy()
fc = cells if not sel else cells[cells.police_station.isin(sel)]
if len(fc) == 0:
    fc = cells
simz = fz.sort_values("CIS", ascending=False).reset_index(drop=True)
# constrained MAX-COVERAGE optimisation (submodular greedy) — spreads patrols to cover the
# most UNIQUE congestion impact, beating naive top-N ranking.
chosen, opt_stats = optimize_coverage(fz, n_units, radius_km=1.2)
chosen = chosen.reset_index(drop=True)
cov = opt_stats["opt_cov"]
routed, route_km, route_eta = patrol_route(chosen)
# ROI · "impact if you act": violations & ₹ averted by enforcing the chosen zones
_ann = 365.0 / max(M["days"], 1)
averted_viol = int(chosen.n_parking.sum() * eff * _ann)
averted_cost = (chosen.CIS.sum() / max(zones.CIS.sum(), 1e-9)) * M.get("cost", {}).get("annual_cost_inr", 0) * eff
# road-following patrol route (MapmyIndia token preferred, OSRM fallback)
road_geo, road_km, road_min, road_prov = get_road(tuple(map(tuple, routed[["lat", "lon"]].values)), ROUTE_TOK)
is_road = road_prov not in ("straight-line", "none")

# ── header + KPIs ───────────────────────────────────────────────────────────
st.markdown(f'<div class="top"><div class="logo">🅿</div>'
            f'<div class="title">ParkSight · <span>Parking-Induced Congestion Intelligence</span></div></div>'
            f'<div class="sub">Turns enforcement logs into a validated, deployable patrol plan · surfacing not '
            f'just today&apos;s hotspots, but <b>where enforcement is missing</b>, <b>where congestion is '
            f'emerging</b>, and <b>when</b> to act · cross-checked against independent congestion data.</div>',
            unsafe_allow_html=True)
st.markdown('<div class="cap" style="margin:-2px 0 8px">▶ <b>Live interactive demo</b> — give maps & the 3-D '
            'view a few seconds to render; if a panel looks blank, refresh once. Use the <b>sidebar</b> to scope '
            'by station and set patrol count.</div>', unsafe_allow_html=True)

ho, cost, v = M.get("holdout", {}), M.get("cost", {}), M.get("validation", {})
c = st.columns(6)
kpi(c[0], "Violations analysed", f"{M['rows_total']/1000:.0f}K", f"{M['days']} days", SKY)
kpi(c[1], "Hotspots / zones", f"{M['n_cells']:,} / {len(fz)}", f"{M['n_chronic_cells']} chronic", VIO)
kpi(c[2], "Deploy coverage", f"{cov}%", f"{n_units} units · {route_km} km route", GRN)
kpi(c[3], "Congestion cost", f"₹{cost.get('annual_cost_cr_low','?')}–{cost.get('annual_cost_cr_high','?')} cr",
    "illustrative range · per year", RED)
kpi(c[4], "Hotspot stability", f"{M['stability']['spatial_pearson']}",
    "violations recur · schedulable", AMB)
kpi(c[5], "Validation lift", f"{v.get('neighbourhood_lift','n/a')}×",
    f"{v.get('neighbourhood_events_top20pct_%','')}% congestion in worst areas", GRN)
st.markdown('<hr class="sep">', unsafe_allow_html=True)

st.markdown("##### 🔎 Ask ParkSight &nbsp;<span style='color:#64748b;font-weight:400;font-size:13px'>"
            "· ask in plain English</span>", unsafe_allow_html=True)
EXQ = ["Worst hotspots in Indiranagar", "Deploy Friday 6pm near Koramangala",
       "How much does congestion cost?", "Repeat offenders", "Hotspots near metro"]
if "askq" not in st.session_state:
    st.session_state.askq = ""
chips = st.columns(len(EXQ))
for i, eq in enumerate(EXQ):
    if chips[i].button(eq, key=f"ex{i}", use_container_width=True):
        st.session_state.askq = eq
q = st.text_input("q", key="askq", label_visibility="collapsed",
                  placeholder="e.g. Where should I deploy patrols on Saturday morning near Koramangala?")
if q:
    try:
        ans, res, focus = ask_parksight(q, cells, zones, SLOT, M)
    except Exception:
        ans, res, focus = ("I couldn't parse that · try a chip above.", pd.DataFrame(), None)
    ans_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ans)
    st.markdown(f"<div style='background:#eef4ff;border:1px solid #cfe0ff;border-left:4px solid {SKY};"
                f"border-radius:10px;padding:13px 16px;margin:8px 0 6px;color:{INK};font-size:15px;'>"
                f"<b style='color:{SKY}'>ParkSight</b> &nbsp;{ans_html}</div>", unsafe_allow_html=True)
    has_pts = len(res) and {"lat", "lon"} <= set(res.columns)
    if has_pts:
        ac = st.columns([1.15, 1])
        ac[0].dataframe(res.drop(columns=["lat", "lon"]), hide_index=True,
                        use_container_width=True, height=270)
        pts = res.reset_index(drop=True)
        fmap = go.Figure(go.Scattermapbox(
            lat=pts.lat, lon=pts.lon, mode="markers+text",
            marker=dict(size=22, color=SKY), text=[str(i + 1) for i in range(len(pts))],
            textfont=dict(color="#fff", size=11),
            hovertext=[str(x) for x in pts.iloc[:, 0]], hoverinfo="text"))
        smap(fmap, 270, zoom=11.4)
        ac[1].plotly_chart(fmap, use_container_width=True, config={"displayModeBar": False})
    elif len(res):
        st.dataframe(res, hide_index=True, use_container_width=True)
st.markdown('<hr class="sep">', unsafe_allow_html=True)

T = st.tabs(["Command Map", "Live Ops", "Priorities & Deploy", "Forecast", "Repeat Offenders",
             "Trends", "Coverage & Context", "Validation", "Method"])

# ── Command Map ─────────────────────────────────────────────────────────────
with T[0]:
    h = st.columns([1.9, 1.1, 0.9, 0.9, 0.9])
    h[0].subheader("Live congestion-impact map")
    _bopts = (["Mappls", "Light", "Streets", "Satellite"] if MK else ["Light", "Streets", "Satellite"])
    basemap = h[1].selectbox("Basemap", _bopts, index=0, label_visibility="collapsed")
    view3d = h[2].toggle("3D city", False)
    show_route = h[3].toggle("Route", True)
    show_poi = h[4].toggle("POI", False)
    def _draw_2d():
        fig = go.Figure()
        if GEO is not None:
            fig.add_trace(go.Choroplethmapbox(
                geojson=GEO, locations=fc.h3, z=fc.CIS, colorscale=IMPACT_SCALE, zmin=0, zmax=100,
                marker=dict(opacity=0.62, line=dict(width=0.25, color="rgba(60,72,90,0.18)")),
                colorbar=dict(title="Impact", x=0.985, len=0.78, thickness=12),
                text=fc.area, hovertemplate="%{text}<br>Impact %{z:.0f}<extra></extra>", name=""))
        else:
            fig.add_trace(go.Densitymapbox(lat=fc.lat, lon=fc.lon, z=fc.CIS, radius=16,
                                           colorscale="Inferno", opacity=0.5))
        if len(chosen):
            fig.add_trace(go.Scattermapbox(lat=chosen.lat, lon=chosen.lon, mode="markers",
                marker=dict(size=11, color=GRN, opacity=0.95),
                text=[f"#{r.zone_rank} {r.name}<br>CIS {r.CIS_100}/100 · {r.n_parking} viol.<br>PATROL ASSIGNED"
                      for r in chosen.itertuples()], hoverinfo="text", name="patrol zones"))
        if show_route and len(road_geo) > 1:
            fig.add_trace(go.Scattermapbox(lat=road_geo.lat, lon=road_geo.lon, mode="lines",
                line=dict(width=3.2, color="#1d4ed8"),
                name=f"route · {road_km} km" + (f" via {road_prov}" if is_road else ""), hoverinfo="skip"))
        if show_poi and "poi" in D and len(D["poi"]):
            poi = D["poi"]
            fig.add_trace(go.Scattermapbox(lat=poi.lat, lon=poi.lon, mode="markers",
                marker=dict(size=7, color=VIO, opacity=0.8),
                text=poi.kind + " · " + poi.name.fillna(""), hoverinfo="text", name="metro/markets"))
        smap(fig, 600, basemap=basemap)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": False})
        st.markdown(f'<div class="cap">Hexagons = Congestion-Impact (≈150 m cells) · green pins = patrol-assigned '
                    f'zones · blue line = {"road-following" if is_road else "optimised"} patrol route '
                    f'({road_km} km). Switch <b>Basemap</b> to Streets/Satellite, or toggle <b>3D city</b>.</div>',
                    unsafe_allow_html=True)

    if view3d:
        try:
            d3 = fc.copy()
            rgbs = d3.CIS.map(cis_rgb)
            d3["r"] = [c[0] for c in rgbs]; d3["g"] = [c[1] for c in rgbs]; d3["b"] = [c[2] for c in rgbs]
            layers = [pdk.Layer("H3HexagonLayer", d3[["h3", "CIS", "area", "r", "g", "b"]],
                                get_hexagon="h3", get_fill_color="[r, g, b]", get_elevation="CIS",
                                elevation_scale=24, extruded=True, opacity=0.86, coverage=0.92, pickable=True)]
            if len(chosen):
                layers.append(pdk.Layer("ColumnLayer", chosen[["lat", "lon"]],
                                        get_position="[lon, lat]", get_elevation=2600, radius=70,
                                        get_fill_color="[52, 211, 153, 200]", elevation_scale=1))
            view = pdk.ViewState(latitude=CITY_CENTER[0], longitude=CITY_CENTER[1], zoom=10.4, pitch=55, bearing=18)
            st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view, map_provider="carto",
                            map_style="light_no_labels", tooltip={"text": "{area}\nImpact {CIS}"}),
                            use_container_width=True)
            st.markdown('<div class="cap">3D column height & colour = Congestion-Impact per ≈150 m hexagon · '
                        'green pillars = patrol-assigned zones. Drag to rotate, scroll to zoom.</div>',
                        unsafe_allow_html=True)
        except Exception:
            st.info("3-D view couldn't initialise in this browser (WebGL / deck.gl). Showing the 2-D impact "
                    "map instead — untoggle **3D city** to dismiss.")
            _draw_2d()
    else:
        _draw_2d()

# ── Live Ops (Right Now) ────────────────────────────────────────────────────
with T[1]:
    st.subheader("Right now · where to deploy this hour")
    now = pd.Timestamp.now(tz="Asia/Kolkata")
    sc = st.columns([1, 1, 2])
    day = sc[0].selectbox("Day", DAYS, index=int(now.dayofweek))
    hour = sc[1].slider("Hour (IST)", 0, 23, int(now.hour))
    di = DAYS.index(day)
    if SLOT is not None:
        ns = SLOT[(SLOT.dow == di) & (SLOT.hour == hour)].sort_values("risk", ascending=False)
        ns = ns.merge(cells[["h3", "area", "police_station"]], on="h3", how="left")
        top = ns.head(12)
        k = st.columns(3)
        kpi(k[0], "Predicted violations / hr", f"{ns.risk.sum():.0f}", f"{day} {hour:02d}:00 city-wide", AMB)
        kpi(k[1], "Active hotspots this hour", f"{int((ns.risk >= 0.5).sum())}", "risk ≥ 0.5", RED)
        kpi(k[2], "Top zone right now", f"{top.area.iloc[0] if len(top) else 'n/a'}",
            f"risk {top.risk.iloc[0]:.1f}" if len(top) else "", GRN)
        a, b = st.columns([1.15, 1])
        with a:
            fig = go.Figure(go.Scattermapbox(lat=top.lat, lon=top.lon, mode="markers+text",
                marker=dict(size=10 + 16 * (top.risk / max(top.risk.max(), 1e-9)), color=RED, opacity=0.9),
                text=[str(i + 1) for i in range(len(top))], textfont=dict(color="#fff", size=11),
                hovertext=[f"{r.area}<br>risk {r.risk:.1f}" for r in top.itertuples()], hoverinfo="text"))
            smap(fig, 460, zoom=11)
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": False})
        with b:
            disp = top[["area", "police_station", "risk"]].copy()
            disp.insert(0, "rank", range(1, len(disp) + 1))
            disp["risk"] = disp.risk.round(1)
            st.dataframe(disp.rename(columns={"area": "Area", "police_station": "Station",
                         "risk": "Pred. viol."}), hide_index=True, use_container_width=True, height=420)
            st.download_button("⬇ Download this-hour deployment plan",
                               disp.to_csv(index=False).encode(), f"parksight_now_{day}_{hour:02d}h.csv",
                               "text/csv", use_container_width=True)
    st.markdown('<div class="cap">Pick the current day & hour · the model surfaces the highest-risk zones to '
                'pre-position patrols <b>this hour</b>, turning the forecast into a live deployment order.</div>',
                unsafe_allow_html=True)

# ── Priorities & Deploy ─────────────────────────────────────────────────────
with T[2]:
    a, b = st.columns([1.15, 1])
    with a:
        st.subheader("Top enforcement zones")
        st.dataframe(fz.head(25)[["zone_rank", "name", "CIS_100", "n_parking", "persistence",
                                  "top_violation", "police_station"]].rename(columns={
            "zone_rank": "#", "CIS_100": "Impact", "n_parking": "Viol.", "persistence": "Chronicity",
            "top_violation": "Dominant", "police_station": "Station"}),
            hide_index=True, use_container_width=True, height=430)
    with b:
        st.subheader("Deployment outcome")
        d = st.columns(2)
        kpi(d[0], "Impact covered", f"{cov}%", f"{n_units} units · optimised placement", GRN)
        kpi(d[1], "Route / ETA", f"{road_km} km", f"~{road_min:.0f} min · {road_prov}", SKY)
        d2 = st.columns(2)
        kpi(d2[0], "Violations averted / yr", f"{averted_viol/1000:.1f}K",
            f"at {int(eff*100)}% effectiveness", VIO)
        kpi(d2[1], "Cost averted / yr", f"₹{averted_cost/1e7:.2f} cr",
            f"₹{averted_cost/1e5:.0f} lakh", RED)
        # optimisation gain: max-coverage vs naive top-N ranking
        fig = go.Figure(go.Bar(
            x=["Optimised (max-coverage)", "Naive top-N ranking"],
            y=[opt_stats["opt_cov"], opt_stats["naive_cov"]],
            marker_color=[GRN, MUTE], text=[f"{opt_stats['opt_cov']}%", f"{opt_stats['naive_cov']}%"],
            textposition="outside"))
        sfig(fig, 300, f"Patrol optimisation · same {n_units} units, more impact covered")
        fig.update_yaxes(title="% of congestion impact covered", range=[0, 105])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<span class="badge">Max-coverage optimiser covers <b>+{opt_stats["uplift_pp"]} '
                    f'percentage points</b> more impact than ranking by score — same patrol budget</span>',
                    unsafe_allow_html=True)
    st.success(f"**Illustrative scenario** (adjust the effectiveness slider): if sustained presence at these "
               f"zones cut violations by **{int(eff*100)}%**, deploying **{n_units} units** would avert "
               f"≈ **{averted_viol:,} violations/yr** and **₹{averted_cost/1e5:.0f} lakh/yr**, covering **{cov}%** "
               f"of impact. A *what-if*, not a guarantee · our own data shows individual repeat-offenders are "
               f"weakly deterred, so this depends on *consistent* presence.")
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.subheader(f"Optimised patrol route · {n_units} units · {road_km} km{' by road' if is_road else ''}")
    pl = routed[["stop", "name", "CIS_100", "n_parking", "top_violation", "police_station"]].copy()
    pl["cum_impact_%"] = (100 * routed.CIS.cumsum() / fz.CIS.sum()).round(1).values
    st.dataframe(pl.rename(columns={"stop": "Stop", "name": "Zone", "CIS_100": "Impact",
                 "n_parking": "Viol.", "top_violation": "Dominant", "police_station": "Station"}),
                 hide_index=True, use_container_width=True)

    st.download_button("⬇ Download patrol route (CSV)", pl.to_csv(index=False).encode(),
                       f"parksight_patrol_{n_units}units.csv", "text/csv")
    if "ward_rollup" in D:
        st.markdown('<hr class="sep">', unsafe_allow_html=True)
        st.subheader("Command roll-up · recommended units by police station")
        wr = D["ward_rollup"]
        a, b = st.columns([1, 1])
        with a:
            fig = go.Figure(go.Bar(x=wr.head(12).recommended_units[::-1],
                                   y=wr.head(12).police_station[::-1], orientation="h",
                                   marker_color=SKY, text=wr.head(12).recommended_units[::-1],
                                   textposition="outside"))
            sfig(fig, 360, "Recommended patrol units (top 12 stations)")
            fig.update_xaxes(title="units")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with b:
            st.dataframe(wr.head(15).rename(columns={"rank": "#", "police_station": "Station",
                         "impact_share_%": "Impact %", "violations": "Viol.", "hotspots": "Hotspots",
                         "chronic": "Chronic", "recommended_units": "Units"}),
                         hide_index=True, use_container_width=True, height=360)
        st.download_button("⬇ Download station allocation plan (CSV)", wr.to_csv(index=False).encode(),
                           "parksight_station_allocation.csv", "text/csv")
    if "area_hourly" in D and "area_vehicles" in D:
        st.markdown('<hr class="sep">', unsafe_allow_html=True)
        st.subheader("🔍 Zone drill-down")
        ah, av = D["area_hourly"], D["area_vehicles"]
        areas = sorted(ah.area.dropna().astype(str).unique())
        sela = st.selectbox("Select an area / hotspot", areas, key="drill")
        dc = st.columns([1.3, 1])
        with dc[0]:
            hh = ah[ah.area == sela].sort_values("hour")
            fig = go.Figure(go.Bar(x=hh.hour, y=hh.n, marker_color=SKY))
            sfig(fig, 300, f"{sela} · violations by hour"); fig.update_xaxes(title="Hour (IST)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with dc[1]:
            vv = av[av.area == sela].sort_values("n", ascending=False).head(8)[::-1]
            fig2 = go.Figure(go.Bar(x=vv.n, y=vv.vehicle_type.astype(str), orientation="h", marker_color=VIO))
            sfig(fig2, 300, "Vehicle mix")
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ── Forecast ────────────────────────────────────────────────────────────────
with T[3]:
    st.subheader("Predicted risk surface · when & where violations are detected")
    st.markdown('<div class="cap">Note: this is built from <b>enforcement records</b>, so the temporal '
                'pattern reflects <b>when patrols detect</b> violations (officer shifts), not raw demand. '
                'It is the right signal for scheduling <b>detection effort</b>; absolute demand at unpatrolled '
                'hours is unobserved.</div>', unsafe_allow_html=True)
    if SLOT is not None:
        piv = SLOT.pivot_table(index="dow", columns="hour", values="risk", aggfunc="sum").reindex(range(7))
        fig = go.Figure(go.Heatmap(z=piv.values, x=list(piv.columns), y=DAYS, colorscale="Inferno",
                                   colorbar=dict(title="risk")))
        sfig(fig, 330, "Predicted violations · day × hour"); fig.update_xaxes(title="Hour (IST)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    f = M["forecast"]
    cc = st.columns(5)
    kpi(cc[0], "Explanatory R² (CV)", f["cv_r2"], f["ensemble"], SKY)
    kpi(cc[1], "Future · where", ho.get("holdout_r2_spatial", "n/a"),
        f"naïve baseline {ho.get('persistence_r2_spatial','?')}", GRN)
    kpi(cc[2], "Future · where+hour", ho.get("holdout_r2_cellhour", "n/a"),
        f"naïve baseline {ho.get('persistence_r2_cellhour','?')}", VIO)
    kpi(cc[3], "Interval coverage", f"{int(100*M.get('pi_coverage_80',0))}%", "80% band hit-rate", AMB)
    kpi(cc[4], "Hotspot stability", M["stability"]["spatial_pearson"], "week-to-week", SKY)
    st.markdown(f'<div class="cap">Honest evaluation: trained on the earliest 16 weeks, scored on the last 8 '
                f'<b>unseen</b> weeks. Much of the spatial signal is persistence (busy stays busy) · a naïve '
                f'"same as last month" baseline already reaches R² {ho.get("persistence_r2_cellhour","?")} at '
                f'location×hour; the model adds most where patterns <b>change</b> (emerging/declining cells). '
                f'Each prediction carries an 80% confidence band.</div>', unsafe_allow_html=True)
    _hc, _pc = ho.get("holdout_r2_cellhour", 0), ho.get("persistence_r2_cellhour", 0)
    _hs, _ps = ho.get("holdout_r2_spatial", 0), ho.get("persistence_r2_spatial", 0)
    _em = M.get("emerging", {})
    st.markdown(
        f"<div style='background:#ecfdf5;border:1px solid #a7f3d0;border-left:4px solid {GRN};"
        f"border-radius:10px;padding:12px 16px;margin:6px 0 10px;color:{INK};font-size:14px;line-height:1.55'>"
        f"<b style='color:{GRN}'>What the forecast adds over a “same-as-last-month” baseline</b><br>"
        f"• <b>Beats persistence on the hard metric</b> — location×hour R² <b>{_hc}</b> vs {_pc} "
        f"(+{_hc-_pc:.3f}); spatial <b>{_hs}</b> vs {_ps} (+{_hs-_ps:.3f}).<br>"
        f"• <b>Hour-level resolution persistence can’t give</b> — last-month is one number per cell; the model "
        f"predicts every day×hour, exactly what shift scheduling needs.<br>"
        f"• <b>Per-prediction 80% confidence bands</b> ({int(100*M.get('pi_coverage_80',0))}% empirical "
        f"coverage) — a naïve copy offers no uncertainty at all.<br>"
        f"• <b>Anticipates change</b> — flags {_em.get('n_emerging','—')} emerging cells "
        f"(fastest +{_em.get('top_growth_x','—')}×, {_em.get('top_area','')}) a last-month copy can’t see."
        f"</div>", unsafe_allow_html=True)
    st.subheader("Recommended proactive patrol windows (with confidence band)")
    sch = D["schedule"].head(40).copy()
    cols = ["day", "window", "risk"] + [c for c in ["risk_low", "risk_high"] if c in sch.columns] + ["lat", "lon"]
    st.dataframe(sch[cols].rename(columns={"risk": "predicted", "risk_low": "low (P10)",
                 "risk_high": "high (P90)"}), hide_index=True, use_container_width=True, height=320)

# ── Repeat Offenders ────────────────────────────────────────────────────────
with T[4]:
    o = M["offenders"]
    cc = st.columns(4)
    kpi(cc[0], "Unique vehicles", f"{o['n_vehicles']/1000:.0f}K", "", SKY)
    kpi(cc[1], "Repeat offenders", f"{o['repeat_share_%']}%", "caught ≥ 2×", AMB)
    kpi(cc[2], "Their share of viol.", f"{o['vio_from_repeat_%']}%", "of all violations", RED)
    kpi(cc[3], "Worst single vehicle", f"{o['max_by_one_vehicle']}×", "violations", RED)
    a, b = st.columns(2)
    with a:
        par = D["offenders_pareto"]
        fig = go.Figure(go.Scatter(x=100*par.veh_frac, y=100*par.vio_cov, line=dict(color=RED, width=3),
                                   fill="tozeroy", fillcolor="rgba(251,113,133,.12)"))
        sfig(fig, 360, f"Offender concentration · top 5% of vehicles = {o['share_top5pct']}% of violations")
        fig.update_xaxes(title="% of vehicles (worst first)"); fig.update_yaxes(title="% of violations")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with b:
        st.markdown("**Top chronic offenders** (anonymised)")
        st.dataframe(D["offenders_top"].rename(columns={"vehicle_number": "Vehicle", "violations": "Viol.",
                     "vehicle_type": "Type", "top_violation": "Dominant", "police_station": "Station",
                     "days_active": "Days"}), hide_index=True, use_container_width=True, height=345)
    dt = M.get("deterrence", {})
    if dt:
        msg = ("limited" if not dt.get("deters") else "some")
        st.markdown(f'<div class="cap">Deterrence check: habitual vehicles are re-caught after a median of '
                    f'{dt.get("median_gap_late_days","?")} days (vs {dt.get("median_gap_early_days","?")} '
                    f'early) → <b>{msg} deterrent effect</b> from current enforcement → case for targeted '
                    f'escalation.</div>', unsafe_allow_html=True)

# ── Trends (post-enforcement loop + emerging) ───────────────────────────────
with T[5]:
    tr = M.get("trends", {})
    st.subheader("Post-enforcement learning loop")
    cc = st.columns(3)
    kpi(cc[0], "Improving hotspots", tr.get("improving", "n/a"), "violations declining", GRN)
    kpi(cc[1], "Worsening hotspots", tr.get("worsening", "n/a"), "need intervention", RED)
    kpi(cc[2], "Emerging (early-warning)", M.get("emerging", {}).get("n_emerging", "n/a"),
        "rising before chronic", AMB)
    if "city_trend" in D:
        ct = D["city_trend"]
        fig = go.Figure(go.Scatter(x=ct.month, y=ct.violations, mode="lines+markers",
                                   line=dict(color=SKY, width=3), fill="tozeroy",
                                   fillcolor="rgba(56,189,248,.12)"))
        sfig(fig, 280, "City-wide monthly parking violations (full months)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    if "cells_monthly" in D:
        st.markdown("**Hotspot evolution · monthly time-lapse** ▶")
        cmF = D["cells_monthly"].sort_values("month")
        figT = px.scatter_mapbox(cmF, lat="lat", lon="lon", size="n", color="n",
            color_continuous_scale="Inferno", animation_frame="month", size_max=17,
            hover_name="area", range_color=(0, cmF.n.quantile(0.97)))
        smap(figT, 460)
        figT.update_layout(coloraxis_colorbar=dict(title="viol.", x=0.985, len=0.78, thickness=12))
        st.plotly_chart(figT, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="cap">Press ▶ to watch illegal-parking hotspots evolve month by month.</div>',
                    unsafe_allow_html=True)
    a, b = st.columns(2)
    if "zone_trends" in D:
        zt = D["zone_trends"].dropna(subset=["pct_per_month"])
        with a:
            st.markdown("**Worsening zones** (rising)")
            w = zt.sort_values("pct_per_month", ascending=False).head(12)
            st.dataframe(w[["area", "pct_per_month", "CIS", "police_station"]].rename(columns={
                "area": "Area", "pct_per_month": "%/month", "police_station": "Station"}),
                hide_index=True, use_container_width=True, height=300)
        with b:
            st.markdown("**Improving zones** (declining)")
            im = zt.sort_values("pct_per_month").head(12)
            st.dataframe(im[["area", "pct_per_month", "CIS", "police_station"]].rename(columns={
                "area": "Area", "pct_per_month": "%/month", "police_station": "Station"}),
                hide_index=True, use_container_width=True, height=300)
    st.markdown('<div class="cap">ParkSight re-computes impact every month, so any enforcement action can be '
                '<b>measured</b> · the post-event learning loop the brief calls for.</div>', unsafe_allow_html=True)

# ── Coverage & Context ──────────────────────────────────────────────────────
with T[6]:
    st.subheader("Under-enforced hotspots · high impact, low patrol effort")
    cg, gp = M.get("coverage", {}), D.get("coverage_gap", pd.DataFrame())
    cc = st.columns(3)
    kpi(cc[0], "Under-enforced zones", cg.get("n_under_enforced", "n/a"), "high impact, low effort", RED)
    kpi(cc[1], "Demand–effort corr.", cg.get("corr_demand_effort", "n/a"), "1 = perfectly matched", SKY)
    poi = M.get("poi", {})
    kpi(cc[2], "Top zones near POI", f"{poi.get('pct_top_near_poi','n/a')}%",
        f"within {poi.get('radius_m','')}m of metro/market/mall", AMB)
    if len(gp):
        fig = px.scatter(gp, x="enf_days", y="CIS", size="n_parking", color="gap",
                         color_continuous_scale="Reds", hover_name="area")
        sfig(fig, 340); fig.update_xaxes(title="Enforcement days"); fig.update_yaxes(title="Congestion impact")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    # #2 enforcement-bias corrected impact
    if "demand_adjusted" in D:
        st.markdown('<hr class="sep">', unsafe_allow_html=True)
        st.subheader("Enforcement-bias correction · estimated true demand")
        da = D["demand_adjusted"]
        m1, m2 = st.columns([1, 1.3])
        with m1:
            kpi(st.container(), "Avg hidden uplift", f"{da['hidden_uplift_%'].mean():.0f}%",
                "where patrols rarely go", VIO)
            st.markdown('<div class="cap">This is <b>caught</b>-violation data. Cells with little enforcement '
                        'under-count true violations, so we inflate their impact by how rarely they are patrolled '
                        '(CIS_adj). The biggest jumps are likely <b>hidden</b> hotspots.</div>',
                        unsafe_allow_html=True)
        with m2:
            up = da.sort_values("hidden_uplift_%", ascending=False).head(10)
            st.dataframe(up[["area", "CIS", "CIS_adj", "hidden_uplift_%", "enf_days", "police_station"]].rename(
                columns={"area": "Area", "CIS_adj": "CIS (adj)", "hidden_uplift_%": "Uplift %",
                         "enf_days": "Enf. days", "police_station": "Station"}),
                hide_index=True, use_container_width=True, height=300)
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.subheader("Commercial / transit context (OpenStreetMap)")
    if poi.get("available"):
        bd = poi.get("poi_breakdown", {})
        st.markdown(" · ".join([f'<span class="badge">{k}: {n}</span>' for k, n in bd.items()]),
                    unsafe_allow_html=True)
        if "poi_zones" in D:
            st.dataframe(D["poi_zones"].rename(columns={"zone_rank": "#", "name": "Zone",
                         "CIS_100": "Impact", "near_poi": "Nearest POI", "near_m": "Dist (m)",
                         "police_station": "Station"}), hide_index=True, use_container_width=True, height=300)
        st.markdown(f'<div class="cap"><b>{poi["pct_top_near_poi"]}%</b> of top hotspots lie within '
                    f'{poi["radius_m"]} m of a metro station, market or mall · confirming parking congestion '
                    f'concentrates around commercial & transit nodes, exactly as the brief describes.</div>',
                    unsafe_allow_html=True)

# ── Validation ──────────────────────────────────────────────────────────────
with T[7]:
    st.subheader("Independent validation · does the Impact Score track REAL congestion?")
    if v.get("available"):
        cc = st.columns(3)
        kpi(cc[0], "Corr. w/ congestion", v["neighbourhood_pearson_res6"], "neighbourhood level", GRN)
        kpi(cc[1], "Congestion in worst 20%", f"{v['neighbourhood_events_top20pct_%']}%", "of areas", AMB)
        kpi(cc[2], "Lift vs random", f"{v['neighbourhood_lift']}×", "", GRN)
        dec = v["decile_event_counts"]; xs = list(range(1, 11))
        ys = [dec.get(str(i), dec.get(i, 0)) for i in xs]
        fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=SKY))
        sfig(fig, 340, "Independent congestion/accident events by Impact-Score decile")
        fig.update_xaxes(title="Impact decile (10 = worst parking)"); fig.update_yaxes(title="events")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown(f'<div class="cap">Cross-checked against <b>{v["n_congestion_accident"]}</b> independent '
                    f'congestion/accident reports: the areas we flag as worst-parking contain '
                    f'<b>{v["neighbourhood_events_top20pct_%"]}%</b> of them · '
                    f'<b>{v["neighbourhood_lift"]}× more than chance.</b></div>', unsafe_allow_html=True)
        st.markdown('<hr class="sep">', unsafe_allow_html=True)
        st.markdown("**Is it just busy-area confounding?** (controlled check)")
        cc2 = st.columns(3)
        kpi(cc2[0], "Corr · hotspot density", v.get("corr_volume_only", "n/a"), "violation volume vs congestion", SKY)
        kpi(cc2[1], "Corr · Impact Score", v.get("corr_CIS", "n/a"), "severity-weighted vs congestion", SKY)
        kpi(cc2[2], "Partial (CIS | volume)", v.get("partial_corr_CIS_given_volume", "n/a"),
            "severity's add beyond volume", MUTE)
        tp = v.get("topzone_precision", {})
        prec = f"{tp.get('precision_%','n/a')}%" if tp.get("available") else "n/a"
        st.markdown(f'<div class="cap"><b>What the control reveals (honestly):</b> the strong validation is driven by '
                    f'parking-hotspot <b>density</b> (corr {v.get("corr_volume_only","?")}). Once we control for volume, '
                    f'severity weighting adds <b>no</b> congestion-predictive power (partial corr '
                    f'{v.get("partial_corr_CIS_given_volume","?")}). So severity is a <b>domain-driven enforcement-triage</b> '
                    f'layer (a main-road block obstructs more than a footpath one) — not a congestion predictor. '
                    f'Quasi-precision: <b>{prec}</b> of top-{tp.get("top_n","")} zones have an independent congestion '
                    f'event within {tp.get("radius_m","")} m. <i>Associational, not causal.</i></div>',
                    unsafe_allow_html=True)

# ── Method ──────────────────────────────────────────────────────────────────
with T[8]:
    st.markdown(f"""
### How ParkSight works
1. **Ingest & clean** {M['rows_total']:,} geo-tagged parking-violation records ({M['days']} days, Bengaluru).
2. **Severity model** · each violation type weighted by carriageway/intersection blocking.
3. **Hotspots** · H3 ~150 m cells → DBSCAN enforcement **zones**.
4. **Congestion-Impact Score** = volume × severity × chronicity × peak-overlap.
5. **Forecast** · HistGB + LightGBM ensemble over (location × day × hour); honest temporal hold-out.
6. **Analytics** · repeat-offenders, emerging hotspots, coverage-gap, post-enforcement trends.
7. **Deploy & Simulate** · **max-coverage optimisation** (submodular greedy) places patrols to cover the
   most *unique* impact, then routes them on MapmyIndia roads · congestion cost (₹) + ROI.
8. **Validation** · independent congestion/accident event log + OpenStreetMap POI context.

**Partners & stack:** **MapmyIndia / Mappls** (maps + routing) · Bengaluru Traffic Police / ASTraM data ·
OpenStreetMap (fallback) · Python · pandas · H3 · scikit-learn · LightGBM · Plotly · pydeck · Streamlit.
""")
    cc = st.columns(2)
    with cc[0]:
        if "severity_calibrated" in D and len(D["severity_calibrated"]):
            st.markdown("**Severity weights** · expert-set, cross-checked against congestion data")
            sv = D["severity_calibrated"].head(12).rename(columns={
                "type": "Violation type", "prior": "Expert", "learned": "Data signal", "final": "Used"})
            st.dataframe(sv, hide_index=True, use_container_width=True, height=270)
            st.caption("Weights are domain-expert-set (how much each violation blocks the carriageway). The "
                       "controlled check (Validation tab) shows the congestion link is driven by hotspot density, "
                       "not severity — so severity is an enforcement-triage layer, not a congestion predictor.")
        else:
            st.markdown("**Severity weights** (congestion impact, 0–1)")
            sv = (pd.Series(SEVERITY).sort_values(ascending=False).head(12)
                  .rename_axis("Violation type").reset_index(name="Weight"))
            st.dataframe(sv, hide_index=True, use_container_width=True, height=300)
    with cc[1]:
        st.markdown("**Assumptions** (stated up-front)")
        st.markdown(f"""
- **Cost model:** {DELAY_MIN_FULL_BLOCK:.0f} vehicle-minutes of delay per full-block violation,
  valued at **₹{VALUE_OF_TIME_PER_HR:.0f}/vehicle-hour** (conservative urban-India value of time),
  annualised from the {M['days']}-day sample.
- **Enforcement effectiveness:** adjustable (default 35%) · shown as a slider, not hidden.
- **Spatial unit:** H3 resolution {H3_RES} (~150 m); zones = DBSCAN of adjacent hot cells.
- **Forecast:** scored on a true **temporal hold-out** (early weeks → unseen later weeks).
""")
        st.markdown("**Limitations & honest scope** (we know our own holes)")
        st.markdown("""
- **We proxy congestion, not measure it.** No live traffic-flow data was provided; CIS is an
  *evidence-based proxy*, validated against an independent congestion log.
- **Selection bias.** *Caught*-violation data, not all violations · surfaced via the
  enforcement-bias correction and independent validation.
- **Temporal = detections, not demand.** Hourly pattern reflects officer shifts; framed as
  *detection-risk*, not absolute demand.
- **Validation is associational, not causal** (busy-area confounding; partial correlation shown).
- **₹ cost & effectiveness are illustrative** · a range and a *what-if* slider, not promises.
- **Forecast ≈ persistence + edge** · value is the *system*, not raw R².
- **Privacy & equity.** IDs **anonymised**; apply targeting with equity safeguards.
- **Scope.** One city, ~5 months · pipeline is **config-driven** for any city.
""")
    with st.expander("Raw metrics (JSON)"):
        st.json(M, expanded=False)
