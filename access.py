#!/usr/bin/env python3
"""
Access to read key presses on macOS.

An active event tap requires two permissions:

  Input Monitoring  (kTCCServiceListenEvent)  — to see events
  Accessibility     (kTCCServiceAccessibility) — to change or swallow them

Quartz can request Input Monitoring. Accessibility requires
AXIsProcessTrustedWithOptions, which pyobjc exposes only through
ApplicationServices — a module PyInstaller does not include. We therefore load
the framework directly from the system with ctypes. This works from source and a
bundled .app, and is the only call that actually adds the app to the list and
displays Apple's own dialog.
"""
import ctypes
import ctypes.util

import Quartz

_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("ApplicationServices"))
_cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))

_lib.AXIsProcessTrusted.restype = ctypes.c_bool
_lib.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
_lib.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]

_cf.CFDictionaryCreate.restype = ctypes.c_void_p
_cf.CFStringCreateWithCString.restype = ctypes.c_void_p
_cf.CFRelease.argtypes = [ctypes.c_void_p]

_kCFBooleanTrue = ctypes.c_void_p.in_dll(_cf, "kCFBooleanTrue")
_kCFTypeDictionaryKeyCallBacks = ctypes.c_void_p.in_dll(
    _cf, "kCFTypeDictionaryKeyCallBacks")
_kCFTypeDictionaryValueCallBacks = ctypes.c_void_p.in_dll(
    _cf, "kCFTypeDictionaryValueCallBacks")


def _cfstr(s: str):
    return _cf.CFStringCreateWithCString(None, s.encode(), 0x08000100)  # UTF-8


def accessibility(prompt=False) -> bool:
    """Check Accessibility. With prompt=True, macOS shows its dialog and adds
    the app to the list — the only way it can add itself."""
    if not prompt:
        return bool(_lib.AXIsProcessTrusted())
    key = _cfstr("AXTrustedCheckOptionPrompt")
    keys = (ctypes.c_void_p * 1)(key)
    vals = (ctypes.c_void_p * 1)(_kCFBooleanTrue)
    opts = _cf.CFDictionaryCreate(
        None, keys, vals, 1,
        ctypes.byref(_kCFTypeDictionaryKeyCallBacks),
        ctypes.byref(_kCFTypeDictionaryValueCallBacks))
    try:
        return bool(_lib.AXIsProcessTrustedWithOptions(opts))
    finally:
        _cf.CFRelease(opts)
        _cf.CFRelease(key)


def input_monitoring(prompt=False) -> bool:
    if Quartz.CGPreflightListenEventAccess():
        return True
    if prompt:
        return bool(Quartz.CGRequestListenEventAccess())
    return False


def status() -> dict:
    return {"accessibility": accessibility(),
            "input_monitoring": bool(Quartz.CGPreflightListenEventAccess())}


def have_all() -> bool:
    s = status()
    return s["accessibility"] and s["input_monitoring"]


def request_all() -> bool:
    """Request both permissions, showing Apple's dialogs and adding the app to both lists."""
    input_monitoring(prompt=True)
    accessibility(prompt=True)
    return have_all()


if __name__ == "__main__":
    print(status())
