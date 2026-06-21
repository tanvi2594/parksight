"""Central configuration: paths, constants, and the congestion-impact severity model."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]   # repo root (portable: works on Windows & Linux/Cloud)


def _read(name):
    p = ROOT / name
    try:
        return p.read_text(encoding="utf-8").strip() if p.exists() else ""
    except Exception:
        return ""


# ---- MapmyIndia / Mappls (official Gridlock partner) -----------------------
# Mappls REST APIs (tiles, routing) authenticate with an OAuth access TOKEN minted
# from a client_id + client_secret — a lone static key cannot authenticate.
# Provide both (env vars, the untracked secret files, or the dashboard sidebar);
# otherwise ParkSight falls back to free OpenStreetMap / OSRM (no credit spent).
MAPPLS_CLIENT_ID = os.environ.get("MAPPLS_CLIENT_ID") or _read("secret_mappls.txt")
MAPPLS_CLIENT_SECRET = os.environ.get("MAPPLS_CLIENT_SECRET") or _read("secret_mappls_secret.txt")
MAPPLS_REST_KEY = os.environ.get("MAPPLS_REST_KEY") or _read("secret_mappls_key.txt")  # for map tiles
MAPPLS_TILE_URL = "https://apis.mappls.com/advancedmaps/v1/{key}/still_map/{z}/{x}/{y}.png"
MAPPLS_ROUTE_URL = ("https://apis.mappls.com/advancedmaps/v1/{key}/route_adv/driving/"
                    "{coords}?geometries=geojson&overview=full")
RAW_CSV = ROOT / "jan to may police violation_anonymized791b166.csv"
EVENTS_CSV = ROOT / "astram_event_data.csv"      # optional cross-validation dataset (Theme-2)
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

TZ = "Asia/Kolkata"
# ---- city profile (change these 4 lines to run ParkSight on any city) ----
CITY_NAME = "Bengaluru"
CITY_CENTER = (12.972, 77.594)     # map default center (lat, lon)
CITY_ZOOM = 10.7
H3_RES = 9          # ~150 m hexagons – street-block granularity
PEAK_HOURS = set(range(8, 12)) | {17, 18, 19}   # morning + evening rush (IST)

# ---------------------------------------------------------------------------
# CONGESTION-IMPACT severity weights (0-1): how much a violation type chokes the
# carriageway / intersection. Main-road & intersection blocking = highest impact;
# footpath / document offences barely affect traffic flow.
# ---------------------------------------------------------------------------
SEVERITY = {
    "PARKING IN A MAIN ROAD": 1.00,
    "PARKING NEAR ROAD CROSSING": 1.00,
    "PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS": 1.00,
    "DOUBLE PARKING": 0.95,
    "AGAINST ONE WAY/NO ENTRY": 0.90,
    "OBSTRUCTING DRIVER": 0.90,
    "PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC": 0.85,
    "PARKING OPPOSITE TO ANOTHER PARKED VEHICLE": 0.80,
    "WRONG PARKING": 0.70,
    "STOPING ON WHITE/STOP LINE": 0.65,
    "VIOLATING LANE DISIPLINE": 0.60,
    "NO PARKING": 0.60,
    "U TURN PROHIBITED": 0.55,
    "H T V PROHIBITED": 0.50,
    "PARKING OTHER THAN BUS STOP": 0.50,
    "CARRYING LENGHTY MATERIAL": 0.45,
    "PARKING ON FOOTPATH": 0.40,
    "JUMPING TRAFFIC SIGNAL": 0.30,
    # ---- document / equipment offences: ~no congestion impact ----
    "DEFECTIVE NUMBER PLATE": 0.05,
    "USING BLACK FILM/OTHER MATERIALS": 0.05,
    "DEMANDING EXCESS FARE": 0.05,
    "REFUSE TO GO FOR HIRE": 0.05,
    "WITHOUT SIDE MIRROR": 0.05,
    "FAIL TO USE SAFETY BELTS": 0.05,
    "RIDER NOT WEARING HELMET": 0.05,
    "2W/3W - USING MOBILE PHONE": 0.05,
    "OTHER - USING MOBILE PHONE": 0.05,
}
DEFAULT_SEVERITY = 0.50

# Bangalore bounding box (for sanity filtering)
LAT_MIN, LAT_MAX = 12.70, 13.40
LON_MIN, LON_MAX = 77.30, 77.90

# ---------------------------------------------------------------------------
# Congestion-cost model (transparent, stated assumptions). A blocking parking
# violation imposes cumulative vehicle-delay; we monetise it at a value-of-time.
# ---------------------------------------------------------------------------
DELAY_MIN_FULL_BLOCK = 12.0      # vehicle-minutes of cumulative delay per full (severity=1) block
VALUE_OF_TIME_PER_HR = 250.0     # ₹ per vehicle-hour (conservative urban India estimate)
PATROL_SPEED_KMPH = 18.0         # avg enforcement-vehicle speed for route ETA
