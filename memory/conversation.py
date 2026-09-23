from database import get_connection


def save_message(user_id, role, message):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO conversations
        (user_id, role, message)
        VALUES (%s, %s, %s)
    """

    cursor.execute(
        query,
        (user_id, role, message)
    )

    conn.commit()

    cursor.close()
    conn.close()


def get_recent_messages(user_id, limit=15):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT role, message
        FROM conversations
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """

    cursor.execute(query, (user_id, limit))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # Database gives newest first
    rows.reverse()

    return rows