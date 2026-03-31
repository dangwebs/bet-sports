#!/usr/bin/env python3
import importlib
import inspect
import sys
import json
import pprint
import os


def main():
    try:
        mod = importlib.import_module("src.application.services.auto_labeler")
    except Exception as e:
        print("IMPORT_ERROR", e)
        return 1

    cls = None
    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if "Auto" in name or name.lower().startswith("auto"):
            cls = obj
            break
    if not cls:
        print("AUTO_LABELER_CLASS_NOT_FOUND")
        return 2

    print("Found class:", cls.__name__)
    al = cls()

    sample = os.path.join("sample_data", "match_predictions_sample.json")
    if not os.path.exists(sample):
        print("SAMPLE_NOT_FOUND", sample)
        return 3

    with open(sample) as f:
        data = json.load(f)

    print("Loaded", len(data), "items from", sample)

    # Try common methods
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
                res = getattr(al, method)(data)
                print("RESULT:")
                pprint.pprint(res)
                return 0
            except Exception as e:
                print("METHOD_FAILED", method, e)

    # Fallback: try callable methods that accept one arg
    methods = [m for m in dir(al) if callable(getattr(al, m)) and not m.startswith("_")]
    print("Available methods:", methods)
    for m in methods:
        try:
            print("TRYING", m)
            res = getattr(al, m)(data)
            print("CALLED", m, "-> result:")
            pprint.pprint(res)
            return 0
        except Exception as e:
            print("METHOD_FAILED", m, e)

    print("NO_METHOD_EXECUTED")
    return 4


if __name__ == "__main__":
    sys.exit(main())
