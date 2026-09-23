import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


class JarvisMemoryStore:
    def __init__(self):
        self.initialize_tables()

    def initialize_tables(self):
        """Creates the user_memories and user_state tables if they don't exist."""
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Create user_memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                memory TEXT NOT NULL,
                importance FLOAT DEFAULT 0.5,
                status ENUM('active', 'superseded') DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_memory (user_id),
                INDEX idx_user_status (user_id, status)
            );
        """)

        # 2. Create user_state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                user_id VARCHAR(100) PRIMARY KEY,
                current_goal TEXT,
                current_subject VARCHAR(255),
                current_topic VARCHAR(255),
                learning_style VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cursor.close()
        conn.close()

    def update_user_state(self, user_id: str, goal: str, subject: str, topic: str, learning_style: str = "structured"):
        """Upsert (insert or update) the user's current agentic state (e.g., GATE prep tracking)."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO user_state (user_id, current_goal, current_subject, current_topic, learning_style)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                current_goal = VALUES(current_goal),
                current_subject = VALUES(current_subject),
                current_topic = VALUES(current_topic),
                learning_style = VALUES(learning_style);
        """
        cursor.execute(query, (user_id, goal, subject, topic, learning_style))
        conn.commit()
        cursor.close()
        conn.close()

    def add_memory(self, user_id: str, category: str, memory_text: str, importance: float = 0.5):
        """Logs a long-term memory for the user."""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO user_memories (user_id, category, memory, importance, status)
            VALUES (%s, %s, %s, %s, 'active');
        """
        cursor.execute(query, (user_id, category, memory_text, importance))
        conn.commit()
        cursor.close()
        conn.close()

    def get_user_state(self, user_id: str):
        """Retrieves the current state of the user (e.g., what they are studying)."""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM user_state WHERE user_id = %s;", (user_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return result