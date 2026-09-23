"""Optional durable conversation storage for Jarvis-X.

MySQL is deliberately best-effort: when MYSQL_ENABLED is not true, or the
connector/server is unavailable, Jarvis continues using its existing local
memory and session-summary behavior.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:  # optional dependency
    mysql = None
    mysql_connector = None
    Error = Exception


class MySQLConversationStore:
    def __init__(self) -> None:
        self.enabled = os.getenv("MYSQL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self._connection = None
        self.conversation_id: int | None = None
        self.user_id = os.getenv("JARVIS_USER_ID", "local-user").strip() or "local-user"
        self._warned = False

    def _connect(self):
        if not self.enabled or self._connection is not None:
            return self._connection
        if "mysql.connector" not in globals() or globals().get("mysql_connector") is None:
            # The import alias is unavailable on older connector versions; use
            # the module-level mysql object when it exists.
            if "mysql" not in globals() or globals().get("mysql") is None:
                self._warn("mysql-connector-python is not installed")
                return None
        try:
            import mysql.connector as connector
            self._connection = connector.connect(
                host=os.getenv("MYSQL_HOST", "127.0.0.1"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                database=os.getenv("MYSQL_DATABASE", "JARVIS"),
                user=os.getenv("MYSQL_USER", "jarvis_user"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                connection_timeout=int(os.getenv("MYSQL_CONNECT_TIMEOUT", "3")),
            )
            self._ensure_schema()
            return self._connection
        except Exception as exc:
            self._warn(f"MySQL unavailable: {exc}")
            self._connection = None
            return None

    def _warn(self, message: str) -> None:
        if not self._warned:
            print(f"[MySQL] {message}. Continuing with local memory.")
            self._warned = True

    def _ensure_schema(self) -> None:
        conn = self._connection
        if conn is None:
            return
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_users (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    external_id VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_conversations (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES jarvis_users(id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_messages (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id BIGINT NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content LONGTEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_jarvis_conversation_time (conversation_id, created_at),
                    FOREIGN KEY (conversation_id) REFERENCES jarvis_conversations(id)
                )
            """)
            conn.commit()
        finally:
            cur.close()

    def start_conversation(self) -> int | None:
        conn = self._connect()
        if conn is None:
            return None
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO jarvis_users (external_id) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)",
                (self.user_id,),
            )
            user_pk = cur.lastrowid
            cur.execute("INSERT INTO jarvis_conversations (user_id) VALUES (%s)", (user_pk,))
            self.conversation_id = cur.lastrowid
            conn.commit()
            return self.conversation_id
        except Exception as exc:
            conn.rollback()
            self._warn(f"Could not start conversation: {exc}")
            return None
        finally:
            cur.close()

    def save_message(self, role: str, content: str) -> bool:
        content = (content or "").strip()
        if not content:
            return False
        if self.conversation_id is None and self.start_conversation() is None:
            return False
        conn = self._connection
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO jarvis_messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                (self.conversation_id, role[:20], content),
            )
            conn.commit()
            cur.close()
            return True
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            self._warn(f"Could not save message: {exc}")
            return False

    def recent_messages(self, limit: int = 12) -> list[dict]:
        conn = self._connect()
        if conn is None:
            return []
        if self.conversation_id is None:
            return []
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT role, content, created_at FROM jarvis_messages "
                "WHERE conversation_id=%s ORDER BY created_at DESC LIMIT %s",
                (self.conversation_id, max(1, min(int(limit), 50))),
            )
            rows = list(reversed(cur.fetchall()))
            return rows
        except Exception as exc:
            self._warn(f"Could not read messages: {exc}")
            return []
        finally:
            cur.close()

    def recent_user_messages(self, limit: int = 8) -> list[dict]:
        """Return a small cross-session window for prompt context."""
        conn = self._connect()
        if conn is None:
            return []
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT m.role, m.content, m.created_at "
                "FROM jarvis_messages m "
                "JOIN jarvis_conversations c ON c.id=m.conversation_id "
                "JOIN jarvis_users u ON u.id=c.user_id "
                "WHERE u.external_id=%s ORDER BY m.created_at DESC LIMIT %s",
                (self.user_id, max(1, min(int(limit), 20))),
            )
            return list(reversed(cur.fetchall()))
        except Exception as exc:
            self._warn(f"Could not read conversation context: {exc}")
            return []
        finally:
            cur.close()

    def prompt_context(self, limit: int = 8) -> str:
        rows = self.recent_user_messages(limit)
        if not rows:
            return ""
        lines = ["[RECENT CONVERSATION MEMORY FROM MYSQL]"]
        for row in rows:
            role = "User" if row.get("role") == "user" else "Jarvis"
            lines.append(f"{role}: {str(row.get('content', '')).strip()[:600]}")
        lines.append("Use this context when relevant; do not recite it unless asked.")
        return "\n".join(lines)

    def close(self) -> None:
        if self._connection is None:
            return
        try:
            if self.conversation_id:
                cur = self._connection.cursor()
                cur.execute(
                    "UPDATE jarvis_conversations SET ended_at=%s WHERE id=%s",
                    (datetime.now(timezone.utc).replace(tzinfo=None), self.conversation_id),
                )
                self._connection.commit()
                cur.close()
            self._connection.close()
        except Exception:
            pass
        finally:
            self._connection = None
