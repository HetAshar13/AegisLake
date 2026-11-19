"""Generate repeatable benchmark evidence and capture the analyst replay demo."""

import argparse
from collections import defaultdict
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
from statistics import median
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("authorizations", "settlements", "ledger")
CASE = "card_ledger_short"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def scaled_fixture(case_count):
    fixture = json.loads((ROOT / "fixtures/card_demo.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "fixtures/card_demo_expected.json").read_text(encoding="utf-8"))
    grouped = defaultdict(list)
    scaled = {key: value for key, value in fixture.items() if key not in SOURCES}
    for source in SOURCES:
        scaled[source] = []
        for row in fixture[source]:
            grouped[row["authorization_id"]].append((source, row))

    target = {"cases": {}, "quarantine": [], "unknown_merchants": []}
    scenarios = list(expected["cases"])
    for index in range(case_count):
        template = scenarios[index % len(scenarios)]
        payment_id = f"case_{index:06d}"
        target["cases"][payment_id] = expected["cases"][template]
        if template in expected["unknown_merchants"]:
            target["unknown_merchants"].append(payment_id)
        for source, row in grouped[template]:
            scaled[source].append(dict(row, authorization_id=payment_id, event_id=f"{source}_{payment_id}"))
    # Preserve the malformed-input rate while scaling the assessed case population separately.
    for item in expected["quarantine"]:
        source, malformed = next(
            (source, row) for entries in grouped.values() for source, row in entries
            if row["event_id"] == item["event_id"]
        )
        for index in range((case_count + len(scenarios) - 1) // len(scenarios)):
            event_id = f"{item['event_id']}_{index:06d}"
            scaled[source].append(dict(malformed, authorization_id=event_id, event_id=event_id))
            target["quarantine"].append(dict(item, event_id=event_id))
    return scaled, target


def run_benchmark(output, sizes, repeats):
    root = output / "runs"
    root.mkdir()
    def run(size, trial):
        folder = root / str(size)
        build = folder / f"trial-{trial}"
        start = time.perf_counter()
        subprocess.run([
            sys.executable, str(ROOT / "scripts/run_card_demo.py"),
            "--fixture", str(folder / "fixture.json"), "--expected", str(folder / "expected.json"),
            "--output", str(build),
        ], cwd=ROOT, check=True)
        seconds = time.perf_counter() - start
        with duckdb.connect() as db:
            bronze = (build / "lakehouse/bronze_events").as_posix()
            committed = db.execute("select count(*) from delta_scan(?)", [bronze]).fetchone()[0]
        assert committed == event_counts[size], (committed, event_counts[size])
        return {"seconds": round(seconds, 3), "committed_events": committed}

    event_counts = {}
    for size in sorted({11, *sizes}):
        fixture, expected = scaled_fixture(size)
        folder = root / str(size)
        folder.mkdir()
        write_json(folder / "fixture.json", fixture)
        write_json(folder / "expected.json", expected)
        event_counts[size] = sum(len(fixture[source]) for source in SOURCES)

    # The first build initializes package caches. Timed trials each start a fresh process and JVM.
    run(11, 0)
    metadata = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "cpu_model": platform.processor(),
        "python": platform.python_version(),
        "java": subprocess.run(["java", "-version"], text=True, capture_output=True, check=True).stderr.splitlines()[0],
        "versions": {name: version(name) for name in ("pyspark", "delta-spark", "dbt-core", "dbt-duckdb", "duckdb")},
        "boundary": "Fixture JSON read through Bronze and Silver Delta, dbt Gold build and correctness checks",
        "start": "Fresh Python and JVM for each sequential trial after warming dependency caches",
        "measurement": "Wall time; input generation and post-run Bronze count query excluded",
    }
    if Path("/proc/cpuinfo").is_file():
        metadata["cpu_model"] = next(
            (line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
             if line.startswith("model name")), metadata["cpu_model"]
        )
        metadata["available_memory_kib"] = int(Path("/proc/meminfo").read_text().splitlines()[0].split()[1])
    summary = ["### Card reconciliation benchmark", "",
               "| Assessed cases | Committed Bronze events | Median seconds | Range seconds | Events/s |",
               "| ---: | ---: | ---: | ---: | ---: |"]
    results = []
    for size in sizes:
        trials = [run(size, trial) for trial in range(1, repeats + 1)]
        seconds = [trial["seconds"] for trial in trials]
        middle = median(seconds)
        rate = event_counts[size] / middle
        results.append({"cases": size, "trials": trials, "median_seconds": middle,
                        "committed_events_per_second": round(rate, 2)})
        summary.append(f"| {size:,} | {event_counts[size]:,} | {middle:.2f} | "
                       f"{min(seconds):.2f}–{max(seconds):.2f} | {rate:.1f} |")
    write_json(output / "benchmark.json", {"environment": metadata, "results": results})
    text = "\n".join(summary) + "\n"
    (output / "benchmark.md").write_text(text, encoding="utf-8")
    print(text, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(text)


def capture_demo(output, replay):
    from PIL import Image, ImageDraw, ImageFont
    from playwright.sync_api import sync_playwright

    caps = [
        ("Payment reconciliation", "Track card authorizations, settlements and ledger postings in one case queue."),
        ("Investigate the €0.10 break", "The authorization and settlement are €100.00. The source ledger posted €99.90."),
        ("Replay with a corrected ledger posting", "A new version of the posting supplies €100.00. The case now matches."),
        ("The original assessment remains available", "The corrected run changes one case. The earlier warehouse preserves the break."),
    ]

    def screenshot(browser, stage, port, name, inspect=False, corrected=False):
        warehouse = replay / stage / "aegislake.duckdb"
        env = os.environ | {"AEGIS_WAREHOUSE": str(warehouse)}
        url = f"http://127.0.0.1:{port}"
        with (output / f"{name}.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", "src/aegis_ui/app.py",
                "--server.headless=true", "--browser.gatherUsageStats=false",
                f"--server.port={port}", "--server.address=127.0.0.1",
            ], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(120):
                    if server.poll() is not None:
                        raise RuntimeError(f"Streamlit stopped; see {name}.log")
                    try:
                        with urlopen(url + "/_stcore/health", timeout=1):
                            break
                    except (URLError, TimeoutError):
                        time.sleep(0.5)
                else:
                    raise TimeoutError("Streamlit health check did not respond")
                page = browser.new_page(viewport={"width": 1280, "height": 849})
                page.goto(url, wait_until="domcontentloaded")
                page.get_by_text("Actionable breaks", exact=True).wait_for(timeout=30000)
                if inspect:
                    if corrected:
                        page.get_by_text("Actionable breaks only", exact=True).click()
                    page.get_by_role("combobox").click()
                    page.get_by_role("option", name=CASE, exact=True).click()
                    status = "MATCHED" if corrected else "BREAK_LEDGER_AMOUNT_MISMATCH"
                    page.get_by_role("heading", name=status, exact=True).wait_for()
                page.screenshot(path=str(output / f"{name}.png"), animations="disabled")
                page.close()
            finally:
                server.terminate()
                server.wait(timeout=15)

    with sync_playwright() as play:
        browser = play.chromium.launch()
        screenshot(browser, "01_original", 8501, "overview")
        screenshot(browser, "01_original", 8502, "break", inspect=True)
        screenshot(browser, "03_correction", 8503, "correction", inspect=True, corrected=True)

    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    captions = output / "timeline.txt"
    names = ("overview", "break", "correction", "break")
    frames = []
    for index, ((title, caption), name, seconds) in enumerate(zip(caps, names, (17, 27, 27, 19), strict=True)):
        canvas = Image.new("RGB", (1280, 960), "#111a2e")
        with Image.open(output / f"{name}.png") as source:
            canvas.paste(source.convert("RGB"), (0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((28, 867), title, font=ImageFont.truetype(str(font), 30), fill="#ffffff")
        draw.text((28, 913), caption, font=ImageFont.truetype(str(font), 22), fill="#d4e3f9")
        frame = f"scene-{index}.png"
        canvas.save(output / frame)
        frames.append(f"file '{frame}'\nduration {seconds}\n")
    captions.write_text("".join(frames) + "file 'scene-3.png'\n", encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", "timeline.txt", "-t", "90", "-r", "24", "-c:v", "libx264", "-pix_fmt",
        "yuv420p", "-movflags", "+faststart", "aegislake-replay.mp4",
    ], cwd=output, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("benchmark", "demo"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--replay", type=Path, help="Run directory produced by verify_card_replay.py")
    args = parser.parse_args()
    if args.repeats < 1 or min(args.sizes) < 1 or len(set(args.sizes)) != len(args.sizes):
        parser.error("Choose distinct positive sizes and at least one repeat")
    if args.mode == "demo" and args.replay is None:
        parser.error("The demo requires --replay")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    if args.mode == "benchmark":
        run_benchmark(output, args.sizes, args.repeats)
    else:
        capture_demo(output, args.replay.resolve())


if __name__ == "__main__":
    main()
