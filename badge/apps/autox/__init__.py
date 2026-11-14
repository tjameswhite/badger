import os
import sys

APP_DIRS = ("/remote/apps/autox", "/system/apps/autox", "/apps/autox", "/autox")
APP_DIR = next(path for path in APP_DIRS if is_dir(path))
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

import math

from badgeware import State

import runlog
import vehicle

badge.mode(HIRES | VSYNC)
screen.font = font.sins
screen.antialias = image.X2

BG = color.rgb(14, 17, 22)
RING = color.rgb(52, 60, 72)
AXIS = color.rgb(34, 40, 50)
LABEL = color.rgb(130, 140, 155)
VALUE = color.rgb(235, 240, 245)
BALL = color.rgb(64, 220, 120)
TRAIL = color.rgb(30, 90, 56)
PEAK = color.rgb(255, 170, 60)
REC = color.rgb(240, 70, 70)
WARN = color.rgb(255, 200, 80)

badge.default_clear = BG

# Swap this out (e.g. from the simulator) to feed in fake motion.
read_raw = badge.imu

CX = 116
CY = 120
RADIUS = 104
MAX_G = 1.5
PX_PER_G = RADIUS / MAX_G
TRAIL_LEN = 48
PANEL_X = 232

# measure_text returns floats; keep LINE an int so it can be used in slices.
_, LINE = screen.measure_text("Ag")
LINE = int(LINE) + 2

CAL_LEVEL = "cal_level"
CAL_FWD = "cal_fwd"
READY = "ready"
RECORDING = "rec"
SUMMARY = "summary"
RUNS = "runs"

saved = {"cal": []}
State.load("autox", saved)

app = {
    "mode": READY,
    "cal": vehicle.Calibration.from_list(saved["cal"]),
    "level": vehicle.LevelStep(),
    "fwd": None,
    "smooth": vehicle.Smoother(),
    "peaks": vehicle.Peaks(),
    "trail": [],
    "writer": runlog.RunWriter(),
    "run": None,
    "error": None,
    "runs": [],
    "scroll": 0,
}
if app["cal"] is None:
    app["mode"] = CAL_LEVEL


def start_calibration():
    app["level"].reset()
    app["level"].too_shaky = False
    app["fwd"] = None
    app["mode"] = CAL_LEVEL


def finish_calibration(cal):
    app["cal"] = cal
    saved["cal"] = cal.to_list()
    State.save("autox", saved)
    reset_live()
    app["mode"] = READY


def reset_live():
    app["peaks"].reset()
    app["trail"] = []
    app["smooth"] = vehicle.Smoother()


def start_run():
    reset_live()
    app["error"] = None
    try:
        app["run"] = app["writer"].start(app["cal"].to_list(), badge.ticks)
        app["mode"] = RECORDING
    except OSError as e:
        app["error"] = "can't record: %s" % e


def stop_run():
    p = app["peaks"]
    summary = {
        "l": round(p.left, 2), "r": round(p.right, 2),
        "b": round(p.brake, 2), "a": round(p.accel, 2), "t": round(p.total, 2),
    }
    app["run"] = app["writer"].stop(summary)
    app["mode"] = SUMMARY


def open_runs():
    app["runs"] = runlog.list_runs()
    app["scroll"] = 0
    app["mode"] = RUNS


# ---------------------------------------------------------------- drawing

def text_right(text, x, y):
    w, _ = screen.measure_text(text)
    screen.text(text, x - w, y)


def text_center(text, x, y):
    w, _ = screen.measure_text(text)
    screen.text(text, x - w / 2, y)


def to_screen(lat, lon):
    # car acceleration: accelerating = up, braking = down,
    # turning right = right, turning left = left
    return CX - lat * PX_PER_G, CY - lon * PX_PER_G


# Build the ring shapes once; drawing them without antialiasing is ~5x faster
# (measured on the badge: 1.3 ms vs 6.7 ms), which keeps the frame rate at 60.
RINGS = [shape.circle(CX, CY, g * PX_PER_G).stroke(1) for g in (0.5, 1.0, 1.5)]


def draw_dial():
    screen.antialias = image.OFF
    screen.pen = AXIS
    screen.line(CX - RADIUS, CY, CX + RADIUS, CY)
    screen.line(CX, CY - RADIUS, CX, CY + RADIUS)
    screen.pen = RING
    for ring in RINGS:
        screen.shape(ring)
    screen.antialias = image.X2
    screen.pen = LABEL
    screen.text("1g", CX + PX_PER_G + 3, CY + 2)
    text_center("ACCEL", CX, 2)
    text_center("BRAKE", CX, screen.height - LINE)


def draw_ball(value):
    screen.pen = TRAIL
    for x, y in app["trail"]:
        screen.rectangle(int(x) - 1, int(y) - 1, 3, 3)
    if value is None:
        return
    x, y = to_screen(*value)
    screen.pen = BALL
    screen.shape(shape.circle(x, y, 7))


def draw_peaks(y):
    p = app["peaks"]
    screen.pen = LABEL
    screen.text("PEAK", PANEL_X, y)
    y += LINE
    for label, v in (("L", p.left), ("R", p.right), ("BRK", p.brake), ("ACC", p.accel)):
        screen.pen = LABEL
        screen.text(label, PANEL_X, y)
        screen.pen = PEAK
        text_right("%.2f" % v, screen.width - 6, y)
        y += LINE
    return y


def draw_live(value):
    draw_dial()
    draw_ball(value)
    y = 4
    if app["mode"] == RECORDING:
        screen.pen = REC
        screen.shape(shape.circle(PANEL_X + 5, y + LINE / 2, 4))
        secs = app["writer"].elapsed // 1000
        screen.text("REC %d:%02d" % (secs // 60, secs % 60), PANEL_X + 14, y)
    else:
        screen.pen = VALUE
        screen.text("READY", PANEL_X, y)
    y += LINE * 2
    lat, lon = value if value else (0.0, 0.0)
    for label, v in (("LAT", lat), ("LONG", lon)):
        screen.pen = LABEL
        screen.text(label, PANEL_X, y)
        screen.pen = VALUE
        text_right("%+.2f" % v, screen.width - 6, y)
        y += LINE
    y += LINE // 2
    draw_peaks(y)
    screen.pen = LABEL
    hint = "SELECT stop" if app["mode"] == RECORDING else "SELECT record"
    screen.text(hint, PANEL_X, screen.height - LINE * 2)
    if app["mode"] == READY:
        screen.text("DOWN runs", PANEL_X, screen.height - LINE)
    if app["error"]:
        screen.pen = WARN
        screen.text(app["error"], 6, screen.height - LINE)


def draw_progress(fraction, y):
    w = screen.width - 40
    screen.pen = RING
    screen.rectangle(20, y, w, 8)
    screen.pen = BALL
    screen.rectangle(20, y, int(w * fraction), 8)


def draw_lines(lines, y=40):
    for text, pen in lines:
        screen.pen = pen
        text_center(text, screen.width / 2, y)
        y += LINE + 2
    return y


def draw_cal_level():
    lines = [
        ("CALIBRATE 1/2", VALUE),
        ("", LABEL),
        ("Mount the badge firmly.", LABEL),
        ("Stop the car and keep still.", LABEL),
    ]
    if app["level"].too_shaky:
        lines.append(("Too much movement, retrying...", WARN))
    y = draw_lines(lines)
    draw_progress(app["level"].progress, y + 12)


def draw_cal_fwd():
    y = draw_lines([
        ("CALIBRATE 2/2", VALUE),
        ("", LABEL),
        ("Drive forward gently", LABEL),
        ("in a straight line.", LABEL),
        ("", LABEL),
        ("BACK to start over", LABEL),
    ])
    draw_progress(app["fwd"].progress, y + 12)


def fmt_time(ms):
    secs = ms // 1000
    return "%d:%02d" % (secs // 60, secs % 60)


def draw_summary():
    p = app["peaks"]
    number = app["run"]
    lines = [
        ("RUN %d SAVED" % number if number else "RUN NOT SAVED", VALUE if number else WARN),
        (fmt_time(app["writer"].elapsed), LABEL),
        ("", LABEL),
        ("Left %.2f g   Right %.2f g" % (p.left, p.right), PEAK),
        ("Brake %.2f g   Accel %.2f g" % (p.brake, p.accel), PEAK),
        ("Max combined %.2f g" % p.total, PEAK),
        ("", LABEL),
        ("SELECT to continue", LABEL),
    ]
    draw_lines(lines, 30)


def draw_runs():
    screen.pen = VALUE
    screen.text("SAVED RUNS", 8, 6)
    screen.pen = LABEL
    text_right("BACK", screen.width - 8, 6)
    runs = app["runs"]
    if not runs:
        screen.text("No runs yet.", 8, 40)
        return
    rows = (screen.height - 34) // LINE
    y = 30
    for number, info in runs[app["scroll"]:app["scroll"] + rows]:
        screen.pen = VALUE
        screen.text("#%d" % number, 8, y)
        screen.pen = LABEL
        screen.text(fmt_time(info.get("ms", 0)), 52, y)
        if "t" in info:
            screen.pen = PEAK
            screen.text("max %.2f  L%.2f R%.2f B%.2f" % (info["t"], info["l"], info["r"], info["b"]), 100, y)
        y += LINE


# ---------------------------------------------------------------- update

def update():
    dt = badge.ticks_delta
    raw = read_raw()
    a = vehicle.to_g(raw)
    mode = app["mode"]

    if mode == CAL_LEVEL:
        if app["level"].add(a, dt):
            app["fwd"] = vehicle.ForwardStep(app["level"].result)
            app["mode"] = CAL_FWD
        draw_cal_level()
        return

    if mode == CAL_FWD:
        if badge.pressed(BUTTON_BACK):
            start_calibration()
        elif app["fwd"].add(a, dt):
            finish_calibration(app["fwd"].result)
        draw_cal_fwd()
        return

    if mode == SUMMARY:
        if badge.pressed(BUTTON_SELECT) or badge.pressed(BUTTON_BACK):
            reset_live()
            app["mode"] = READY
        draw_summary()
        return

    if mode == RUNS:
        if badge.pressed(BUTTON_BACK):
            app["mode"] = READY
        if badge.pressed(BUTTON_DOWN):
            app["scroll"] = min(max(len(app["runs"]) - 1, 0), app["scroll"] + 1)
        if badge.pressed(BUTTON_UP):
            app["scroll"] = max(0, app["scroll"] - 1)
        draw_runs()
        return

    # READY / RECORDING: live g-meter
    value = app["smooth"].add(app["cal"].car_g(a), dt)
    app["peaks"].add(*value)
    trail = app["trail"]
    trail.append(to_screen(*value))
    if len(trail) > TRAIL_LEN:
        trail.pop(0)

    if mode == RECORDING:
        still_going = app["writer"].add(dt, raw)
        if badge.pressed(BUTTON_SELECT) or not still_going:
            stop_run()
    else:
        if badge.pressed(BUTTON_SELECT):
            start_run()
        elif badge.pressed(BUTTON_BACK):
            reset_live()
        elif badge.pressed(BUTTON_MENU):
            start_calibration()
        elif badge.pressed(BUTTON_DOWN):
            open_runs()

    draw_live(value)


run(update)
