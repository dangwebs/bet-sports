import importlib.util
import os
import sys
from types import SimpleNamespace

HERE = os.path.abspath(os.path.dirname(__file__))
SCRIPT_PATH = os.path.abspath(
    os.path.join(HERE, "..", "..", "scripts", "train_model_optimized.py")
)

spec = importlib.util.spec_from_file_location("train_model_optimized", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_parse_args_defaults():
    args = mod.parse_args([])
    assert args.days == 550
    assert args.n_jobs == -1
    assert args.league is None
    assert not args.force_retrain_per_league
    assert not args.no_timeout


def test_parse_args_custom():
    args = mod.parse_args(["--days", "10", "--league", "L1", "--n-jobs", "4"])
    assert args.days == 10
    assert args.league == "L1"
    assert args.n_jobs == 4


def test_group_matches_by_league():
    m1 = SimpleNamespace(league=SimpleNamespace(id="L1"))
    m2 = SimpleNamespace(league=SimpleNamespace(id="L2"))
    m3 = SimpleNamespace(league=SimpleNamespace(id="L1"))
    matches = [m1, m2, m3]

    grouped = mod.group_matches_by_league(matches)
    assert set(grouped.keys()) == {"L1", "L2"}
    assert grouped["L1"] == [m1, m3]
    assert grouped["L2"] == [m2]
