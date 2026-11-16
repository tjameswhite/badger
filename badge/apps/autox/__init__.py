import os
import sys

APP_DIRS = ("/remote/apps/autox", "/system/apps/autox", "/apps/autox", "/autox")
APP_DIR = next(path for path in APP_DIRS if is_dir(path))
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

import math

from badgeware import State, set_backlight

import runlog
import vehicle

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

# Full brightness for reading in a car. Not saved: leaving the app resets the
# badge, which restores the brightness chosen in Settings.
set_backlight(100, save=False)

# High contrast colours for daylight readability.
BG = color.rgb(0, 0, 0)
RING = color.rgb(90, 100, 115)
AXIS = color.rgb(60, 68, 80)
LABEL = color.rgb(190, 198, 210)
VALUE = color.rgb(235, 240, 245)
BALL = color.rgb(64, 220, 120)
TRAIL = color.rgb(30, 90, 56)
PEAK = color.rgb(255, 170, 60)
REC = color.rgb(240, 70, 70)
WARN = color.rgb(255, 200, 80)

badge.default_clear = BG

# Swap this out (e.g. from the simulator) to feed in fake motion.
read_raw = badge.imu

CX = 94
CY = 122
RADIUS = 88
MAX_G = 1.5
PX_PER_G = RADIUS / MAX_G
TRAIL_LEN = 48
PANEL_X = 192
PANEL_R = 316

# Large fonts for reading at a glance in the car.
BIG = font.ignore     # 28 px: live LAT/LONG and summary numbers
MED = font.smart      # 16 px: status, peaks, headings
SMALL = font.nope     # 13 px: labels and hints


def font_height(f):
    # measure_text returns floats; keep heights ints so they work in slices.
    screen.font = f
    return int(screen.measure_text("Ag")[1])


BIG_H = font_height(BIG)
MED_H = font_height(MED)
SMALL_H = font_height(SMALL)

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
    # The dot shows the force you feel, like a ball in a bowl:
    # accelerating = down, braking = up,
    # turning left = right, turning right = left
    return CX + lat * PX_PER_G, CY + lon * PX_PER_G


# Build the ring shapes once; drawing them without antialiasing is ~5x faster
# (measured on the badge: 1.3 ms vs 6.7 ms), which keeps the frame rate up.
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
    screen.font = SMALL
    screen.pen = LABEL
    screen.text("1g", CX + PX_PER_G + 3, CY + 2)
    text_center("BRAKE", CX, CY - RADIUS - SMALL_H - 4)
    text_center("ACCEL", CX, CY + RADIUS + 4)


def draw_ball(value):
    screen.pen = TRAIL
    for x, y in app["trail"]:
        screen.rectangle(int(x) - 1, int(y) - 1, 3, 3)
    if value is None:
        return
    x, y = to_screen(*value)
    screen.pen = BALL
    screen.shape(shape.circle(x, y, 8))


def draw_peaks(y):
    p = app["peaks"]
    screen.font = SMALL
    screen.pen = LABEL
    screen.text("PEAK", PANEL_X, y)
    y += SMALL_H + 4
    half = (PANEL_R - PANEL_X) // 2
    # each column: label at its left edge, value right-aligned to its right edge
    columns = ((PANEL_X, PANEL_X + half - 6), (PANEL_X + half + 6, PANEL_R))
    for row in ((("L", p.left), ("R", p.right)), (("B", p.brake), ("A", p.accel))):
        for (left, right), (label, v) in zip(columns, row):
            screen.font = SMALL
            screen.pen = LABEL
            screen.text(label, left, y + MED_H - SMALL_H)
            screen.font = MED
            screen.pen = PEAK
            text_right("%.2f" % v, right, y)
        y += MED_H + 6
    return y


def draw_live(value):
    draw_dial()
    draw_ball(value)
    y = 4
    screen.font = MED
    if app["mode"] == RECORDING:
        screen.pen = REC
        screen.shape(shape.circle(PANEL_X + 6, y + MED_H / 2, 5))
        screen.text("REC " + fmt_time(app["writer"].elapsed), PANEL_X + 16, y)
    else:
        screen.pen = VALUE
        screen.text("READY", PANEL_X, y)
    y += MED_H + 10
    lat, lon = value if value else (0.0, 0.0)
    for label, v in (("LAT", lat), ("LONG", lon)):
        screen.font = SMALL
        screen.pen = LABEL
        screen.text(label, PANEL_X, y + BIG_H - SMALL_H - 2)
        screen.font = BIG
        screen.pen = VALUE
        text_right("%+.2f" % v, PANEL_R, y)
        y += BIG_H + 6
    draw_peaks(y + 4)
    screen.font = SMALL
    screen.pen = LABEL
    hint = "SELECT stop" if app["mode"] == RECORDING else "SELECT record"
    screen.text(hint, PANEL_X, screen.height - (SMALL_H + 3) * 2)
    if app["mode"] == READY:
        screen.text("DOWN runs", PANEL_X, screen.height - SMALL_H - 3)
    if app["error"]:
        screen.pen = WARN
        screen.text(app["error"], 6, screen.height - SMALL_H - 3)


def draw_progress(fraction, y):
    w = screen.width - 40
    screen.pen = RING
    screen.rectangle(20, y, w, 10)
    screen.pen = BALL
    screen.rectangle(20, y, int(w * fraction), 10)


def draw_lines(lines, y=24):
    # lines: (text, pen, font); returns the y below the last line
    for text, pen, f in lines:
        screen.font = f
        screen.pen = pen
        if text:
            text_center(text, screen.width / 2, y)
        y += font_height(f) + 8
    return y


def draw_cal_level():
    lines = [
        ("CALIBRATE 1/2", VALUE, BIG),
        ("", LABEL, SMALL),
        ("Mount the badge firmly.", LABEL, MED),
        ("Stop the car and keep still.", LABEL, MED),
    ]
    if app["level"].too_shaky:
        lines.append(("Too much movement, retrying...", WARN, MED))
    y = draw_lines(lines)
    draw_progress(app["level"].progress, y + 8)


def draw_cal_fwd():
    y = draw_lines([
        ("CALIBRATE 2/2", VALUE, BIG),
        ("", LABEL, SMALL),
        ("Drive forward gently", LABEL, MED),
        ("in a straight line.", LABEL, MED),
        ("", LABEL, SMALL),
        ("BACK to start over", LABEL, SMALL),
    ])
    draw_progress(app["fwd"].progress, y + 8)


def fmt_time(ms):
    secs = int(ms) // 1000
    return "%d:%02d" % (secs // 60, secs % 60)


def draw_cell(label, value, x, y):
    screen.font = SMALL
    screen.pen = LABEL
    text_center(label, x, y)
    screen.font = BIG
    screen.pen = PEAK
    text_center("%.2f" % value, x, y + SMALL_H + 2)


def draw_summary():
    p = app["peaks"]
    number = app["run"]
    screen.font = BIG
    screen.pen = VALUE if number else WARN
    text_center("RUN %d SAVED" % number if number else "RUN NOT SAVED", screen.width / 2, 6)
    screen.font = MED
    screen.pen = LABEL
    text_center(fmt_time(app["writer"].elapsed), screen.width / 2, 8 + BIG_H)
    y = 16 + BIG_H + MED_H
    cell_h = SMALL_H + BIG_H + 8
    left_x, right_x = screen.width // 4, screen.width * 3 // 4
    draw_cell("LEFT g", p.left, left_x, y)
    draw_cell("RIGHT g", p.right, right_x, y)
    y += cell_h
    draw_cell("BRAKE g", p.brake, left_x, y)
    draw_cell("ACCEL g", p.accel, right_x, y)
    y += cell_h
    draw_cell("MAX COMBINED g", p.total, screen.width // 2, y)
    screen.font = SMALL
    screen.pen = LABEL
    text_center("SELECT to continue", screen.width / 2, screen.height - SMALL_H - 3)


def draw_runs():
    screen.font = MED
    screen.pen = VALUE
    screen.text("SAVED RUNS", 8, 6)
    screen.font = SMALL
    screen.pen = LABEL
    text_right("BACK", screen.width - 8, 8)
    runs = app["runs"]
    if not runs:
        screen.font = MED
        screen.text("No runs yet.", 8, 40)
        return
    row_h = MED_H + 6
    top = 14 + MED_H
    rows = (screen.height - top) // row_h
    y = top
    for number, info in runs[app["scroll"]:app["scroll"] + rows]:
        screen.font = MED
        screen.pen = VALUE
        screen.text("#%d" % number, 8, y)
        screen.pen = LABEL
        screen.text(fmt_time(info.get("ms", 0)), 50, y)
        if "t" in info:
            screen.pen = PEAK
            screen.text("%.2f g" % info["t"], 104, y)
            screen.font = SMALL
            screen.pen = LABEL
            screen.text("L%.2f R%.2f B%.2f" % (info["l"], info["r"], info["b"]), 176, y + MED_H - SMALL_H)
        y += row_h


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
