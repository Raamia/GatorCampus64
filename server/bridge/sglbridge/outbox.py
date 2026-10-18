"""Crash-safe event delivery. Only acknowledged rows are removed from the outbox.

SQLite lives in the bridge's persistent state directory, outside deployed source.
The process lock prevents two bridge instances from delivering the same database.
Permanent API rejections are retained for inspection. At capacity/disk failure,
stop the game instead of evicting accepted events or silently losing identities.
"""
import fcntl
import json
import os
from pathlib import Path
import sqlite3

from .api import RetryQueue


class OutboxFull(RuntimeError):
    pass


class DurableRetryQueue(RetryQueue):
    def __init__(self, send, path, *, maxlen=20_000, fatal=None, **kwargs):
        super().__init__(send, maxlen=maxlen, **kwargs)
        self.fatal = fatal or (lambda: None)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file_lock = open(str(path) + '.lock', 'a')
        try:
            fcntl.flock(self._file_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.db = sqlite3.connect(path, check_same_thread=False)
            os.chmod(path, 0o600)
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('''CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT, envelope TEXT NOT NULL,
                error TEXT, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            self.db.commit()
        except BaseException:
            if hasattr(self, 'db'):
                self.db.close()
            self._file_lock.close()
            raise

    def __len__(self):
        with self._cv:
            return self.db.execute('SELECT count(*) FROM outbox WHERE error IS NULL').fetchone()[0]

    def put(self, item):
        # No HTTP under this lock. A returned put guarantees a durable commit.
        try:
            encoded = json.dumps(item, separators=(',', ':'), allow_nan=False)
            if len(encoded.encode()) > 128 * 1024:
                raise ValueError('event exceeds 128 KiB outbox limit')
            with self._cv, self.db:
                if self.db.execute('SELECT count(*) FROM outbox').fetchone()[0] >= self.maxlen:
                    raise OutboxFull('event outbox full (including rejected rows); game stopped, inspect outbox')
                self.db.execute('INSERT INTO outbox (envelope) VALUES (?)', (encoded,))
            with self._cv:
                self._cv.notify()
        except Exception:
            self.fatal()
            raise

    def _head(self):
        row = self.db.execute('SELECT id, envelope FROM outbox WHERE error IS NULL ORDER BY id LIMIT 1').fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def _pop(self, token):
        with self._cv, self.db:
            self.db.execute('DELETE FROM outbox WHERE id = ?', (token,))

    def _reject(self, token, item, error):
        with self._cv, self.db:
            self.db.execute('UPDATE outbox SET error = ? WHERE id = ?', (str(error)[:2000], token))

    def close(self):
        with self._drain_lock, self._cv:
            self.db.close()
            self._file_lock.close()

    def run(self, stop):
        try:
            super().run(stop)
        except Exception:
            self.fatal()
            raise
