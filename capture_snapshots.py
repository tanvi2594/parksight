"""Capture authentic, focused dashboard screenshots of every feature into ./snapshots."""
import sys, pathlib
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8533"
SNAP = pathlib.Path("snapshots"); SNAP.mkdir(exist_ok=True)
TABS = [("Command Map", "01_command_map", 360), ("Live Ops", "02_live_ops", 360),
        ("Priorities & Deploy", "03_priorities_deploy", 360), ("Forecast", "04_forecast", 360),
        ("Repeat Offenders", "05_repeat_offenders", 360), ("Trends", "06_trends", 360),
        ("Coverage & Context", "07_coverage_context", 360), ("Validation", "08_validation", 360),
        ("Method", "09_method", 360)]


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl",
                                    "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": 1500, "height": 950}, device_scale_factor=2)
        pg.goto(URL, wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(9000)
        # 0) overview (top of page: header + KPIs + Ask bar)
        pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(800)
        pg.screenshot(path=str(SNAP / "00_overview.png")); print("00_overview")
        # tabs (focused: scroll past the header so the tab's own content fills the frame)
        for name, fn, y in TABS:
            try:
                pg.get_by_role("tab", name=name, exact=False).first.click()
                pg.wait_for_timeout(5000)
                pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(900)
                pg.screenshot(path=str(SNAP / f"{fn}.png")); print(fn)
            except Exception as e:
                print("fail", fn, str(e)[:70])
        # 3D city: back to Command Map, toggle 3D, scroll to the map
        try:
            pg.get_by_role("tab", name="Command Map", exact=False).first.click(); pg.wait_for_timeout(2500)
            pg.get_by_text("3D city", exact=False).first.click(); pg.wait_for_timeout(7000)
            pg.evaluate("window.scrollTo(0,360)"); pg.wait_for_timeout(1500)
            pg.screenshot(path=str(SNAP / "01b_3d_city.png")); print("01b_3d_city")
            pg.get_by_text("3D city", exact=False).first.click(); pg.wait_for_timeout(1500)
        except Exception as e:
            print("3d fail", str(e)[:70])
        # Ask ParkSight demo (click a chip -> answer + map)
        try:
            pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(600)
            pg.get_by_role("button", name="Worst hotspots in Indiranagar").click()
            pg.wait_for_timeout(4500)
            pg.evaluate("window.scrollTo(0,150)"); pg.wait_for_timeout(700)
            pg.screenshot(path=str(SNAP / "00b_ask_parksight.png")); print("00b_ask_parksight")
        except Exception as e:
            print("ask fail", str(e)[:70])
        b.close()


if __name__ == "__main__":
    main()
