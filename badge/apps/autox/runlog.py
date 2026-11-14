# Run logging for the autocross g-meter.
#
# File format (little-endian), shared with tools/autox/export.py:
#   header: "AXR1", version (u8), up xyz + fwd xyz (6 x f32), start ticks (u32)
#   record: dt_ms (u16), ax, ay, az raw counts (3 x i16)   -> 8 bytes
# Raw counts are kept so the computer can redo any maths later.

import json
import os
import struct

MAGIC = b"AXR1"
VERSION = 1
HEADER = "<4sB6fI"
RECORD = "<Hhhh"
HEADER_SIZE = struct.calcsize(HEADER)
RECORD_SIZE = struct.calcsize(RECORD)

STATE_DIR = "/state"
RUN_DIR = STATE_DIR + "/autox"
INDEX = RUN_DIR + "/index.json"
PARTIAL = ".part"
KEPT = ".axr"
PREFIX = "run-"

MAX_RUN_MS = 180000           # stop recording after 3 minutes
MAX_BYTES = HEADER_SIZE + RECORD_SIZE * 100 * (MAX_RUN_MS // 1000)  # worst case at 100 Hz
RESERVE_BYTES = 64 * 1024     # always leave room for other apps' state
KEEP = 40                      # never keep more than this many runs
BUFFER_RECORDS = 128           # flush roughly every 1.5 s at ~89 Hz


def ensure_dir(path):
    try:
        os.stat(path)
    except OSError:
        os.mkdir(path)


def free_bytes(path):
    stats = os.statvfs(path)
    return stats[0] * stats[3]


def run_number(name):
    for ext in (KEPT, PARTIAL):
        if name.startswith(PREFIX) and name.endswith(ext):
            digits = name[len(PREFIX):-len(ext)]
            if digits.isdigit():
                return int(digits)
    return None


def load_index():
    try:
        with open(INDEX) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_index(index):
    temporary = INDEX + ".tmp"
    try:
        with open(temporary, "w") as f:
            json.dump(index, f)
        try:
            os.remove(INDEX)
        except OSError:
            pass
        os.rename(temporary, INDEX)
    except OSError:
        pass


def list_runs():
    """Saved runs, newest first: [(number, summary dict)]."""
    try:
        names = os.listdir(RUN_DIR)
    except OSError:
        return []
    index = load_index()
    runs = []
    for name in names:
        if name.endswith(KEPT):
            number = run_number(name)
            if number is not None:
                runs.append((number, index.get(str(number), {})))
    runs.sort(key=lambda r: -r[0])
    return runs


def run_path(number):
    return "%s/%s%04d%s" % (RUN_DIR, PREFIX, number, KEPT)


def delete_run(number, index=None):
    try:
        os.remove(run_path(number))
    except OSError:
        pass
    own = index is None
    if own:
        index = load_index()
    index.pop(str(number), None)
    if own:
        save_index(index)


def next_number():
    """Tidy leftovers, free space if needed, and return the next run number."""
    ensure_dir(STATE_DIR)
    ensure_dir(RUN_DIR)
    numbers = []
    for name in os.listdir(RUN_DIR):
        number = run_number(name)
        if number is None:
            continue
        if name.endswith(PARTIAL):
            # a run that never finished (reset or crash): keep what was written
            path = RUN_DIR + "/" + name
            if os.stat(path)[6] <= HEADER_SIZE:
                os.remove(path)
                continue
            os.rename(path, run_path(number))
        numbers.append(number)
    numbers.sort()
    newest = numbers[-1] if numbers else 0
    index = load_index()
    changed = False
    while numbers and (len(numbers) >= KEEP or free_bytes(STATE_DIR) < MAX_BYTES + RESERVE_BYTES):
        delete_run(numbers.pop(0), index)
        changed = True
    if changed:
        save_index(index)
    if free_bytes(STATE_DIR) < MAX_BYTES + RESERVE_BYTES:
        raise OSError("no space")
    return newest + 1


class RunWriter:
    def __init__(self):
        self.buffer = bytearray(RECORD_SIZE * BUFFER_RECORDS)
        self.view = memoryview(self.buffer)
        self.position = 0
        self.recording = False
        self.number = None
        self.path = None
        self.elapsed = 0
        self.samples = 0

    def start(self, cal_values, ticks):
        self.number = next_number()
        self.path = "%s/%s%04d%s" % (RUN_DIR, PREFIX, self.number, PARTIAL)
        header = struct.pack(HEADER, MAGIC, VERSION, *(list(cal_values) + [ticks & 0xFFFFFFFF]))
        with open(self.path, "wb") as f:
            f.write(header)
        self.position = 0
        self.elapsed = 0
        self.samples = 0
        self.recording = True
        return self.number

    def add(self, dt_ms, raw):
        """Record one sample. Returns False once the run hits its time cap."""
        if not self.recording:
            return False
        struct.pack_into(RECORD, self.buffer, self.position,
                         min(max(int(dt_ms), 0), 0xFFFF), raw[0], raw[1], raw[2])
        self.position += RECORD_SIZE
        self.samples += 1
        self.elapsed += dt_ms
        if self.position >= len(self.buffer):
            self.flush()
        if self.elapsed >= MAX_RUN_MS:
            return False
        return self.recording

    def flush(self):
        if not self.position:
            return
        try:
            with open(self.path, "ab") as f:
                f.write(self.view[:self.position])
        except OSError:
            self.recording = False
        self.position = 0

    def stop(self, summary):
        """Finish the run and store its summary. Returns the run number."""
        if self.path is None:
            return None
        self.flush()
        self.recording = False
        try:
            os.rename(self.path, run_path(self.number))
        except OSError:
            return None
        index = load_index()
        summary["ms"] = self.elapsed
        summary["n"] = self.samples
        index[str(self.number)] = summary
        save_index(index)
        self.path = None
        return self.number


def decode(data):
    """Decode a run file's bytes (used by the computer-side export script).
    Returns (up, fwd, start_ticks, [(t_ms, ax, ay, az), ...])."""
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        raise ValueError("not an autox run file")
    fields = struct.unpack_from(HEADER, data, 0)
    if fields[1] != VERSION:
        raise ValueError("unsupported version %d" % fields[1])
    up, fwd, start = fields[2:5], fields[5:8], fields[8]
    rows = []
    t = 0
    offset = HEADER_SIZE
    while offset + RECORD_SIZE <= len(data):
        dt, ax, ay, az = struct.unpack_from(RECORD, data, offset)
        t += dt
        rows.append((t, ax, ay, az))
        offset += RECORD_SIZE
    return up, fwd, start, rows
