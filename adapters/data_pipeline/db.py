# 作者: 阿洋
"""Yang.skills v4 本地数据湖 CRUD 接口"""
from __future__ import annotations

import math
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = "project_data.db") -> None:
    try:
        schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        with _get_conn(db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()
    except Exception as e:
        print(f"[db] init_db failed: {e}", file=__import__("sys").stderr)


def insert_video(video: dict) -> str:
    try:
        if not video.get("id"):
            video["id"] = str(uuid.uuid4())
        fields = [
            "id", "url", "platform", "title", "author",
            "duration_sec", "publish_date", "local_path", "downloaded_at", "status",
        ]
        values = {f: video.get(f) for f in fields}
        sql = (
            "INSERT OR REPLACE INTO videos ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        db_path = video.pop("_db_path", "project_data.db")
        with _get_conn(db_path) as conn:
            conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return video["id"]
    except Exception as e:
        print(f"[db] insert_video failed: {e}", file=__import__("sys").stderr)
        return ""


def get_video(video_id: str, db_path: str = "project_data.db") -> dict | None:
    try:
        with _get_conn(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
        return row
    except Exception as e:
        print(f"[db] get_video failed: {e}", file=__import__("sys").stderr)
        return None


def insert_frames(video_id: str, frames: list[dict], db_path: str = "project_data.db") -> int:
    try:
        rows = [
            (
                video_id,
                f.get("frame_index", 0),
                f.get("timestamp_sec", 0.0),
                f.get("file_path", ""),
                f.get("visual_desc"),
                f.get("on_screen_text"),
                f.get("scene_change", 0),
            )
            for f in frames
        ]
        if not rows:
            return 0
        with _get_conn(db_path) as conn:
            conn.executemany(
                "INSERT INTO frames (video_id, frame_index, timestamp_sec, file_path, "
                "visual_desc, on_screen_text, scene_change) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        return len(rows)
    except Exception as e:
        print(f"[db] insert_frames failed: {e}", file=__import__("sys").stderr)
        return 0


def get_frames_by_video(video_id: str, db_path: str = "project_data.db") -> list[dict]:
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM frames WHERE video_id = ? ORDER BY frame_index",
                (video_id,),
            ).fetchall()
        return rows
    except Exception as e:
        print(f"[db] get_frames_by_video failed: {e}", file=__import__("sys").stderr)
        return []


def insert_comments(video_id: str, comments: list[dict], db_path: str = "project_data.db") -> int:
    try:
        rows = [
            (
                video_id,
                c.get("content", ""),
                c.get("likes", 0),
                c.get("reply_count", 0),
                c.get("sentiment"),
                c.get("scraped_at"),
            )
            for c in comments
        ]
        if not rows:
            return 0
        with _get_conn(db_path) as conn:
            conn.executemany(
                "INSERT INTO comments (video_id, content, likes, reply_count, sentiment, scraped_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        return len(rows)
    except Exception as e:
        print(f"[db] insert_comments failed: {e}", file=__import__("sys").stderr)
        return 0


def insert_prediction(pred: dict, db_path: str = "project_data.db") -> None:
    try:
        if not pred.get("id"):
            pred["id"] = str(uuid.uuid4())
        fields = [
            "id", "score_file", "predicted_bucket_A", "predicted_bucket_B",
            "predicted_bucket_C", "predicted_bucket_D", "actual_bucket", "actual_plays",
            "prediction_date", "retro_date",
        ]
        values = {f: pred.get(f) for f in fields}
        sql = (
            "INSERT OR REPLACE INTO predictions ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
    except Exception as e:
        print(f"[db] insert_prediction failed: {e}", file=__import__("sys").stderr)


def update_prediction_result(
    pred_id: str, actual_bucket: str, actual_plays: int, db_path: str = "project_data.db"
) -> None:
    try:
        with _get_conn(db_path) as conn:
            conn.execute(
                "UPDATE predictions SET actual_bucket = ?, actual_plays = ?, "
                "retro_date = datetime('now') WHERE id = ?",
                (actual_bucket, actual_plays, pred_id),
            )
            conn.commit()
    except Exception as e:
        print(f"[db] update_prediction_result failed: {e}", file=__import__("sys").stderr)


def get_predictions(limit: int = 100, db_path: str = "project_data.db") -> list[dict]:
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY prediction_date DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return rows
    except Exception as e:
        print(f"[db] get_predictions failed: {e}", file=__import__("sys").stderr)
        return []


def insert_trends(trends: list[dict], db_path: str = "project_data.db") -> int:
    try:
        rows = [
            (
                t.get("keyword", ""),
                t.get("platform", ""),
                t.get("rank"),
                t.get("heat_value"),
                t.get("url"),
                t.get("fetched_at"),
            )
            for t in trends
        ]
        if not rows:
            return 0
        with _get_conn(db_path) as conn:
            conn.executemany(
                "INSERT INTO trends (keyword, platform, rank, heat_value, url, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        return len(rows)
    except Exception as e:
        print(f"[db] insert_trends failed: {e}", file=__import__("sys").stderr)
        return 0


def export_to_json(output_path: str, db_path: str = "project_data.db") -> dict:
    tables = ["videos", "frames", "comments", "emotions", "predictions", "trends", "competitors", "competitor_snapshots", "competitor_strategy_changes", "landscape_snapshots", "competitor_monitors"]
    data: dict = {}
    try:
        with _get_conn(db_path) as conn:
            for table in tables:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                data[table] = rows
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return data
    except Exception as e:
        print(f"[db] export_to_json failed: {e}", file=__import__("sys").stderr)
        return {}


def insert_competitor(data: dict, db_path: str = "project_data.db") -> str:
    try:
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())
        fields = [
            "id", "account_name", "platform", "account_id", "account_url",
            "avatar_url", "bio", "verified", "category_tags", "discovery_source",
            "discovery_keyword", "first_seen_at", "last_updated_at", "is_active",
        ]
        values = {f: data.get(f) for f in fields}
        sql = (
            "INSERT OR REPLACE INTO competitors ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return data["id"]
    except Exception as e:
        print(f"[db] insert_competitor failed: {e}", file=__import__("sys").stderr)
        return ""


def insert_competitor_snapshot(competitor_id: str, data: dict, db_path: str = "project_data.db") -> int:
    try:
        fields = [
            "competitor_id", "snapshot_date", "follower_count", "total_likes",
            "total_videos", "avg_views_30d", "avg_likes_30d", "avg_comments_30d",
            "engagement_rate", "audience_insight", "content_trends", "raw_json",
        ]
        values = {f: data.get(f) for f in fields}
        values["competitor_id"] = competitor_id
        json_fields = {"audience_insight", "content_trends", "raw_json"}
        for jf in json_fields:
            if values[jf] is not None and not isinstance(values[jf], str):
                values[jf] = json.dumps(values[jf], ensure_ascii=False)
        sql = (
            "INSERT INTO competitor_snapshots ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            cursor = conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[db] insert_competitor_snapshot failed: {e}", file=__import__("sys").stderr)
        return 0


def get_competitor_snapshots(competitor_id: str, limit: int = 10, db_path: str = "project_data.db") -> list[dict]:
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM competitor_snapshots WHERE competitor_id = ? ORDER BY snapshot_date DESC LIMIT ?",
                (competitor_id, limit),
            ).fetchall()
        return rows
    except Exception as e:
        print(f"[db] get_competitor_snapshots failed: {e}", file=__import__("sys").stderr)
        return []


def get_all_competitors(platform: str = None, is_active: bool = True, db_path: str = "project_data.db") -> list[dict]:
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM competitors WHERE is_active = ? AND (platform = ? OR ? IS NULL)",
                (int(is_active), platform, platform),
            ).fetchall()
        for row in rows:
            if row.get("category_tags"):
                row["category_tags"] = [t.strip() for t in row["category_tags"].split(",") if t.strip()]
        return rows
    except Exception as e:
        print(f"[db] get_all_competitors failed: {e}", file=__import__("sys").stderr)
        return []


def detect_strategy_changes(competitor_id: str, current_snapshot: dict, previous_snapshot: dict, db_path: str = "project_data.db") -> dict:
    try:
        changes = []

        def _parse_json(raw):
            if not raw:
                return {}
            if isinstance(raw, dict):
                return raw
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}

        cur = _parse_json(current_snapshot.get("raw_json"))
        prev = _parse_json(previous_snapshot.get("raw_json"))

        cur_engagement = current_snapshot.get("engagement_rate")
        prev_engagement = previous_snapshot.get("engagement_rate")

        hook_cur = cur.get("hook_type")
        hook_prev = prev.get("hook_type")
        if hook_cur and hook_prev and hook_cur != hook_prev:
            changes.append({
                "change_type": "hook_type_shift",
                "before": hook_prev,
                "after": hook_cur,
                "significance": 0.6,
                "evidence": f"Hook type changed from '{hook_prev}' to '{hook_cur}'",
                "suggested_action": f"Review recent videos to analyze the '{hook_cur}' hook pattern and evaluate its effectiveness",
            })

        recent_cur = cur.get("recent_videos") or []
        recent_prev = prev.get("recent_videos") or []
        if recent_cur and recent_prev:
            avg_cur = sum(v.get("duration_sec", 0) for v in recent_cur) / len(recent_cur)
            avg_prev = sum(v.get("duration_sec", 0) for v in recent_prev) / len(recent_prev)
            if avg_prev > 0:
                diff = abs(avg_cur - avg_prev) / avg_prev
                if diff > 0.3:
                    direction = "increased" if avg_cur > avg_prev else "decreased"
                    changes.append({
                        "change_type": "duration_trend",
                        "before": round(avg_prev, 1),
                        "after": round(avg_cur, 1),
                        "significance": round(min(diff, 1.0), 2),
                        "evidence": f"Average video duration {direction} by {diff*100:.0f}% ({avg_prev:.1f}s → {avg_cur:.1f}s)",
                        "suggested_action": f"Consider adjusting video length to match the {direction} trend in competitor content",
                    })

        keywords_cur = set(cur.get("top_keywords") or [])
        keywords_prev = set(prev.get("top_keywords") or [])
        if keywords_cur and keywords_prev:
            intersection = keywords_cur & keywords_prev
            union = keywords_cur | keywords_prev
            jaccard = len(intersection) / len(union) if union else 1.0
            if jaccard < 0.5:
                new_kw = keywords_cur - keywords_prev
                old_kw = keywords_prev - keywords_cur
                changes.append({
                    "change_type": "topic_shift",
                    "before": ", ".join(sorted(keywords_prev)[:10]),
                    "after": ", ".join(sorted(keywords_cur)[:10]),
                    "significance": round(1.0 - jaccard, 2),
                    "evidence": f"Jaccard similarity={jaccard:.2f}, new topics: {', '.join(sorted(new_kw)[:5])}, dropped: {', '.join(sorted(old_kw)[:5])}",
                    "suggested_action": f"Evaluate whether to adopt new topics or double down on existing keyword strengths",
                })

        palette_cur = cur.get("color_palette")
        palette_prev = prev.get("color_palette")
        if palette_cur and palette_prev:
            if isinstance(palette_cur, dict) and isinstance(palette_prev, dict):
                all_colors = set(list(palette_cur.keys()) + list(palette_prev.keys()))
                if all_colors:
                    curr_dist = [palette_cur.get(c, 0) for c in sorted(all_colors)]
                    prev_dist = [palette_prev.get(c, 0) for c in sorted(all_colors)]
                    curr_sum = sum(curr_dist) or 1
                    prev_sum = sum(prev_dist) or 1
                    curr_norm = [v / curr_sum for v in curr_dist]
                    prev_norm = [v / prev_sum for v in prev_dist]
                    kl_divergence = sum(
                        p * math.log((p + 1e-10) / (q + 1e-10))
                        for p, q in zip(curr_norm, prev_norm) if p > 0
                    )
                    if kl_divergence > 0.3:
                        changes.append({
                            "change_type": "style_change",
                            "before": str(palette_prev),
                            "after": str(palette_cur),
                            "significance": round(min(kl_divergence / 0.6, 1.0), 2),
                            "evidence": f"Color palette distribution KL divergence={kl_divergence:.3f}, exceeds threshold 0.3",
                            "suggested_action": "Check if style change is due to platform algorithm shift, audience preference change, or intentional competitor pivot",
                        })
            elif palette_cur != palette_prev:
                changes.append({
                    "change_type": "style_change",
                    "before": str(palette_prev)[:100],
                    "after": str(palette_cur)[:100],
                    "significance": 0.5,
                    "evidence": "Color palette has been modified (non-distribution format, using direct comparison)",
                    "suggested_action": "Review recent videos to assess visual style changes and their impact on engagement",
                })

        freq_cur = cur.get("publish_count_14d")
        freq_prev = prev.get("publish_count_14d")
        if freq_cur is not None and freq_prev is not None and freq_prev > 0:
            diff = abs(freq_cur - freq_prev) / freq_prev
            if diff > 0.5:
                direction = "increased" if freq_cur > freq_prev else "decreased"
                changes.append({
                    "change_type": "frequency_change",
                    "before": freq_prev,
                    "after": freq_cur,
                    "significance": round(min(diff, 1.0), 2),
                    "evidence": f"Publish frequency {direction} by {diff*100:.0f}% ({freq_prev} → {freq_cur} posts/14d)",
                    "suggested_action": f"Monitor whether the {direction} publish frequency affects engagement metrics",
                })

        catch_cur = set(cur.get("catchphrases") or [])
        catch_prev = set(prev.get("catchphrases") or [])
        catch_all = catch_cur | catch_prev
        if catch_all:
            stale = catch_prev - catch_cur
            change_rate = len(stale) / len(catch_all)
            if change_rate > 0.4:
                changes.append({
                    "change_type": "persona_drift",
                    "before": ", ".join(sorted(catch_prev)[:10]),
                    "after": ", ".join(sorted(catch_cur)[:10]),
                    "significance": round(change_rate, 2),
                    "evidence": f"Catchphrase change rate={change_rate:.2f}, dropped phrases: {', '.join(sorted(stale)[:5])}",
                    "suggested_action": "Assess whether the persona drift is intentional rebranding or signals a content pivot",
                })

        if cur_engagement is not None and prev_engagement is not None and prev_engagement > 0:
            eng_diff = (cur_engagement - prev_engagement) / prev_engagement
            if eng_diff < -0.4:
                changes.append({
                    "change_type": "engagement_drop",
                    "before": round(prev_engagement, 4),
                    "after": round(cur_engagement, 4),
                    "significance": round(min(abs(eng_diff), 1.0), 2),
                    "evidence": f"Engagement rate dropped by {abs(eng_diff)*100:.0f}% ({prev_engagement:.4f} → {cur_engagement:.4f})",
                    "suggested_action": "Investigate recent content for potential causes of engagement decline",
                })
            elif eng_diff > 0.8:
                changes.append({
                    "change_type": "engagement_spike",
                    "before": round(prev_engagement, 4),
                    "after": round(cur_engagement, 4),
                    "significance": round(min(eng_diff, 1.0), 2),
                    "evidence": f"Engagement rate rose by {eng_diff*100:.0f}% ({prev_engagement:.4f} → {cur_engagement:.4f})",
                    "suggested_action": "Analyze recent viral content to identify replicable engagement drivers",
                })

        all_change_types = {
            "hook_type_shift", "duration_trend", "topic_shift",
            "style_change", "frequency_change", "persona_drift",
            "engagement_drop", "engagement_spike"
        }
        changed_types = {c["change_type"] for c in changes}
        stable_dimensions = sorted(all_change_types - changed_types)

        return {
            "detected_changes": changes,
            "stable_dimensions": stable_dimensions,
            "comparison_base": {
                "snapshot_current_id": current_snapshot.get("id") if isinstance(current_snapshot, dict) else None,
                "snapshot_previous_id": previous_snapshot.get("id") if isinstance(previous_snapshot, dict) else None,
                "snapshot_current_date": current_snapshot.get("snapshot_date") if isinstance(current_snapshot, dict) else None,
                "snapshot_previous_date": previous_snapshot.get("snapshot_date") if isinstance(previous_snapshot, dict) else None,
            }
        }
    except Exception as e:
        print(f"[db] detect_strategy_changes failed: {e}", file=__import__("sys").stderr)
        return {"detected_changes": [], "stable_dimensions": [], "comparison_base": {}}


def insert_strategy_change(competitor_id: str, change_data: dict, db_path: str = "project_data.db") -> int:
    try:
        fields = [
            "competitor_id", "change_type", "before_state", "after_state",
            "significance", "summary",
        ]
        values = {f: change_data.get(f) for f in fields}
        values["competitor_id"] = competitor_id
        sql = (
            "INSERT INTO competitor_strategy_changes ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            cursor = conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[db] insert_strategy_change failed: {e}", file=__import__("sys").stderr)
        return 0


def insert_landscape_snapshot(keyword: str, data: dict, db_path: str = "project_data.db") -> int:
    try:
        fields = [
            "keyword", "total_competitors", "hook_type_distribution",
            "duration_distribution", "topic_heatmap", "blue_ocean_signals", "raw_json",
        ]
        values = {f: data.get(f) for f in fields}
        values["keyword"] = keyword
        json_fields = {
            "hook_type_distribution", "duration_distribution",
            "topic_heatmap", "blue_ocean_signals", "raw_json",
        }
        for jf in json_fields:
            if values[jf] is not None and not isinstance(values[jf], str):
                values[jf] = json.dumps(values[jf], ensure_ascii=False)
        sql = (
            "INSERT INTO landscape_snapshots ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            cursor = conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[db] insert_landscape_snapshot failed: {e}", file=__import__("sys").stderr)
        return 0


def insert_competitor_monitor(competitor_id: str, config: dict, db_path: str = "project_data.db") -> int:
    try:
        fields = [
            "competitor_id", "rss_url", "platform_monitor_type",
            "check_interval_hours", "is_enabled",
        ]
        values = {f: config.get(f) for f in fields}
        values["competitor_id"] = competitor_id
        sql = (
            "INSERT INTO competitor_monitors ("
            + ", ".join(fields)
            + ") VALUES ("
            + ", ".join("?" for _ in fields)
            + ")"
        )
        with _get_conn(db_path) as conn:
            cursor = conn.execute(sql, tuple(values[f] for f in fields))
            conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"[db] insert_competitor_monitor failed: {e}", file=__import__("sys").stderr)
        return 0


def get_active_monitors(db_path: str = "project_data.db") -> list[dict]:
    try:
        with _get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM competitor_monitors WHERE is_enabled = 1"
            ).fetchall()
        return rows
    except Exception as e:
        print(f"[db] get_active_monitors failed: {e}", file=__import__("sys").stderr)
        return []


def get_competitor_by_id(competitor_id: str, db_path: str = "project_data.db") -> dict:
    try:
        with _get_conn(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM competitors WHERE id = ?", (competitor_id,)
            ).fetchone()
        return row
    except Exception as e:
        print(f"[db] get_competitor_by_id failed: {e}", file=__import__("sys").stderr)
        return None