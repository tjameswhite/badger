# Calibration and car-frame maths for the autocross g-meter.
# Pure Python (no badge globals) so it runs under CPython tests too.

import math

IMU_GRAVITY = 16384.0  # raw counts per 1 g (+/-2 g range)

LEVEL_MS = 1000         # time to hold still while measuring gravity
LEVEL_MAX_SPREAD = 0.04  # g; more wobble than this means "keep still"
FWD_MIN_G = 0.12        # horizontal accel needed to count as "driving forward"
FWD_MS = 750            # time of forward accel needed to lock in direction


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

    def __init__(self, up, fwd):
        self.up = up
        self.fwd = fwd
        # right-handed: fwd x left = up  ->  left = up x fwd
        self.left = cross(up, fwd)

    def car_g(self, a):
        """Return the car's acceleration as (lat, long) in g.
        lat > 0 = turning left, lat < 0 = turning right,
        long > 0 = accelerating, long < 0 = braking."""
        lin = sub(a, self.up)
        return dot(lin, self.left), dot(lin, self.fwd)

    def to_list(self):
        return list(self.up) + list(self.fwd)

    @staticmethod
    def from_list(values):
        if not values or len(values) != 6:
            return None
        up = normalize(tuple(values[0:3]))
        fwd = normalize(tuple(values[3:6]))
        if up is None or fwd is None:
            return None
        return Calibration(up, fwd)


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

    def add(self, a, dt_ms):
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
        self.count += 1
        self.elapsed += dt_ms
        if self.elapsed >= LEVEL_MS and self.count:
            self.result = normalize(scale(self.sum, 1.0 / self.count))
            return self.result is not None
        return False

    @property
    def progress(self):
        return min(1.0, self.elapsed / LEVEL_MS)


class ForwardStep:
    """Find the forward direction from a gentle straight-line acceleration."""

    def __init__(self, up):
        self.up = up
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
                self.result = Calibration(self.up, fwd)
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
