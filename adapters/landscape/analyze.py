# 作者: 阿洋
"""Yang.skills 赛道格局分析 - 跨竞品汇总与蓝海信号检测"""
from __future__ import annotations

import argparse
import json
import os
import sys
import importlib
import statistics
from datetime import datetime, timezone

_current_dir = os.path.dirname(os.path.abspath(__file__))
_adapter_dir = os.path.dirname(_current_dir)
if _adapter_dir not in sys.path:
    sys.path.insert(0, _adapter_dir)
db = importlib.import_module('data_pipeline.db')

PROJECT_ROOT = os.path.dirname(os.path.dirname(_adapter_dir))
STATE_FILE = os.path.join(PROJECT_ROOT, '.yang-state.json')

HOOK_TYPES = ['suspense', 'conflict', 'empathy', 'benefit', 'anti_common_sense', 'other']
HOOK_LABELS_CN = {
    'suspense': '\u60ac\u5ff5\u578b',
    'conflict': '\u51b2\u7a81\u578b',
    'empathy': '\u5171\u60c5\u578b',
    'benefit': '\u5229\u76ca\u578b',
    'anti_common_sense': '\u53cd\u5e38\u8bc6\u578b',
    'other': '\u5176\u4ed6\u578b',
}


def _parse_json_field(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _match_keyword(competitor, keyword):
    keyword_lower = keyword.lower()
    discovery_kw = (competitor.get('discovery_keyword') or '').lower()
    if keyword_lower in discovery_kw:
        return True
    category_tags = competitor.get('category_tags', [])
    if isinstance(category_tags, str):
        try:
            category_tags = json.loads(category_tags)
        except (json.JSONDecodeError, TypeError):
            category_tags = [t.strip() for t in category_tags.split(',') if t.strip()]
    if isinstance(category_tags, list):
        for tag in category_tags:
            if keyword_lower in (tag or '').lower():
                return True
    return False


def _compute_blue_ocean_score(angle_candidates, total_competitors):
    results = []
    for angle in angle_candidates:
        topic = angle.get('topic', '')
        competitor_count = angle.get('competitor_count', 0)
        avg_engagement = angle.get('avg_engagement', 0.0)
        saturation_norm = competitor_count / max(total_competitors, 1)
        trend_dir = angle.get('trend_direction', 'stable')
        trend_score = {'rising': 1.0, 'stable': 0.5, 'falling': 0.0}.get(trend_dir, 0.5)
        engagement_norm = min(avg_engagement / 0.1, 1.0) if avg_engagement is not None and avg_engagement > 0 else 0.5
        knowledge_match = 0.5
        score = (
            0.4 * (1.0 - saturation_norm)
            + 0.3 * engagement_norm
            + 0.2 * trend_score
            + 0.1 * knowledge_match
        )
        results.append({
            'angle': topic,
            'reason': f"\u9971\u548c\u5ea6={saturation_norm:.2f}, \u8d8b\u52bf={trend_dir}, \u4e92\u52a8\u7387={avg_engagement:.4f}",
            'confidence': round(score, 4),
        })
    results.sort(key=lambda x: x['confidence'], reverse=True)
    return results[:5]


def run_landscape_analysis(keyword, output_path=None, db_path="project_data.db"):
    now_iso = datetime.now(timezone.utc).isoformat()

    all_competitors = db.get_all_competitors(is_active=True, db_path=db_path)
    if not all_competitors:
        msg = f"\u6570\u636e\u5e93\u4e2d\u65e0\u7ade\u54c1\u6570\u636e\u3002\u8bf7\u5148\u8fd0\u884c yang-competitor-search \u53d1\u73b0\u7ade\u54c1\u3002"
        print(msg)
        return None

    matched = [c for c in all_competitors if _match_keyword(c, keyword)]
    if len(matched) < 3:
        msg = f"\u9700\u8981\u81f3\u5c11 3 \u4e2a\u7ade\u54c1\u6570\u636e\u624d\u80fd\u8fdb\u884c\u8d5b\u9053\u683c\u5c40\u5206\u6790\uff0c\u5f53\u524d\u4ec5\u6709 {len(matched)} \u4e2a"
        print(msg)
        return None

    snapshots_data = []
    for comp in matched:
        comp_id = comp['id']
        snaps = db.get_competitor_snapshots(comp_id, limit=1, db_path=db_path)
        if snaps:
            snap = snaps[0]
            raw = _parse_json_field(snap.get('raw_json'))
            snapshots_data.append({
                'competitor': comp,
                'snapshot': snap,
                'parsed': raw,
            })

    if not snapshots_data:
        print(f"\u672a\u627e\u5230\u5bf9\u5e94\u7ade\u54c1\u7684\u5feb\u7167\u6570\u636e")
        return None

    hook_counts = {ht: 0 for ht in HOOK_TYPES}
    for sd in snapshots_data:
        raw = sd['parsed']
        hook_type = raw.get('hook_type', 'other')
        if hook_type not in hook_counts:
            hook_type = 'other'
        hook_counts[hook_type] += 1

    total_with_hooks = max(sum(hook_counts.values()), 1)
    hook_pcts = {}
    for ht in HOOK_TYPES:
        hook_pcts[ht] = round(hook_counts[ht] / total_with_hooks * 100, 1)

    min_hook_type = min(HOOK_TYPES, key=lambda h: hook_counts[h])
    blue_ocean_hook = HOOK_LABELS_CN.get(min_hook_type, min_hook_type)

    all_durations = []
    for sd in snapshots_data:
        raw = sd['parsed']
        recent_videos = raw.get('recent_videos', [])
        if not isinstance(recent_videos, list):
            recent_videos = []
        for video in recent_videos:
            dur = video.get('duration_sec')
            if dur is not None:
                try:
                    dur_val = float(dur)
                    if dur_val > 0:
                        all_durations.append(dur_val)
                except (ValueError, TypeError):
                    pass

    if all_durations:
        avg_dur = round(sum(all_durations) / len(all_durations), 1)
        med_dur = round(statistics.median(all_durations), 1)
        dur_min = min(all_durations)
        dur_max = max(all_durations)
        optimal_min = round(max(dur_min, med_dur * 0.7), 1)
        optimal_max = round(max(min(dur_max, med_dur * 1.5), optimal_min + 1.0), 1)
    else:
        avg_dur = 0.0
        med_dur = 0.0
        dur_min = 0.0
        dur_max = 0.0
        optimal_min = 0.0
        optimal_max = 0.0

    duration_trend = 'stable'
    for sd in snapshots_data:
        raw = sd['parsed']
        raw_trend = raw.get('duration_trend', '')
        if raw_trend in ('shortening', 'lengthening', 'stable'):
            if raw_trend != 'stable':
                duration_trend = raw_trend
                break

    topic_map = {}
    for sd in snapshots_data:
        comp = sd['competitor']
        raw = sd['parsed']
        snap = sd['snapshot']
        bio = comp.get('bio', '')
        category_tags = comp.get('category_tags', [])
        if isinstance(category_tags, str):
            try:
                category_tags = json.loads(category_tags)
            except (json.JSONDecodeError, TypeError):
                category_tags = [t.strip() for t in category_tags.split(',') if t.strip()]
        engagement = snap.get('engagement_rate')
        engagement = float(engagement) if engagement is not None else 0.0

        topics = set()
        if bio:
            topics.add(bio.strip())
        for tag in (category_tags or []):
            if tag and isinstance(tag, str):
                topics.add(tag.strip())

        content_trends_raw = _parse_json_field(snap.get('content_trends'))
        if isinstance(content_trends_raw, list):
            for ct in content_trends_raw:
                kw = ct.get('keyword') or ct.get('topic')
                if kw and isinstance(kw, str):
                    topics.add(kw.strip())

        keywords_raw = raw.get('top_keywords', [])
        if isinstance(keywords_raw, list):
            for kw in keywords_raw:
                if kw and isinstance(kw, str):
                    topics.add(kw.strip())

        for topic in topics:
            if not topic:
                continue
            if topic not in topic_map:
                topic_map[topic] = {
                    'topic': topic,
                    'competitor_count': 0,
                    'total_engagement': 0.0,
                }
            topic_map[topic]['competitor_count'] += 1
            topic_map[topic]['total_engagement'] += engagement

    topic_heatmap = []
    for topic, data in sorted(topic_map.items(), key=lambda x: -x[1]['competitor_count']):
        avg_eng = data['total_engagement'] / max(data['competitor_count'], 1)
        n = data['competitor_count']
        total = max(len(snapshots_data), 1)
        ratio = n / total
        if ratio < 0.34:
            sat = 'low'
        elif ratio < 0.67:
            sat = 'medium'
        else:
            sat = 'high'
        topic_heatmap.append({
            'topic': topic,
            'competitor_count': n,
            'avg_engagement': round(avg_eng, 4),
            'saturation_level': sat,
            'trend_direction': 'stable',
        })

    angle_candidates = []
    for th in topic_heatmap:
        angle_candidates.append({
            'topic': th['topic'],
            'competitor_count': th['competitor_count'],
            'avg_engagement': th['avg_engagement'],
            'trend_direction': th.get('trend_direction', 'stable'),
        })
    blue_ocean_signals = _compute_blue_ocean_score(angle_candidates, len(snapshots_data))
    for th in topic_heatmap:
        th.pop('trend_direction', None)

    sorted_by_followers = sorted(
        snapshots_data,
        key=lambda sd: sd['snapshot'].get('follower_count') or 0,
        reverse=True,
    )
    leader = sorted_by_followers[0]['competitor'].get('account_name', '') if sorted_by_followers else ''

    innovators = []
    followers = []
    for sd in snapshots_data:
        name = sd['competitor'].get('account_name', '')
        raw = sd['parsed']
        hook = raw.get('hook_type', 'other')
        if hook not in ('other', 'empathy') and hook != min_hook_type:
            if name not in innovators:
                innovators.append(name)
        else:
            if name not in followers:
                followers.append(name)

    relationship_notes = (
        f"\u8d5b\u9053\u4e2d\u5171 {len(snapshots_data)} \u4e2a\u7ade\u54c1\uff0c"
        f"'{leader}' \u7c89\u4e1d\u91cf\u9886\u5148\u3002"
        f"\u84dd\u6d77\u94a9\u5b50\u7c7b\u578b\u4e3a {blue_ocean_hook}\u3002"
    )

    competitor_relationships = {
        'leader': leader,
        'innovators': innovators if innovators else ['(\u6682\u65e0\u660e\u786e\u521b\u65b0\u8005)'],
        'followers': followers if followers else ['(\u6682\u65e0\u660e\u786e\u8ffd\u968f\u8005)'],
        'relationship_notes': relationship_notes,
    }

    hook_counts_by_pattern = {}
    for sd in snapshots_data:
        name = sd['competitor'].get('account_name', '')
        raw = sd['parsed']
        hook = raw.get('hook_type', 'other')
        if hook not in hook_counts_by_pattern:
            hook_counts_by_pattern[hook] = {'adopted_by': [], 'hook': hook}
        hook_counts_by_pattern[hook]['adopted_by'].append(name)

    total_comps = max(len(snapshots_data), 1)
    cross_patterns = []
    for hook, data in hook_counts_by_pattern.items():
        if len(data['adopted_by']) >= 1:
            effectiveness = round(len(data['adopted_by']) / total_comps, 2)
            cross_patterns.append({
                'pattern_name': f"{HOOK_LABELS_CN.get(hook, hook)}\u94a9\u5b50\u6a21\u5f0f",
                'adopted_by': data['adopted_by'],
                'effectiveness': effectiveness,
            })
    cross_patterns.sort(key=lambda x: -x['effectiveness'])

    dates = [sd['snapshot'].get('snapshot_date', '') for sd in snapshots_data if sd['snapshot'].get('snapshot_date')]
    date_from = min(dates) if dates else now_iso
    date_to = max(dates) if dates else now_iso

    output_data = {
        'landscape_meta': {
            'keyword': keyword,
            'snapshot_date': now_iso,
            'competitors_analyzed': len(snapshots_data),
            'total_benchmarks': len(snapshots_data),
            'date_range': {'from': date_from, 'to': date_to},
        },
        'hook_type_landscape': {
            'suspense_pct': hook_pcts.get('suspense', 0.0),
            'conflict_pct': hook_pcts.get('conflict', 0.0),
            'empathy_pct': hook_pcts.get('empathy', 0.0),
            'benefit_pct': hook_pcts.get('benefit', 0.0),
            'anti_common_sense_pct': hook_pcts.get('anti_common_sense', 0.0),
            'other_pct': hook_pcts.get('other', 0.0),
            'blue_ocean_hook': blue_ocean_hook,
        },
        'duration_analysis': {
            'avg_duration_sec': avg_dur,
            'median_duration_sec': med_dur,
            'trend': duration_trend,
            'optimal_range': {'min_sec': optimal_min, 'max_sec': optimal_max},
        },
        'topic_heatmap': topic_heatmap,
        'blue_ocean_signals': blue_ocean_signals,
        'competitor_relationships': competitor_relationships,
        'cross_competitor_patterns': cross_patterns,
    }

    db_data = {
        'total_competitors': len(snapshots_data),
        'hook_type_distribution': output_data['hook_type_landscape'],
        'duration_distribution': output_data['duration_analysis'],
        'topic_heatmap': output_data['topic_heatmap'],
        'blue_ocean_signals': output_data['blue_ocean_signals'],
        'raw_json': output_data,
    }
    db.insert_landscape_snapshot(keyword, db_data, db_path=db_path)

    try:
        state = {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        state['last_landscape_snapshot'] = now_iso
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[analyze] \u66f4\u65b0 .yang-state.json \u5931\u8d25: {e}", file=sys.stderr)

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"\u8d5b\u9053\u683c\u5c40\u5206\u6790\u5b8c\u6210 [{keyword}]")
    print(f"  \u7ade\u54c1\u6570: {len(snapshots_data)}")
    print(f"  \u84dd\u6d77\u94a9\u5b50: {blue_ocean_hook} ({min(hook_pcts.values()):.1f}%)")
    print(f"  \u5e73\u5747\u65f6\u957f: {avg_dur}s")
    print(f"  \u84dd\u6d77\u4fe1\u53f7\u6570: {len(blue_ocean_signals)}")
    if output_path:
        print(f"  \u8f93\u51fa\u6587\u4ef6: {os.path.abspath(output_path)}")

    return output_data


def main():
    parser = argparse.ArgumentParser(description='\u8d5b\u9053\u683c\u5c40\u5206\u6790 - \u8de8\u7ade\u54c1\u6c47\u603b\u4e0e\u84dd\u6d77\u4fe1\u53f7\u68c0\u6d4b')
    parser.add_argument('--keyword', type=str, required=True, help='\u8d5b\u9053\u5173\u952e\u8bcd')
    parser.add_argument('--output', type=str, default=None, help='\u8f93\u51fa JSON \u6587\u4ef6\u8def\u5f84')
    parser.add_argument('--db-path', type=str, default='project_data.db', help='\u6570\u636e\u5e93\u8def\u5f84')
    args = parser.parse_args()

    result = run_landscape_analysis(args.keyword, args.output, args.db_path)
    if result is None:
        sys.exit(0)


if __name__ == '__main__':
    main()