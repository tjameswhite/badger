# Calibration and car-frame maths for the autocross g-meter.
# Pure Python (no badge globals) so it runs under CPython tests too.

import math

IMU_GRAVITY = 16384.0  # raw counts per 1 g (+/-2 g range)

LEVEL_MS = 1000         # time to hold still while measuring gravity
LEVEL_MAX_SPREAD = 0.04  # g; more wobble than this means "keep still"
FWD_MIN_G = 0.12        # horizontal accel needed to count as "driving forward"
FWD_MS = 750            # time of forward accel needed to lock in direction

# Gyro: CTRL2_G = 0x40 on the badge (read from the LSM6DS3TR-C), i.e. +/-245 dps,
# 8.75 mdps per count.
GYRO_COUNTS_PER_DPS = 114.3

# Re-levelling: while the car is stopped the app re-measures "up" so a badge that
# tips in its mount doesn't leak gravity into the readings.
STILL_BLOCK_MS = 250       # still detection works on 4 x 250 ms blocks
STILL_BLOCKS = 4
STILL_MAX_SPREAD = 0.08    # g; raw spread allowed (engine vibration at idle)
STILL_MAX_DRIFT = 0.02     # g; how much the block averages may differ
STILL_MAX_ROTATION = 3.0   # dps above the gyro bias; cornering is ~30+ dps
STILL_MAX_GYRO_SPREAD = 1.0  # dps between blocks, used when the bias is unknown
STILL_GRAVITY_TOL = 0.03   # g; |a| must be close to 1 g
RELEVEL_MAX_DEG = 30.0     # beyond this the badge was remounted: recalibrate instead
TILT_WARN_DEG = 5.0        # warn during a run if the badge has tipped this much


def to_g(raw):
    return (raw[0] / IMU_GRAVITY, raw[1] / IMU_GRAVITY, raw[2] / IMU_GRAVITY)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    if n < 1e-9:
        return None
    return scale(a, 1.0 / n)


class Calibration:
    """Orientation of the badge in the car.

    `up` is the unit vector the accelerometer reads when the car is still
    (the sensor reports the reaction to gravity, so this points up).
    `fwd` is the unit vector pointing to the front of the car.
    """

    def __init__(self, up, fwd, gyro_bias=None):
        self.up = up
        self.fwd = fwd
        # raw gyro reading while still (counts), or None if never measured
        self.gyro_bias = gyro_bias
        # right-handed: fwd x left = up  ->  left = up x fwd
        self.left = cross(up, fwd)

    def car_g(self, a):
        """Return the car's acceleration as (lat, long) in g.
        lat > 0 = turning left, lat < 0 = turning right,
        long > 0 = accelerating, long < 0 = braking."""
        lin = sub(a, self.up)
        return dot(lin, self.left), dot(lin, self.fwd)

    def axes(self):
        """up + fwd as 6 floats (the run log header format)."""
        return list(self.up) + list(self.fwd)

    def to_list(self):
        values = self.axes()
        if self.gyro_bias is not None:
            values += list(self.gyro_bias)
        return values

    @staticmethod
    def from_list(values):
        if not values or len(values) not in (6, 9):
            return None
        up = normalize(tuple(values[0:3]))
        fwd = normalize(tuple(values[3:6]))
        if up is None or fwd is None:
            return None
        bias = tuple(values[6:9]) if len(values) == 9 else None
        return Calibration(up, fwd, bias)


def angle_deg(u, v):
    """Angle between two unit vectors in degrees."""
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(u, v)))))


def rotate_toward(v, old_up, new_up):
    """Rotate v by the smallest rotation that takes old_up to new_up."""
    axis = cross(old_up, new_up)
    s = length(axis)
    c = dot(old_up, new_up)
    if s < 1e-9:
        return v
    k = scale(axis, 1.0 / s)
    kv = cross(k, v)
    kd = dot(k, v)
    return tuple(v[i] * c + kv[i] * s + k[i] * kd * (1 - c) for i in range(3))


def relevel(cal, new_up):
    """Calibration with a fresh `up`, assuming the badge tipped rather than
    twisted in its mount (fwd is rotated along with it)."""
    fwd = rotate_toward(cal.fwd, cal.up, new_up)
    fwd = normalize(sub(fwd, scale(new_up, dot(fwd, new_up))))
    if fwd is None:
        return cal
    return Calibration(new_up, fwd, cal.gyro_bias)


class StillTracker:
    """Detects when the car has been stopped for about a second.

    Uses 250 ms blocks of samples. The car counts as still when the last four
    blocks agree, raw vibration is small, |a| is about 1 g, and the gyro shows
    no rotation (steady cornering can look still to the accelerometer alone).
    """

    def __init__(self):
        self.blocks = []
        self._new_block()

    def _new_block(self):
        self.n = 0
        self.ms = 0
        self.sa = [0.0, 0.0, 0.0]
        self.sg = [0.0, 0.0, 0.0]
        self.lo = [9.0, 9.0, 9.0]
        self.hi = [-9.0, -9.0, -9.0]

    def reset(self):
        self.blocks = []
        self._new_block()

    def add(self, a, g, dt_ms):
        """Add a sample; returns True when a 250 ms block has just completed."""
        # unrolled: this runs every frame on the badge
        self.n += 1
        self.ms += dt_ms
        sa, sg, lo, hi = self.sa, self.sg, self.lo, self.hi
        ax, ay, az = a
        sa[0] += ax
        sa[1] += ay
        sa[2] += az
        sg[0] += g[0]
        sg[1] += g[1]
        sg[2] += g[2]
        if ax < lo[0]:
            lo[0] = ax
        if ax > hi[0]:
            hi[0] = ax
        if ay < lo[1]:
            lo[1] = ay
        if ay > hi[1]:
            hi[1] = ay
        if az < lo[2]:
            lo[2] = az
        if az > hi[2]:
            hi[2] = az
        if self.ms < STILL_BLOCK_MS:
            return False
        n = self.n
        self.blocks.append((
            (sa[0] / n, sa[1] / n, sa[2] / n),
            (sg[0] / n, sg[1] / n, sg[2] / n),
            max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]),
        ))
        if len(self.blocks) > STILL_BLOCKS:
            self.blocks.pop(0)
        self._new_block()
        return True

    def still_up(self, gyro_bias=None):
        """The measured `up` (unit vector) if the car has been still, else None."""
        if len(self.blocks) < STILL_BLOCKS:
            return None
        means = [b[0] for b in self.blocks]
        gyros = [b[1] for b in self.blocks]
        if max(b[2] for b in self.blocks) > STILL_MAX_SPREAD:
            return None
        for i in range(3):
            col = [m[i] for m in means]
            if max(col) - min(col) > STILL_MAX_DRIFT:
                return None
        avg = tuple(sum(m[i] for m in means) / STILL_BLOCKS for i in range(3))
        if abs(length(avg) - 1.0) > STILL_GRAVITY_TOL:
            return None
        g_avg = tuple(sum(g[i] for g in gyros) / STILL_BLOCKS for i in range(3))
        if gyro_bias is not None:
            if length(sub(g_avg, gyro_bias)) / GYRO_COUNTS_PER_DPS > STILL_MAX_ROTATION:
                return None
        else:
            for i in range(3):
                col = [g[i] for g in gyros]
                if (max(col) - min(col)) / GYRO_COUNTS_PER_DPS > STILL_MAX_GYRO_SPREAD:
                    return None
        return normalize(avg)

    def gyro_mean(self):
        if not self.blocks:
            return None
        return tuple(sum(b[1][i] for b in self.blocks) / len(self.blocks) for i in range(3))


class LevelStep:
    """Average gravity while the car is still."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.elapsed = 0
        self.sum = (0.0, 0.0, 0.0)
        self.count = 0
        self.lo = None
        self.hi = None
        self.result = None
        self.too_shaky = False
        self.gsum = (0.0, 0.0, 0.0)
        self.gyro_bias = None

    def add(self, a, dt_ms, g=None):
        if self.lo is None:
            self.lo = list(a)
            self.hi = list(a)
        for i in range(3):
            self.lo[i] = min(self.lo[i], a[i])
            self.hi[i] = max(self.hi[i], a[i])
        spread = max(self.hi[i] - self.lo[i] for i in range(3))
        if spread > LEVEL_MAX_SPREAD:
            self.reset()
            self.too_shaky = True
            return False
        self.sum = (self.sum[0] + a[0], self.sum[1] + a[1], self.sum[2] + a[2])
        if g is not None:
            self.gsum = (self.gsum[0] + g[0], self.gsum[1] + g[1], self.gsum[2] + g[2])
        self.count += 1
        self.elapsed += dt_ms
        if self.elapsed >= LEVEL_MS and self.count:
            self.result = normalize(scale(self.sum, 1.0 / self.count))
            if g is not None:
                self.gyro_bias = scale(self.gsum, 1.0 / self.count)
            return self.result is not None
        return False

    @property
    def progress(self):
        return min(1.0, self.elapsed / LEVEL_MS)


class ForwardStep:
    """Find the forward direction from a gentle straight-line acceleration."""

    def __init__(self, up, gyro_bias=None):
        self.up = up
        self.gyro_bias = gyro_bias
        self.reset()

    def reset(self):
        self.elapsed = 0
        self.sum = (0.0, 0.0, 0.0)
        self.result = None

    def horizontal(self, a):
        # remove gravity, then drop whatever is left along the up axis
        lin = sub(a, self.up)
        return sub(lin, scale(self.up, dot(lin, self.up)))

    def add(self, a, dt_ms):
        h = self.horizontal(a)
        if length(h) < FWD_MIN_G:
            return False
        self.sum = (self.sum[0] + h[0], self.sum[1] + h[1], self.sum[2] + h[2])
        self.elapsed += dt_ms
        if self.elapsed >= FWD_MS:
            fwd = normalize(self.sum)
            if fwd is not None:
                self.result = Calibration(self.up, fwd, self.gyro_bias)
                return True
        return False

    @property
    def progress(self):
        return min(1.0, self.elapsed / FWD_MS)


class Smoother:
    """Frame-rate independent exponential moving average for (lat, long)."""

    def __init__(self, time_constant_ms=120):
        self.tc = time_constant_ms
        self.value = None

    def add(self, v, dt_ms):
        if self.value is None:
            self.value = v
            return v
        k = 1 - math.exp(-min(dt_ms, 200) / self.tc)
        self.value = (
            self.value[0] + (v[0] - self.value[0]) * k,
            self.value[1] + (v[1] - self.value[1]) * k,
        )
        return self.value


class Peaks:
    def __init__(self):
        self.reset()

    def reset(self):
        self.left = 0.0
        self.right = 0.0
        self.brake = 0.0
        self.accel = 0.0
        self.total = 0.0

    def add(self, lat, lon):
        self.left = max(self.left, lat)
        self.right = max(self.right, -lat)
        self.accel = max(self.accel, lon)
        self.brake = max(self.brake, -lon)
        self.total = max(self.total, math.sqrt(lat * lat + lon * lon))
