#!/usr/bin/env python3
"""
Compute and export baseline KPIs (90d) from MongoDB.
Writes output to: specs/definir-metrics/metrics_90d.json

Usage (inside project root or container where repo is mounted):
  python3 scripts/metrics_baseline.py
"""

import datetime
import json
import math
import os

from pymongo import MongoClient

try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

OUT_DIR = os.path.join("specs", "definir-metrics")
OUT_FILE = os.path.join(OUT_DIR, "metrics_90d.json")

FINISHED_STATUSES = ["FT", "AET", "PEN", "FT_PEN"]


def parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v
    if date_parser:
        try:
            return date_parser.parse(v)
        except Exception:
            pass
    try:
        # ISO-like: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
        return datetime.datetime.fromisoformat(v)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(v, fmt)
            except Exception:
                continue
    return None


def mean(xs):
    if not xs:
        return None
    return sum(xs) / float(len(xs))


def compute_brier(probs, labels):
    # probs, labels are lists of floats/ints (0/1)
    if not probs:
        return None
    return sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def compute_ece(probs, labels, n_bins=10):
    if not probs:
        return None
    bins = [[] for _ in range(n_bins)]
    total = len(probs)
    for p, y in zip(probs, labels):
        idx = int(min(n_bins - 1, math.floor(p * n_bins)))
        bins[idx].append((p, y))
    ece = 0.0
    for b in bins:
        if not b:
            continue
        avg_p = mean([pp for pp, _ in b])
        freq = mean([yy for _, yy in b])
        ece += abs(avg_p - freq) * (len(b) / total)
    return ece


def safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def main():  # noqa: C901
    uri = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@mongodb:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "bjj_betsports")
    client = MongoClient(uri)
    db = client[db_name]

    now = datetime.datetime.utcnow()
    cut_90 = now - datetime.timedelta(days=90)

    out = {"generated_at": now.isoformat(), "mongo_uri": uri, "db": db_name}

    # --- training_results summary ---
    tr = db["training_results"].find_one({"key": "latest_daily"})
    if tr and isinstance(tr.get("data"), dict):
        data = tr["data"]
        out["training_summary"] = {
            "matches_processed": data.get("matches_processed"),
            "correct_predictions": data.get("correct_predictions"),
            "accuracy": data.get("accuracy"),
            "total_bets": data.get("total_bets"),
            "roi": data.get("roi"),
            "profit_units": data.get("profit_units"),
            "pick_efficiency_sample": data.get("pick_efficiency", [])[:30],
            "roi_evolution_points": len(data.get("roi_evolution", [])),
        }
        # avg roi last 90d if roi_evolution has date entries
        roi_evo = data.get("roi_evolution", [])
        recent = []
        for e in roi_evo:
            d = None
            if isinstance(e, dict) and "date" in e:
                d = parse_date(e["date"])
            if d and d >= cut_90:
                recent.append(e)
        out["training_summary"]["recent_points_90d"] = len(recent)
        if recent:
            rois = [float(x.get("roi", 0)) for x in recent]
            out["training_summary"]["avg_roi_90d"] = mean(rois)
            out["training_summary"]["profit_change_90d"] = recent[-1].get(
                "profit", 0
            ) - recent[0].get("profit", 0)
    else:
        out["training_summary"] = None

    # --- labeled predictions analysis (if any finished matches exist) ---
    q = {"data.match.status": {"$in": FINISHED_STATUSES}}
    n_labeled = db["match_predictions"].count_documents(q)
    out["labeled"] = {"n_labeled": n_labeled}

    if n_labeled > 0:
        probs_home = []
        labels_home = []
        probs_draw = []
        labels_draw = []
        probs_away = []
        labels_away = []
        correct_preds = 0
        total_preds = 0
        league_counts = {}

        for doc in db["match_predictions"].find(q):
            data = doc.get("data", {})
            pred = data.get("prediction", {}) or {}
            match = data.get("match", {}) or {}
            # actual
            try:
                home_goals = match.get("home_goals")
                away_goals = match.get("away_goals")
                if home_goals is None or away_goals is None:
                    continue
                home_goals = int(home_goals)
                away_goals = int(away_goals)
            except Exception:
                continue
            actual_home = 1 if home_goals > away_goals else 0
            actual_draw = 1 if home_goals == away_goals else 0
            actual_away = 1 if away_goals > home_goals else 0

            # probabilities
            p_home = safe_get(pred, "home_win_probability")
            p_draw = safe_get(pred, "draw_probability")
            p_away = safe_get(pred, "away_win_probability")

            if p_home is not None:
                probs_home.append(float(p_home))
                labels_home.append(actual_home)
            if p_draw is not None:
                probs_draw.append(float(p_draw))
                labels_draw.append(actual_draw)
            if p_away is not None:
                probs_away.append(float(p_away))
                labels_away.append(actual_away)

            # predicted class accuracy (argmax among available probs)
            probs = []
            classes = []
            if p_home is not None:
                probs.append(float(p_home))
                classes.append("home")
            if p_draw is not None:
                probs.append(float(p_draw))
                classes.append("draw")
            if p_away is not None:
                probs.append(float(p_away))
                classes.append("away")
            if probs:
                pred_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
                pred_class = classes[pred_idx]
                if (
                    (pred_class == "home" and actual_home)
                    or (pred_class == "draw" and actual_draw)
                    or (pred_class == "away" and actual_away)
                ):
                    correct_preds += 1
                total_preds += 1

            lid = data.get("match", {}).get("league") or doc.get("league_id")
            if lid:
                league_counts[lid] = league_counts.get(lid, 0) + 1

        out["labeled"]["brier_home"] = compute_brier(probs_home, labels_home)
        out["labeled"]["brier_draw"] = compute_brier(probs_draw, labels_draw)
        out["labeled"]["brier_away"] = compute_brier(probs_away, labels_away)
        out["labeled"]["ece_home"] = compute_ece(probs_home, labels_home)
        out["labeled"]["ece_draw"] = compute_ece(probs_draw, labels_draw)
        out["labeled"]["ece_away"] = compute_ece(probs_away, labels_away)
        out["labeled"]["predicted_accuracy_1x2"] = (
            (correct_preds / total_preds) if total_preds else None
        )
        out["labeled"]["league_counts"] = league_counts
    else:
        out["labeled"]["note"] = (
            "No labeled finished matches found in match_predictions. "
            "Implement auto-labeling when matches finish."
        )

    # Ensure output dir
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    # Print concise summary
    print("Wrote:", OUT_FILE)
    print("Summary:")
    print("  training_summary present:", bool(out.get("training_summary")))
    print("  labeled matches:", out["labeled"].get("n_labeled"))
    if out["training_summary"]:
        print("  accuracy:", out["training_summary"].get("accuracy"))
        print("  total_bets:", out["training_summary"].get("total_bets"))
        print("  avg_roi_90d:", out["training_summary"].get("avg_roi_90d"))
    if out["labeled"] and out["labeled"].get("n_labeled"):
        print("  brier_home:", out["labeled"].get("brier_home"))
        print("  ece_home:", out["labeled"].get("ece_home"))
        print("  predicted_accuracy_1x2:", out["labeled"].get("predicted_accuracy_1x2"))
    else:
        print("  Note: No labeled finished matches to compute Brier/ECE.")


if __name__ == "__main__":
    main()
