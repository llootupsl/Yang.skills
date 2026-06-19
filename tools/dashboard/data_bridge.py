# 作者: 阿洋
"""Yang.skills v4 Dashboard 数据桥接器 - SQLite → JSON"""
import json
import os
import sys
import sqlite3
from datetime import datetime

def get_state_info():
    """Read .yang-state.json for meta info."""
    state_path = ".yang-state.json"
    if not os.path.exists(state_path):
        return {"project_name": "未初始化", "total_calibration_samples": 0}
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
    return {
        "project_name": state.get("project_name", "未知"),
        "total_calibration_samples": state.get("calibration_samples", 0),
    }

def build_data_json(output_path: str = None):
    """Build data.json from SQLite + state file."""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "data.json")
    
    state_info = get_state_info()
    
    v45_state = {}
    state_path = ".yang-state.json"
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                v45_state = json.load(f)
        except Exception:
            pass
    
    data = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "project_name": state_info.get("project_name", ""),
            "total_predictions": 0,
            "total_calibration_samples": state_info.get("total_calibration_samples", 0),
            "competitor_count": v45_state.get("competitor_count", 0),
            "monitor_enabled_competitors": v45_state.get("monitor_enabled_competitors", 0),
            "total_strategy_changes_detected": v45_state.get("total_strategy_changes_detected", 0),
        },
        "prediction_accuracy": [],
        "bucket_distribution": [],
        "competitor_radar": [],
        "topic_heatmap": [],
        "competitors": {
            "total": 0,
            "by_platform": {},
            "active_count": 0,
            "with_monitor_count": 0,
        },
        "strategy_changes": [],
        "landscape": None,
    }
    
    # Try to read from project_data.db
    db_path = "project_data.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get predictions for accuracy chart
            cursor.execute("SELECT * FROM predictions ORDER BY prediction_date DESC LIMIT 100")
            preds = [dict(row) for row in cursor.fetchall()]
            data["meta"]["total_predictions"] = len(preds)
            
            bucket_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for i, p in enumerate(preds):
                deviation = 0
                if p.get("actual_bucket") and p.get("predicted_bucket_A"):
                    buckets = ["A", "B", "C", "D"]
                    pred_values = [p.get(f"predicted_bucket_{b}", 0) for b in buckets]
                    pred_bucket = buckets[pred_values.index(max(pred_values))]
                    actual_idx = buckets.index(p["actual_bucket"])
                    pred_idx = buckets.index(pred_bucket)
                    deviation = pred_idx - actual_idx
                
                data["prediction_accuracy"].append({
                    "sample_id": i + 1,
                    "predicted_bucket": p.get("actual_bucket", "?") if not deviation else "?",
                    "actual_bucket": p.get("actual_bucket", "?"),
                    "deviation": deviation,
                    "date": p.get("prediction_date", "")[:10] if p.get("prediction_date") else "",
                })
                
                if p.get("actual_bucket"):
                    bucket_counts[p["actual_bucket"]] = bucket_counts.get(p["actual_bucket"], 0) + 1
            
            for b, count in bucket_counts.items():
                data["bucket_distribution"].append({
                    "bucket": b,
                    "predicted_count": count,
                    "actual_count": count,
                    "hit_rate": 0.0,
                })
            
            # Read competitor data
            try:
                # Competitor summary
                cursor.execute("SELECT platform, COUNT(*) as cnt FROM competitors WHERE is_active=1 GROUP BY platform")
                platform_rows = cursor.fetchall()
                by_platform = {}
                total_competitors = 0
                for row in platform_rows:
                    d = dict(row)
                    by_platform[d["platform"]] = d["cnt"]
                    total_competitors += d["cnt"]
                
                cursor.execute("SELECT COUNT(*) as cnt FROM competitors WHERE is_active=1")
                active_count = cursor.fetchone()["cnt"]
                
                cursor.execute("SELECT COUNT(DISTINCT competitor_id) as cnt FROM competitor_monitors WHERE is_enabled=1")
                with_monitor = cursor.fetchone()["cnt"]
                
                data["competitors"] = {
                    "total": total_competitors,
                    "by_platform": by_platform,
                    "active_count": active_count,
                    "with_monitor_count": with_monitor,
                }
                
                # Strategy changes (recent 20)
                cursor.execute("""
                    SELECT cs.change_type, cs.before_state, cs.after_state, cs.detected_at,
                           c.account_name, c.platform
                    FROM competitor_strategy_changes cs
                    JOIN competitors c ON cs.competitor_id = c.id
                    ORDER BY cs.detected_at DESC LIMIT 20
                """)
                changes = cursor.fetchall()
                data["strategy_changes"] = [
                    {
                        "competitor_name": row["account_name"],
                        "platform": row["platform"],
                        "change_type": row["change_type"],
                        "before": row["before_state"],
                        "after": row["after_state"],
                        "detected_at": row["detected_at"],
                    }
                    for row in changes
                ]
                
                # Landscape (most recent)
                cursor.execute("SELECT * FROM landscape_snapshots ORDER BY snapshot_date DESC LIMIT 1")
                landscape_row = cursor.fetchone()
                if landscape_row:
                    landscape_dict = dict(landscape_row)
                    try:
                        if landscape_dict.get("raw_json"):
                            data["landscape"] = json.loads(landscape_dict["raw_json"])
                        else:
                            data["landscape"] = {
                                "snapshot_date": landscape_dict.get("snapshot_date"),
                                "keyword": landscape_dict.get("keyword"),
                                "total_competitors": landscape_dict.get("total_competitors", 0),
                            }
                    except Exception:
                        data["landscape"] = {"snapshot_date": landscape_dict.get("snapshot_date")}
            except Exception as e:
                print(f"读取竞品数据时出错（非致命）: {e}", file=sys.stderr)
            
            conn.close()
        except Exception as e:
            print(f"读取数据库时出错: {e}", file=sys.stderr)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"数据已导出: {output_path} (预测: {data['meta']['total_predictions']} 条, 竞品: {data['competitors']['total']} 个)")
    return data

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else None
    build_data_json(output)