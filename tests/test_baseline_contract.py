import sys
import unittest
from types import SimpleNamespace
from unittest import mock


sys.modules.setdefault("hid", SimpleNamespace())

import device
import signals
import xzkj


class FakeHidHandle:
    def __init__(self, write_result=xzkj.REPORT_LEN):
        self.write_result = write_result
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)
        return self.write_result


class DeviceContractTests(unittest.TestCase):
    def test_resolves_key_targets_to_empirical_key_ids(self):
        self.assertEqual(device.resolve("key5"), 4)
        self.assertEqual(device.resolve("key10"), 11)
        self.assertEqual(device.resolve("key16"), 9)

    def test_resolves_knob_targets_to_empirical_key_ids(self):
        self.assertEqual(device.resolve("knob1.left"), 19)
        self.assertEqual(device.resolve("knob1.press"), 20)
        self.assertEqual(device.resolve("knob1.right"), 21)
        self.assertEqual(device.resolve("knob4.left"), 13)
        self.assertEqual(device.resolve("knob4.press"), 14)
        self.assertEqual(device.resolve("knob4.right"), 15)

    def test_all_targets_returns_24_bindable_controls(self):
        self.assertEqual(len(device.all_targets()), 24)

    def test_all_targets_lists_knobs_before_keys_in_physical_order(self):
        target_names = [target for target, _key_id, _description in device.all_targets()]
        self.assertEqual(
            target_names,
            [
                "knob1.left",
                "knob1.press",
                "knob1.right",
                "knob2.left",
                "knob2.press",
                "knob2.right",
                "knob3.left",
                "knob3.press",
                "knob3.right",
                "knob4.left",
                "knob4.press",
                "knob4.right",
                "key5",
                "key6",
                "key7",
                "key8",
                "key9",
                "key10",
                "key11",
                "key12",
                "key13",
                "key14",
                "key15",
                "key16",
            ],
        )


class SignalContractTests(unittest.TestCase):
    def test_defines_24_signal_targets(self):
        self.assertEqual(len(signals.TARGETS), 24)
        self.assertEqual(len(signals.SIGNALS), 24)

    def test_assigns_unique_signal_specs_to_each_target(self):
        self.assertEqual(len(set(signals.SIGNALS.values())), 24)
        self.assertEqual(signals.BY_SIGNAL, {value: key for key, value in signals.SIGNALS.items()})

    def test_assigns_representative_signal_specs(self):
        self.assertEqual(signals.spec_for("key5"), "f13")
        self.assertEqual(signals.spec_for("key12"), "f20")
        self.assertEqual(signals.spec_for("key13"), "ctrl+alt+f13")
        self.assertEqual(signals.spec_for("knob2.press"), "ctrl+shift+f13")
        self.assertEqual(signals.spec_for("knob2.right"), "ctrl+shift+f14")
        self.assertEqual(signals.spec_for("knob4.right"), "ctrl+shift+f20")

    def test_signal_key_ids_match_device_resolution(self):
        self.assertEqual(signals.key_id_for("key5"), device.resolve("key5"))
        self.assertEqual(signals.key_id_for("knob4.right"), device.resolve("knob4.right"))


class XzkjKeyboardFrameTests(unittest.TestCase):
    def test_bind_key_sequence_writes_padded_65_byte_keyboard_report(self):
        handle = FakeHidHandle()
        entries = [(0, xzkj.MODIFIERS["ctrl"]), (25, xzkj.HID_CODES["f13"])]

        with mock.patch.object(xzkj.time, "sleep"):
            xzkj.bind_key_sequence(handle, key_id=4, entries=entries, layer=1)

        self.assertEqual(len(handle.writes), 1)
        report = handle.writes[0]
        self.assertEqual(len(report), 65)
        self.assertEqual(
            report[:13],
            bytes([0x03, 0xFD, 0x04, 0x01, 0x01, 0x00, 0x02, 0x00, 0x00, 0xF1, 0x00, 0x19, 0x68]),
        )
        self.assertEqual(report[13:], bytes(52))

    def test_bind_key_sequence_rejects_empty_entries(self):
        handle = FakeHidHandle()

        with self.assertRaisesRegex(AssertionError, "1.18"):
            xzkj.bind_key_sequence(handle, key_id=4, entries=[], layer=1)

        self.assertEqual(handle.writes, [])


if __name__ == "__main__":
    unittest.main()
