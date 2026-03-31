#!/usr/bin/env python3
"""Genera un baseline 90d con métricas básicas (Brier, ECE, ROI, P&L)
desde los datos de muestra en `sample_data` o desde un JSON similar.
Guarda resultado en `backend/output/baseline_90d.json`.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional


def parse_score(match: Dict[str, Any]) -> Optional[Dict[str, int]]:
    # Intentar normalizar distintos campos de score que aparecen en muestras
    if "home_goals" in match and "away_goals" in match:
        return {"home": int(match["home_goals"]), "away": int(match["away_goals"])}
    if "home_score" in match and "away_score" in match:
        return {"home": int(match["home_score"]), "away": int(match["away_score"])}
    if "score" in match and isinstance(match["score"], dict):
        try:
            return {"home": int(match["score"].get("home", 0)), "away": int(match["score"].get("away", 0))}
        except Exception:
            return None
    return None


def outcome_home_win(score: Dict[str, int]) -> int:
    return 1 if score["home"] > score["away"] else 0


def brier_score(preds: List[float], truths: List[int]) -> float:
    if not preds:
        return float("nan")
    n = len(preds)
    return sum((p - y) ** 2 for p, y in zip(preds, truths)) / n


def ece(preds: List[float], truths: List[int], n_bins: int = 10) -> Dict[str, float]:
    # Expected Calibration Error (ECE) with equal-width bins
    import math

    if not preds:
        return {"ece": float("nan"), "mce": float("nan")}
    bins = [0.0 for _ in range(n_bins)]
    acc = [0.0 for _ in range(n_bins)]
    tot = len(preds)
    for p, y in zip(preds, truths):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx] += 1
        acc[idx] += y
    ece = 0.0
    mce = 0.0
    for i in range(n_bins):
        if bins[i] == 0:
            continue
        avg_p = ((i + 0.5) / n_bins)
        acc_i = acc[i] / bins[i]
        e = abs(acc_i - avg_p)
        ece += (bins[i] / tot) * e
        mce = max(mce, e)
    return {"ece": ece, "mce": mce}


def simulate_betting(preds: List[float], truths: List[int], threshold: float = 0.5) -> Dict[str, float]:
    # Simple strategy: bet 1 unit on home win when p > threshold, odds = 1/p
    stakes = 0
    pnl = 0.0
    wins = 0
    for p, y in zip(preds, truths):
        if p <= threshold:
            continue
        stakes += 1
        odds = 1.0 / p if p > 0 else 0.0
        if y == 1:
            profit = odds - 1.0
            wins += 1
        else:
            profit = -1.0
        pnl += profit
    roi = (pnl / stakes) if stakes > 0 else float("nan")
    win_rate = (wins / stakes) if stakes > 0 else float("nan")
    return {"stakes": stakes, "pnl": pnl, "roi": roi, "win_rate": win_rate}


def load_sample(path: Path) -> List[Dict[str, Any]]:
    with path.open() as f:
        return json.load(f)


def run(sample_path: Path, out_path: Path) -> Dict[str, Any]:
    data = load_sample(sample_path)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)

    preds = []
    truths = []
    included = []
    for doc in data:
        match = doc.get("data", {}).get("match", {})
        pred = doc.get("data", {}).get("prediction", {})
        match_date_s = match.get("match_date")
        if not match_date_s:
            continue
        try:
            match_date = datetime.fromisoformat(match_date_s.replace("Z", "+00:00"))
        except Exception:
            continue
        if match_date < cutoff:
            # skip older than 90 days
            continue
        score = parse_score(match)
        if not score:
            # not finished or no final score available
            continue
        p = pred.get("home_win_probability")
        if p is None:
            continue
        y = outcome_home_win(score)
        preds.append(float(p))
        truths.append(int(y))
        included.append({"match_id": doc.get("match_id"), "p": float(p), "y": int(y), "match_date": match_date_s})

    brier = brier_score(preds, truths)
    ece_res = ece(preds, truths)
    betting = simulate_betting(preds, truths, threshold=0.5)

    out = {
        "generated_at": now.isoformat(),
        "n_samples": len(included),
        "brier": brier,
        "ece": ece_res.get("ece"),
        "mce": ece_res.get("mce"),
        "betting": betting,
        "samples_preview": included[:50],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out, f, indent=2, default=str)

    return out


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    sample = base / "sample_data" / "match_predictions_sample.json"
    out = base / "output" / "baseline_90d.json"
    res = run(sample, out)
    print("Baseline generated:")
    print(json.dumps({k: res[k] for k in ("generated_at", "n_samples", "brier", "ece", "mce")}, indent=2))
    print("Saved to", out)
