import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_step TEXT NOT NULL DEFAULT 'survey',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Survey Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey_questions (
        question_id TEXT PRIMARY KEY,
        question_text TEXT NOT NULL,
        category TEXT NOT NULL, -- VARK, Motivation, Self-Regulation
        parameter TEXT NOT NULL, -- e.g., VARK_visual, intrinsic_motivation, goal_setting
        reverse_scored INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 3. Survey Responses Table (Raw Data)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey_responses (
        response_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        raw_score INTEGER NOT NULL, -- 1 to 5
        normalized_score REAL NOT NULL, -- 0.0 to 1.0
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES survey_questions(question_id)
    );
    """)

    # 4. Student Psychological Profile Table (Derived Parameters)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_psychological_profile (
        student_id TEXT PRIMARY KEY,
        vark_visual REAL NOT NULL DEFAULT 0.0,
        vark_aural REAL NOT NULL DEFAULT 0.0,
        vark_read_write REAL NOT NULL DEFAULT 0.0,
        vark_kinesthetic REAL NOT NULL DEFAULT 0.0,
        intrinsic_motivation REAL NOT NULL DEFAULT 0.0,
        extrinsic_motivation REAL NOT NULL DEFAULT 0.0,
        learning_goal_orientation REAL NOT NULL DEFAULT 0.0,
        task_value REAL NOT NULL DEFAULT 0.0,
        goal_setting REAL NOT NULL DEFAULT 0.0,
        planning REAL NOT NULL DEFAULT 0.0,
        self_monitoring REAL NOT NULL DEFAULT 0.0,
        revision_behavior REAL NOT NULL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
    );
    """)

    # 0. Domains Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS domains (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL
    );
    """)

    # 5. Knowledge Topics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_topics (
        topic_id TEXT PRIMARY KEY,
        domain_id TEXT NOT NULL DEFAULT 'python',
        topic_name TEXT NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (domain_id) REFERENCES domains(id)
    );
    """)

    # 6. Knowledge Components (KCs) Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_components (
        kc_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL,
        kc_name TEXT NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES knowledge_topics(topic_id)
    );
    """)

    # 7. Knowledge Questions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_questions (
        question_id TEXT PRIMARY KEY,
        topic_id TEXT NOT NULL,
        kc_id TEXT NOT NULL,
        question_text TEXT NOT NULL,
        question_type TEXT NOT NULL DEFAULT 'mcq',
        difficulty TEXT NOT NULL, -- Easy, Medium, Hard
        options TEXT NOT NULL, -- JSON array of string options
        correct_answer TEXT NOT NULL,
        explanation TEXT NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES knowledge_topics(topic_id),
        FOREIGN KEY (kc_id) REFERENCES knowledge_components(kc_id)
    );
    """)

    # 8. Baseline Test Attempts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS baseline_attempts (
        attempt_id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        total_questions INTEGER NOT NULL DEFAULT 0,
        correct_count INTEGER NOT NULL DEFAULT 0,
        overall_score REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
    );
    """)

    # 9. Baseline Test Responses Table (Raw interaction log)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS baseline_responses (
        response_id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id TEXT NOT NULL,
        student_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        kc_id TEXT NOT NULL,
        selected_answer TEXT NOT NULL,
        correct INTEGER NOT NULL, -- 0 or 1
        difficulty TEXT NOT NULL,
        response_time_seconds REAL NOT NULL DEFAULT 0.0,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (attempt_id) REFERENCES baseline_attempts(attempt_id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES knowledge_questions(question_id)
    );
    """)

    # 10. Student Knowledge Profile Table (Derived Snapshot)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_knowledge_profile (
        profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        attempt_id TEXT NOT NULL,
        overall_performance REAL NOT NULL,
        topic_scores TEXT NOT NULL, -- JSON object {topic_id: score}
        kc_scores TEXT NOT NULL, -- JSON object {kc_id: score}
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (attempt_id) REFERENCES baseline_attempts(attempt_id) ON DELETE CASCADE
    );
    """)

    # 11. Recommendations Table (Stored AI Recommendation Snapshots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id TEXT PRIMARY KEY,
        student_id TEXT NOT NULL,
        domain_id TEXT NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        model_name TEXT NOT NULL,
        learning_goal TEXT,
        profile_snapshot TEXT NOT NULL,
        recommendation_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'completed',
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY (domain_id) REFERENCES domains(id)
    );
    """)

    # Migration check for existing databases
    cursor.execute("PRAGMA table_info(knowledge_topics);")
    cols = [row[1] for row in cursor.fetchall()]
    if "domain_id" not in cols:
        cursor.execute("ALTER TABLE knowledge_topics ADD COLUMN domain_id TEXT NOT NULL DEFAULT 'python';")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
