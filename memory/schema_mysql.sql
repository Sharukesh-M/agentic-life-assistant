CREATE TABLE IF NOT EXISTS jarvis_users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    external_id VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jarvis_conversations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES jarvis_users(id)
);

CREATE TABLE IF NOT EXISTS jarvis_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_jarvis_conversation_time (conversation_id, created_at),
    FOREIGN KEY (conversation_id) REFERENCES jarvis_conversations(id)
);
CREATE TABLE IF NOT EXISTS user_memories (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    user_id VARCHAR(100) NOT NULL,

    category VARCHAR(50) NOT NULL,

    memory TEXT NOT NULL,

    importance FLOAT DEFAULT 0.5,

    status ENUM(
        'active',
        'superseded'
    ) DEFAULT 'active',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user_memory (user_id),

    INDEX idx_user_status (
        user_id,
        status
    )
);
CREATE TABLE IF NOT EXISTS user_state (

    user_id VARCHAR(100) PRIMARY KEY,

    current_goal TEXT,

    current_subject VARCHAR(255),

    current_topic VARCHAR(255),

    learning_style VARCHAR(255),

    updated_at TIMESTAMP
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);