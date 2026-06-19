-- 作者: 阿洋
-- Yang.skills v4 本地数据湖 DDL
-- 由 yang-init 自动执行

CREATE TABLE IF NOT EXISTS videos (
    id              TEXT PRIMARY KEY,
    url             TEXT NOT NULL,
    platform        TEXT NOT NULL,
    title           TEXT,
    author          TEXT,
    duration_sec    INTEGER,
    publish_date    TEXT,
    local_path      TEXT,
    downloaded_at   TEXT DEFAULT (datetime('now')),
    status          TEXT DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_videos_platform ON videos(platform);
CREATE INDEX IF NOT EXISTS idx_videos_author ON videos(author);

CREATE TABLE IF NOT EXISTS frames (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES videos(id),
    frame_index     INTEGER NOT NULL,
    timestamp_sec   REAL NOT NULL,
    file_path       TEXT NOT NULL,
    visual_desc     TEXT,
    on_screen_text  TEXT,
    scene_change    INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_frames_video ON frames(video_id);

CREATE TABLE IF NOT EXISTS comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES videos(id),
    content         TEXT NOT NULL,
    likes           INTEGER DEFAULT 0,
    reply_count     INTEGER DEFAULT 0,
    sentiment       TEXT,
    scraped_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_comments_video ON comments(video_id);

CREATE TABLE IF NOT EXISTS emotions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES videos(id),
    timestamp_sec   REAL NOT NULL,
    emotion_type    TEXT NOT NULL,
    intensity       REAL NOT NULL,
    source          TEXT DEFAULT 'llm'
);
CREATE INDEX IF NOT EXISTS idx_emotions_video ON emotions(video_id);

CREATE TABLE IF NOT EXISTS predictions (
    id              TEXT PRIMARY KEY,
    score_file      TEXT,
    predicted_bucket_A  REAL DEFAULT 0,
    predicted_bucket_B  REAL DEFAULT 0,
    predicted_bucket_C  REAL DEFAULT 0,
    predicted_bucket_D  REAL DEFAULT 0,
    actual_bucket   TEXT,
    actual_plays    INTEGER,
    prediction_date TEXT DEFAULT (datetime('now')),
    retro_date      TEXT
);

CREATE TABLE IF NOT EXISTS trends (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL,
    platform        TEXT NOT NULL,
    rank            INTEGER,
    heat_value      REAL,
    url             TEXT,
    fetched_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_trends_platform ON trends(platform, fetched_at);

-- 竞品账号主表
CREATE TABLE IF NOT EXISTS competitors (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    platform TEXT NOT NULL CHECK(platform IN ('douyin','bilibili','xiaohongshu','kuaishou','weibo','zhihu','other')),
    account_id TEXT NOT NULL,
    account_url TEXT NOT NULL,
    avatar_url TEXT,
    bio TEXT,
    verified INTEGER DEFAULT 0,
    category_tags TEXT,
    discovery_source TEXT,
    discovery_keyword TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1,
    UNIQUE(platform, account_id)
);

-- 竞品数据快照
CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id TEXT NOT NULL REFERENCES competitors(id),
    snapshot_date TEXT NOT NULL DEFAULT (datetime('now')),
    follower_count INTEGER,
    total_likes INTEGER,
    total_videos INTEGER,
    avg_views_30d INTEGER,
    avg_likes_30d INTEGER,
    avg_comments_30d INTEGER,
    engagement_rate REAL,
    audience_insight TEXT,
    content_trends TEXT,
    raw_json TEXT,
    UNIQUE(competitor_id, snapshot_date)
);

-- 竞品策略变化日志
CREATE TABLE IF NOT EXISTS competitor_strategy_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id TEXT NOT NULL REFERENCES competitors(id),
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    change_type TEXT NOT NULL CHECK(change_type IN (
        'hook_type_shift',
        'duration_trend',
        'topic_shift',
        'style_change',
        'frequency_change',
        'persona_drift',
        'engagement_drop',
        'engagement_spike'
    )),
    before_state TEXT,
    after_state TEXT,
    significance REAL DEFAULT 0.5,
    summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_cs_competitor_date ON competitor_strategy_changes(competitor_id, detected_at);

-- 赛道格局快照
CREATE TABLE IF NOT EXISTS landscape_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL DEFAULT (datetime('now')),
    keyword TEXT NOT NULL,
    total_competitors INTEGER,
    hook_type_distribution TEXT,
    duration_distribution TEXT,
    topic_heatmap TEXT,
    blue_ocean_signals TEXT,
    raw_json TEXT
);

-- 竞品监控订阅
CREATE TABLE IF NOT EXISTS competitor_monitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id TEXT NOT NULL REFERENCES competitors(id),
    rss_url TEXT,
    platform_monitor_type TEXT CHECK(platform_monitor_type IN ('rsshub','playwright_poll','manual')),
    last_checked_at TEXT,
    last_video_found_at TEXT,
    check_interval_hours INTEGER DEFAULT 24,
    is_enabled INTEGER DEFAULT 1
);