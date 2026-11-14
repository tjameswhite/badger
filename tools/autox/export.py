#!/usr/bin/env python3
"""Copy AutoX runs off a connected badge and convert them to CSV.

Usage (from the repository root, badge connected over USB):
    python3 tools/autox/export.py               # writes ./autox-runs/run-0001.csv ...
    python3 tools/autox/export.py --out runs     # choose the output folder
    python3 tools/autox/export.py --delete       # remove runs from the badge after copying
    python3 tools/autox/export.py --convert FILE.axr   # convert a file already copied

Needs mpremote (python3 -m pip install mpremote).
"""

import argparse
import ast
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "badge", "apps", "autox"))

import runlog  # noqa: E402
import vehicle  # noqa: E402

BADGE_VID_PID = "2e8a:1101"


def find_mpremote():
    exe = shutil.which("mpremote")
    if exe:
        return [exe]
    try:
        import mpremote  # noqa: F401
        return [sys.executable, "-m", "mpremote"]
    except ImportError:
        sys.exit("mpremote not found. Install it with: python3 -m pip install mpremote")


def find_port(mp):
    out = subprocess.run(mp + ["connect", "list"], capture_output=True, text=True, check=True).stdout
    ports = [line.split()[0] for line in out.splitlines() if BADGE_VID_PID in line]
    if not ports:
        sys.exit("No badge found. Connect it over USB and close other serial tools.")
    return ports[0]


def remote(mp, port, *args):
    return subprocess.run(mp + ["connect", port] + list(args), capture_output=True, text=True)


def convert(data, path_out):
    up, fwd, _start, rows = runlog.decode(data)
    cal = vehicle.Calibration.from_list(list(up) + list(fwd))
    with open(path_out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t_s", "lat_g", "long_g", "ax_g", "ay_g", "az_g"])
        for t, ax, ay, az in rows:
            a = vehicle.to_g((ax, ay, az))
            lat, lon = cal.car_g(a)
            writer.writerow(["%.3f" % (t / 1000), "%.4f" % lat, "%.4f" % lon,
                             "%.4f" % a[0], "%.4f" % a[1], "%.4f" % a[2]])
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="autox-runs", help="output folder (default: autox-runs)")
    parser.add_argument("--delete", action="store_true", help="delete runs from the badge after copying")
    parser.add_argument("--port", help="serial port (default: auto-detect)")
    parser.add_argument("--convert", metavar="FILE", help="convert a local .axr file instead of using the badge")
    args = parser.parse_args()

    if args.convert:
        out = os.path.splitext(args.convert)[0] + ".csv"
        with open(args.convert, "rb") as f:
            n = convert(f.read(), out)
        print("%s: %d samples -> %s" % (args.convert, n, out))
        return

    mp = find_mpremote()
    port = args.port or find_port(mp)
    listing = remote(mp, port, "exec", "import os\ntry:\n print(os.listdir('%s'))\nexcept OSError:\n print([])" % runlog.RUN_DIR)
    if listing.returncode:
        sys.exit(listing.stderr.strip() or "could not read the badge")
    names = sorted(n for n in ast.literal_eval(listing.stdout.strip().splitlines()[-1]) if n.endswith(runlog.KEPT))
    if not names:
        print("No saved runs on the badge.")
        return

    os.makedirs(args.out, exist_ok=True)
    summaries = {}
    index = remote(mp, port, "fs", "cat", ":" + runlog.INDEX)
    if index.returncode == 0:
        try:
            summaries = json.loads(index.stdout)
        except ValueError:
            pass

    copied = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            local = os.path.join(tmp, name)
            result = remote(mp, port, "fs", "cp", ":%s/%s" % (runlog.RUN_DIR, name), local)
            if result.returncode:
                print("  skipped %s: %s" % (name, result.stderr.strip()))
                continue
            with open(local, "rb") as f:
                data = f.read()
            shutil.copy(local, os.path.join(args.out, name))
            csv_path = os.path.join(args.out, name[:-len(runlog.KEPT)] + ".csv")
            n = convert(data, csv_path)
            info = summaries.get(str(runlog.run_number(name)), {})
            peak = " max %.2f g" % info["t"] if "t" in info else ""
            print("  %s: %d samples%s -> %s" % (name, n, peak, csv_path))
            copied.append(name)

    if args.delete and copied:
        for name in copied:
            remote(mp, port, "fs", "rm", ":%s/%s" % (runlog.RUN_DIR, name))
        left = [n for n in names if n not in copied]
        if not left:
            remote(mp, port, "fs", "rm", ":" + runlog.INDEX)
        print("Deleted %d run(s) from the badge." % len(copied))
    print("Done: %d run(s) in %s/" % (len(copied), args.out))


if __name__ == "__main__":
    main()
