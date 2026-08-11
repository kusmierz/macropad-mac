import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


sys.modules.setdefault("hid", SimpleNamespace())

import device
import macroctl
import signals
import store
import xzkj


if "Quartz" not in sys.modules:
    sys.modules["Quartz"] = SimpleNamespace(
        kCGEventFlagMaskControl=1, kCGEventFlagMaskShift=2,
        kCGEventFlagMaskAlternate=4, kCGEventFlagMaskCommand=8,
    )
if "AppKit" not in sys.modules:
    sys.modules["AppKit"] = SimpleNamespace(NSWorkspace=object)
import daemon


class FakeHidHandle:
    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)
        return xzkj.REPORT_LEN


class SixteenKeyModelTests(unittest.TestCase):
    def test_target_and_id_map(self):
        model = device.get(device.MODEL_16_3)
        self.assertEqual(len(model.targets()), 25)
        self.assertEqual(model.targets()[:3], ["key1", "key2", "key3"])
        self.assertEqual(model.targets()[-1], "knob3.right")
        self.assertEqual(device.resolve("key16", model.id), 16)
        self.assertEqual(device.resolve("knob1.left", model.id), 17)
        self.assertEqual(device.resolve("knob3.right", model.id), 25)
        self.assertEqual(model.knob_sizes, {1: "small", 2: "small", 3: "large"})

    def test_signal_map_has_25_unique_values_and_fourth_tier(self):
        mapping = signals.signal_map(device.MODEL_16_3)
        self.assertEqual(len(mapping), 25)
        self.assertEqual(len(set(mapping.values())), 25)
        self.assertEqual(mapping["key1"], "f13")
        self.assertEqual(mapping["key16"], "ctrl+alt+f20")
        self.assertEqual(mapping["knob3.right"], "alt+shift+f13")


class StoreMigrationTests(unittest.TestCase):
    def test_fresh_store_requires_model_selection(self):
        doc = store.normalize({}, fresh=True)
        self.assertIsNone(doc["active_model"])

    def test_legacy_profiles_are_scoped_to_current_model(self):
        doc = store.normalize({"active": "Profil 1", "profiles": {
            "Profil 1": {"default": {"key5": "key:cmd+c"}, "apps": {}}
        }})
        self.assertEqual(doc["active_model"], device.MODEL_12_4)
        self.assertEqual(doc["models"][device.MODEL_12_4]["active"], "Profile 1")
        self.assertEqual(doc["models"][device.MODEL_12_4]["profiles"]["Profile 1"]["default"]["key5"], "key:cmd+c")
        self.assertNotIn("Profil 1", doc["models"][device.MODEL_12_4]["profiles"])
        self.assertEqual(doc["models"][device.MODEL_16_3]["profiles"]["Profile 1"]["default"], {})

    def test_model_profiles_do_not_share_mappings(self):
        doc = store.normalize({})
        doc["models"][device.MODEL_12_4]["profiles"]["Profile 1"]["default"]["key5"] = "key:cmd+c"
        doc["active_model"] = device.MODEL_16_3
        self.assertEqual(store.active_map(doc)["default"], {})


class DaemonFirstRunTests(unittest.TestCase):
    def test_unselected_model_does_not_claim_or_dispatch_signals(self):
        daemon_instance = daemon.Daemon.__new__(daemon.Daemon)
        daemon_instance.model_id = None
        daemon_instance.profiles = store.normalize({}, fresh=True)
        self.assertIsNone(daemon_instance.target_for_signal("f13"))
        self.assertEqual(daemon_instance.action_for("key1", "com.example.app"), (None, None))


class MacroctlModelTests(unittest.TestCase):
    def test_loads_16_key_layout(self):
        config = """model: xzkj_16key_3knob\nkeys:\n  - [a, b, c, d]\n  - [e, f, g, h]\n  - [i, j, k, l]\n  - [m, n, o, p]\nknobs:\n  3: {press: enter}\n"""
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(config)
            path = f.name
        try:
            model, layer, bindings = macroctl.load_config(path)
        finally:
            os.unlink(path)
        self.assertEqual(model.id, device.MODEL_16_3)
        self.assertEqual(layer, 1)
        self.assertEqual(bindings[0][0], 1)
        self.assertEqual(bindings[-1][0], 24)

    def test_16_key_media_and_mouse_frames_use_captured_format(self):
        handle = FakeHidHandle()
        with mock.patch.object(xzkj.time, "sleep"):
            xzkj.bind_media(handle, 17, 0xCD, protocol="16_3")
            xzkj.bind_mouse_click(handle, 25, 1, protocol="16_3")
        self.assertEqual(handle.writes[0][:13], bytes([3, 0xFD, 17, 1, 2, 0, 2, 0, 0, 0xCD, 0, 0, 0]))
        self.assertEqual(handle.writes[1][:13], bytes([3, 0xFD, 25, 1, 3, 1, 4, 0, 0, 0, 0, 0, 1]))


if __name__ == "__main__":
    unittest.main()
