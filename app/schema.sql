PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
 display_name TEXT NOT NULL, newspaper_name TEXT NOT NULL, timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
 city TEXT NOT NULL DEFAULT '서울', team TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL,
 topic TEXT NOT NULL, title TEXT NOT NULL, fields TEXT NOT NULL, photos TEXT NOT NULL DEFAULT '[]',
 version INTEGER NOT NULL DEFAULT 1, deleted INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS entries_day ON entries(user_id,date,deleted);
CREATE TABLE IF NOT EXISTS media (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), filename TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS day_settings (
 user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL,
 automatic TEXT NOT NULL DEFAULT '[]', PRIMARY KEY(user_id,date)
);
CREATE TABLE IF NOT EXISTS publications (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL,
 request_key TEXT NOT NULL, status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
 source TEXT NOT NULL, content TEXT, error TEXT, created_at TEXT NOT NULL,
 UNIQUE(user_id,request_key)
);
CREATE TABLE IF NOT EXISTS revisions (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL,
 revision INTEGER NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(user_id,date,revision)
);
CREATE INDEX IF NOT EXISTS revision_archive ON revisions(user_id,date);
CREATE TABLE IF NOT EXISTS shares (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), revision_id TEXT NOT NULL REFERENCES revisions(id),
 token_hash TEXT NOT NULL UNIQUE, revoked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
);
