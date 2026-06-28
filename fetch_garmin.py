#!/usr/bin/env python3
"""Runs in GitHub Actions. Restores the saved Garmin token from the
GARMIN_TOKENS secret (no password or MFA needed), pulls today's wellness,
and writes garmin.json. The token auto-refreshes for ~a year."""
import os, io, base64, tarfile, json, datetime
from garminconnect import Garmin

tokendir = os.path.expanduser("~/.garminconnect")
os.makedirs(tokendir, exist_ok=True)
raw = base64.b64decode(os.environ["GARMIN_TOKENS"])
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
    tar.extractall(tokendir)

g = Garmin()
g.login(tokendir)          # resume from saved token; refreshes automatically

today = datetime.date.today().isoformat()
out = {"date": today}

def safe(fn):
    try:
        return fn()
    except Exception as e:
        print("skip:", e); return None

sleep = safe(lambda: g.get_sleep_data(today))
if sleep:
    dto = sleep.get("dailySleepDTO", {}) or {}
    if dto.get("sleepTimeSeconds"):
        out["sleepHours"] = round(dto["sleepTimeSeconds"] / 3600, 1)
    try: out["sleepScore"] = dto["sleepScores"]["overall"]["value"]
    except Exception: pass

hrv = safe(lambda: g.get_hrv_data(today))
if hrv:
    s = hrv.get("hrvSummary", {}) or {}
    if s.get("lastNightAvg") is not None: out["hrv"] = s["lastNightAvg"]
    if s.get("status"): out["hrvStatus"] = str(s["status"]).title()

stats = safe(lambda: g.get_stats(today))
if stats:
    for k_src, k_dst in [("totalSteps","steps"),("activeKilocalories","caloriesActive"),
                         ("restingHeartRate","restingHr"),("bodyBatteryMostRecentValue","bodyBattery")]:
        if stats.get(k_src) is not None:
            out[k_dst] = stats[k_src]

if "bodyBattery" not in out:
    bb = safe(lambda: g.get_body_battery(today, today))
    try: out["bodyBattery"] = bb[0]["bodyBatteryValuesArray"][-1][1]
    except Exception: pass

with open("garmin.json", "w") as f:
    json.dump(out, f, indent=2)
print("wrote garmin.json:", out)
