"""Tests for the autox app's calibration maths and run log format.

Run with: python3 tools/autox/test_autox.py
"""

import math
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "badge", "apps", "autox"))

import runlog  # noqa: E402
import vehicle  # noqa: E402


def rotate(v, axis, degrees):
    """Rotate vector v around a unit axis (Rodrigues)."""
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    k = axis
    kv = vehicle.cross(k, v)
    kd = vehicle.dot(k, v)
    return tuple(v[i] * c + kv[i] * s + k[i] * kd * (1 - c) for i in range(3))


def mounted(up, fwd):
    """Return a function that turns car-frame accel (fwd, left, up in g) into
    what a badge mounted with the given up/fwd axes would read."""
    left = vehicle.cross(up, fwd)

    def read(forward_g, left_g):
        # accelerometer reads specific force: kinematic accel + 1 g up
        return tuple(fwd[i] * forward_g + left[i] * left_g + up[i] for i in range(3))

    return read


def calibrate(read, still_frames=200, dt=11):
    level = vehicle.LevelStep()
    for _ in range(still_frames):
        if level.add(read(0, 0), dt):
            break
    assert level.result is not None, "level step did not finish"
    step = vehicle.ForwardStep(level.result)
    for _ in range(200):
        if step.add(read(0.25, 0), dt):
            break
    assert step.result is not None, "forward step did not finish"
    return step.result


MOUNTS = {
    "flat, screen up": ((0, 0, -1), (1, 0, 0)),
    "upright on dash": ((0, -1, 0), (0, 0, 1)),
    "tilted 30 deg, yawed 45 deg": (
        rotate(rotate((0, 0, 1), (1, 0, 0), 30), (0, 0, 1), 45),
        rotate(rotate((0, 1, 0), (1, 0, 0), 30), (0, 0, 1), 45),
    ),
}


class CalibrationTests(unittest.TestCase):
    def test_mounts(self):
        for name, (up, fwd) in MOUNTS.items():
            with self.subTest(name):
                read = mounted(up, fwd)
                cal = calibrate(read)
                for forward_g, left_g in ((0.8, 0), (-1.1, 0), (0, 1.2), (0, -0.9), (0.4, -0.6)):
                    lat, lon = cal.car_g(read(forward_g, left_g))
                    self.assertAlmostEqual(lon, forward_g, places=4)
                    self.assertAlmostEqual(lat, left_g, places=4)

    def test_level_rejects_shaking(self):
        level = vehicle.LevelStep()
        level.add((0, 0, 1), 11)
        level.add((0.2, 0, 1), 11)
        self.assertTrue(level.too_shaky)
        self.assertIsNone(level.result)

    def test_forward_ignores_small_motion(self):
        step = vehicle.ForwardStep((0, 0, 1))
        for _ in range(200):
            self.assertFalse(step.add((0.05, 0, 1), 11))

    def test_round_trip_list(self):
        cal = calibrate(mounted(*MOUNTS["upright on dash"]))
        again = vehicle.Calibration.from_list(cal.to_list())
        self.assertEqual(again.car_g((0.3, 0.2, 0.9)), cal.car_g((0.3, 0.2, 0.9)))
        self.assertIsNone(vehicle.Calibration.from_list([]))

    def test_peaks(self):
        peaks = vehicle.Peaks()
        for lat, lon in ((0.5, 0), (-0.7, 0), (0, 0.3), (0, -1.0)):
            peaks.add(lat, lon)
        self.assertEqual((peaks.left, peaks.right, peaks.accel, peaks.brake), (0.5, 0.7, 0.3, 1.0))

    def test_smoother_frame_rate_independent(self):
        a, b = vehicle.Smoother(), vehicle.Smoother()
        a.add((0, 0), 10)
        b.add((0, 0), 10)
        for _ in range(10):
            a.add((1, 1), 10)
        for _ in range(5):
            b.add((1, 1), 20)
        self.assertAlmostEqual(a.value[0], b.value[0], places=6)


class RelevelTests(unittest.TestCase):
    def tipped(self, up, fwd, axis, degrees):
        return rotate(up, axis, degrees), rotate(fwd, axis, degrees)

    def test_relevel_recovers_after_tip(self):
        up, fwd = MOUNTS["upright on dash"]
        cal = calibrate(mounted(up, fwd))
        left = vehicle.cross(up, fwd)
        for name, axis in (("pitch", left), ("roll", fwd)):
            with self.subTest(name):
                up2, fwd2 = self.tipped(up, fwd, axis, 25)
                read = mounted(up2, fwd2)
                # stale calibration leaks gravity into the readings
                self.assertGreater(max(abs(x) for x in cal.car_g(read(0, 0))), 0.3)
                fixed = vehicle.relevel(cal, vehicle.normalize(read(0, 0)))
                for forward_g, left_g in ((0.6, 0), (-0.9, 0), (0, 0.8), (0.3, -0.5)):
                    lat, lon = fixed.car_g(read(forward_g, left_g))
                    self.assertAlmostEqual(lon, forward_g, places=3)
                    self.assertAlmostEqual(lat, left_g, places=3)

    def test_calibration_list_with_gyro_bias(self):
        cal = vehicle.Calibration((0, 0, 1), (1, 0, 0), (185.0, -646.0, -248.0))
        again = vehicle.Calibration.from_list(cal.to_list())
        self.assertEqual(again.gyro_bias, (185.0, -646.0, -248.0))
        self.assertEqual(len(cal.axes()), 6)
        self.assertIsNone(vehicle.Calibration.from_list([0, 0, 1, 1, 0, 0]).gyro_bias)


class StillTrackerTests(unittest.TestCase):
    BIAS = (185.0, -646.0, -248.0)  # measured on the badge at rest

    def feed(self, tracker, accel, gyro, seconds=1.5, dt=23):
        t = 0
        i = 0
        while t < seconds * 1000:
            tracker.add(accel(i), gyro(i), dt)
            t += dt
            i += 1

    def idle_vibration(self, i):
        wobble = 0.03 * math.sin(i * 1.7)
        return (wobble, 0.0, 1.0 - wobble)

    def test_still_with_idle_vibration(self):
        tr = vehicle.StillTracker()
        self.feed(tr, self.idle_vibration, lambda i: self.BIAS)
        up = tr.still_up(self.BIAS)
        self.assertIsNotNone(up)
        self.assertLess(vehicle.angle_deg(up, (0, 0, 1)), 2)

    def test_steady_cornering_is_not_still(self):
        # 0.2 g lateral looks almost like gravity, but the car is turning at 30 dps
        yaw = vehicle.GYRO_COUNTS_PER_DPS * 30
        tr = vehicle.StillTracker()
        lean = vehicle.normalize((0.2, 0, 1.0))
        self.feed(tr, lambda i: lean, lambda i: (self.BIAS[0], self.BIAS[1], self.BIAS[2] + yaw))
        self.assertIsNone(tr.still_up(self.BIAS))

    def test_accelerating_is_not_still(self):
        tr = vehicle.StillTracker()
        self.feed(tr, lambda i: (0.3, 0, 1.0), lambda i: self.BIAS)
        self.assertIsNone(tr.still_up(self.BIAS))

    def test_bumps_are_not_still(self):
        tr = vehicle.StillTracker()
        self.feed(tr, lambda i: (0, 0, 1.0 + (0.3 if i % 7 == 0 else 0)), lambda i: self.BIAS)
        self.assertIsNone(tr.still_up(self.BIAS))

    def test_unknown_bias_uses_gyro_steadiness(self):
        tr = vehicle.StillTracker()
        self.feed(tr, self.idle_vibration, lambda i: self.BIAS)
        self.assertIsNotNone(tr.still_up(None))
        tr = vehicle.StillTracker()
        swing = vehicle.GYRO_COUNTS_PER_DPS * 20
        self.feed(tr, self.idle_vibration, lambda i: (self.BIAS[0] + swing * math.sin(i / 10), self.BIAS[1], self.BIAS[2]))
        self.assertIsNone(tr.still_up(None))

    def test_needs_a_full_second(self):
        tr = vehicle.StillTracker()
        self.feed(tr, self.idle_vibration, lambda i: self.BIAS, seconds=0.6)
        self.assertIsNone(tr.still_up(self.BIAS))


class LogFormatTests(unittest.TestCase):
    def test_decode(self):
        cal = [0, 0, 1, 1, 0, 0]
        data = struct.pack(runlog.HEADER, runlog.MAGIC, runlog.VERSION, *(cal + [1234]))
        samples = [(11, 100, -200, 16384), (12, -32768, 32767, 0)]
        for s in samples:
            data += struct.pack(runlog.RECORD, *s)
        up, fwd, start, rows = runlog.decode(data)
        self.assertEqual(tuple(up), (0, 0, 1))
        self.assertEqual(tuple(fwd), (1, 0, 0))
        self.assertEqual(start, 1234)
        self.assertEqual(rows, [(11, 100, -200, 16384), (23, -32768, 32767, 0)])
        self.assertEqual(runlog.RECORD_SIZE, 8)

    def test_decode_rejects_other_files(self):
        with self.assertRaises(ValueError):
            runlog.decode(b"nope" + bytes(40))


class ExportSafetyTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, HERE)
        import export
        self.export = export

    def test_run_names_from_badge_are_filtered(self):
        names = ["run-0001.axr", "../../evil.axr", "..run-0002.axr", "run-12.axr",
                 "run-0003.axr.part", 5, "run-0004.axr"]
        self.assertEqual(self.export.safe_run_names(names), ["run-0001.axr", "run-0004.axr"])

    def test_port_must_be_a_device(self):
        self.assertEqual(self.export.safe_port("/dev/cu.usbmodem101"), "/dev/cu.usbmodem101")
        self.assertEqual(self.export.safe_port("COM3"), "COM3")
        for bad in ("-x", "--help", "/dev/../etc"):
            with self.assertRaises(SystemExit):
                self.export.safe_port(bad)

    def test_out_dir_stays_inside_cwd(self):
        self.assertTrue(self.export.safe_out_dir("autox-runs").startswith(os.path.realpath(os.getcwd())))
        for bad in ("../evil", "/tmp/x"):
            with self.assertRaises(SystemExit):
                self.export.safe_out_dir(bad)


if __name__ == "__main__":
    unittest.main()
