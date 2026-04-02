#!/usr/bin/env python3
import asyncio
import importlib
import inspect
import json
import os
import pprint
import sys


def import_labeler_module():
    try:
        return importlib.import_module("src.application.services.auto_labeler")
    except Exception as e:
        print("IMPORT_ERROR", e)
        return None


def find_labeler_class(mod):
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if "Auto" in name or name.lower().startswith("auto"):
            return obj
    return None


def load_sample(sample_path: str):
    if not os.path.exists(sample_path):
        print("SAMPLE_NOT_FOUND", sample_path)
        return None
    with open(sample_path) as f:
        return json.load(f)


def _maybe_call(obj, method_name: str, data):
    """Call a method and if it returns a coroutine run it in asyncio."""
    fn = getattr(obj, method_name)
    try:
        res = fn(data)
        if asyncio.iscoroutine(res):
            return asyncio.run(res)
        return res
    except Exception:
        raise


def try_methods_on_labeler(al, data):
    # Try common methods first
    for method in (
        "dry_run",
        "label_batch",
        "label_predictions",
        "run",
        "execute",
        "process",
        "label",
    ):
        if hasattr(al, method):
            print("CALLING", method)
            try:
                res = _maybe_call(al, method, data)
                print("RESULT:")
                pprint.pprint(res)
                return 0
            except Exception as e:
                print("METHOD_FAILED", method, e)

    # Fallback: try public callable attributes
    methods = [m for m in dir(al) if callable(getattr(al, m)) and not m.startswith("_")]
    print("Available methods:", methods)
    for m in methods:
        try:
            print("TRYING", m)
            res = _maybe_call(al, m, data)
            print("CALLED", m, "-> result:")
            pprint.pprint(res)
            return 0
        except Exception as e:
            print("METHOD_FAILED", m, e)

    return None


def main():
    mod = import_labeler_module()
    if mod is None:
        return 1

    cls = find_labeler_class(mod)
    if not cls:
        print("AUTO_LABELER_CLASS_NOT_FOUND")
        return 2

    print("Found class:", cls.__name__)
    al = cls()

    sample = os.path.join("sample_data", "match_predictions_sample.json")
    data = load_sample(sample)
    if data is None:
        return 3

    print("Loaded", len(data), "items from", sample)

    res = try_methods_on_labeler(al, data)
    if res is None:
        print("NO_METHOD_EXECUTED")
        return 4
    return res


if __name__ == "__main__":
    sys.exit(main())
