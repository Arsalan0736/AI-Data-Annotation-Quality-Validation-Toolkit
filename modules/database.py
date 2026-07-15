import sqlite3
import os
import json
from config import DB_PATH

def get_connection():
    """Establish connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Create all required tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Projects
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL, -- 'Image' or 'Text'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Images (Represents Dataset Items - images or text texts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        content TEXT, -- Text content for text classification tasks
        blur_score REAL,
        is_corrupted INTEGER DEFAULT 0,
        is_duplicate INTEGER DEFAULT 0,
        duplicate_of TEXT,
        similarity_score REAL,
        FOREIGN KEY (project_id) REFERENCES Projects(id) ON DELETE CASCADE
    );
    """)

    # 3. Annotations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Annotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER NOT NULL,
        annotator_name TEXT NOT NULL,
        label TEXT NOT NULL,
        duration_seconds REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (image_id) REFERENCES Images(id) ON DELETE CASCADE,
        UNIQUE(image_id, annotator_name)
    );
    """)

    # 4. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL
    );
    """)

    # Default users
    cursor.execute("INSERT OR IGNORE INTO Users (username, role) VALUES ('Annotator A', 'annotator')")
    cursor.execute("INSERT OR IGNORE INTO Users (username, role) VALUES ('Annotator B', 'annotator')")
    cursor.execute("INSERT OR IGNORE INTO Users (username, role) VALUES ('Annotator C', 'annotator')")
    cursor.execute("INSERT OR IGNORE INTO Users (username, role) VALUES ('Admin', 'admin')")

    # 5. Reviews
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER NOT NULL,
        reviewer_name TEXT NOT NULL,
        status TEXT NOT NULL, -- 'Approved' or 'Corrected'
        corrected_label TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (image_id) REFERENCES Images(id) ON DELETE CASCADE
    );
    """)

    # 6. Statistics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER UNIQUE NOT NULL,
        total_items INTEGER DEFAULT 0,
        annotated_count INTEGER DEFAULT 0,
        pending_count INTEGER DEFAULT 0,
        wrong_labels_count INTEGER DEFAULT 0,
        duplicate_count INTEGER DEFAULT 0,
        missing_labels_count INTEGER DEFAULT 0,
        corrupted_count INTEGER DEFAULT 0,
        avg_annotation_time REAL DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects(id) ON DELETE CASCADE
    );
    """)
    
    conn.commit()
    conn.close()

# ----------------- PROJECTS -----------------

def create_project(name, project_type):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Projects (name, type) VALUES (?, ?)", (name, project_type))
        project_id = cursor.lastrowid
        # Initialize stats row for this project
        cursor.execute("INSERT OR IGNORE INTO Statistics (project_id) VALUES (?)", (project_id,))
        conn.commit()
        return project_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_projects():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Projects ORDER BY created_at DESC")
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return projects

def get_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

# ----------------- DATA ITEMS (IMAGES / TEXTS) -----------------

def add_data_item(project_id, filename, content=None, blur_score=None, is_corrupted=0, is_duplicate=0, duplicate_of=None, similarity_score=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Images (project_id, filename, content, blur_score, is_corrupted, is_duplicate, duplicate_of, similarity_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, filename, content, blur_score, is_corrupted, is_duplicate, duplicate_of, similarity_score))
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id

def get_data_items(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Images WHERE project_id = ?", (project_id,))
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def get_data_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Images WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_item_validation(item_id, is_corrupted=None, blur_score=None, is_duplicate=None, duplicate_of=None, similarity_score=None):
    conn = get_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    if is_corrupted is not None:
        fields.append("is_corrupted = ?")
        values.append(is_corrupted)
    if blur_score is not None:
        fields.append("blur_score = ?")
        values.append(blur_score)
    if is_duplicate is not None:
        fields.append("is_duplicate = ?")
        values.append(is_duplicate)
    if duplicate_of is not None:
        fields.append("duplicate_of = ?")
        values.append(duplicate_of)
    if similarity_score is not None:
        fields.append("similarity_score = ?")
        values.append(similarity_score)
    
    if fields:
        values.append(item_id)
        cursor.execute(f"UPDATE Images SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    conn.close()

# ----------------- ANNOTATIONS -----------------

def add_annotation(image_id, annotator_name, label, duration_seconds):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Annotations (image_id, annotator_name, label, duration_seconds)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(image_id, annotator_name) DO UPDATE SET
            label = excluded.label,
            duration_seconds = duration_seconds + excluded.duration_seconds,
            created_at = CURRENT_TIMESTAMP
    """, (image_id, annotator_name, label, duration_seconds))
    conn.commit()
    conn.close()

def get_annotations_for_item(image_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Annotations WHERE image_id = ?", (image_id,))
    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

def get_all_annotations_for_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, i.filename, i.content 
        FROM Annotations a 
        JOIN Images i ON a.image_id = i.id 
        WHERE i.project_id = ?
    """, (project_id,))
    annotations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

# ----------------- REVIEWS -----------------

def add_review(image_id, reviewer_name, status, corrected_label=None):
    conn = get_connection()
    cursor = conn.cursor()
    # Check if a review already exists for this image
    cursor.execute("SELECT id FROM Reviews WHERE image_id = ?", (image_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE Reviews 
            SET reviewer_name = ?, status = ?, corrected_label = ?, created_at = CURRENT_TIMESTAMP
            WHERE image_id = ?
        """, (reviewer_name, status, corrected_label, image_id))
    else:
        cursor.execute("""
            INSERT INTO Reviews (image_id, reviewer_name, status, corrected_label)
            VALUES (?, ?, ?, ?)
        """, (image_id, reviewer_name, status, corrected_label))
    conn.commit()
    conn.close()

def get_reviews_for_project(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, i.filename, i.content
        FROM Reviews r
        JOIN Images i ON r.image_id = i.id
        WHERE i.project_id = ?
    """, (project_id,))
    reviews = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reviews

# ----------------- STATISTICS -----------------

def update_statistics(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total items
    cursor.execute("SELECT COUNT(*) FROM Images WHERE project_id = ?", (project_id,))
    total_items = cursor.fetchone()[0]
    
    # 2. Duplicate count
    cursor.execute("SELECT COUNT(*) FROM Images WHERE project_id = ? AND is_duplicate = 1", (project_id,))
    duplicate_count = cursor.fetchone()[0]
    
    # 3. Corrupted count
    cursor.execute("SELECT COUNT(*) FROM Images WHERE project_id = ? AND is_corrupted = 1", (project_id,))
    corrupted_count = cursor.fetchone()[0]

    # For annotations, we aggregate majority-vote decisions per image or check if there's any annotation.
    # Total distinct items with at least one annotation
    cursor.execute("""
        SELECT COUNT(DISTINCT image_id) 
        FROM Annotations a 
        JOIN Images i ON a.image_id = i.id 
        WHERE i.project_id = ?
    """, (project_id,))
    annotated_count = cursor.fetchone()[0]
    
    # Pending count
    pending_count = total_items - annotated_count

    # Missing labels count: total items that have no annotations
    cursor.execute("""
        SELECT COUNT(*) FROM Images i 
        WHERE i.project_id = ? 
          AND i.id NOT IN (SELECT DISTINCT image_id FROM Annotations)
    """, (project_id,))
    missing_labels_count = cursor.fetchone()[0]

    # Avg annotation time
    cursor.execute("""
        SELECT AVG(duration_seconds) 
        FROM Annotations a 
        JOIN Images i ON a.image_id = i.id 
        WHERE i.project_id = ?
    """, (project_id,))
    row = cursor.fetchone()
    avg_annotation_time = row[0] if row and row[0] is not None else 0.0

    # Wrong labels count: We can estimate this dynamically using the validation similarity score.
    # An item is flagged as "wrong label" if it has an annotation and the model's similarity score is below the threshold
    # Let's count items where the validation similarity score (pre-calculated via MobileNet) is less than WRONG_LABEL_THRESHOLD.
    # Wait, we will compute this in validation.py and mark similarity_score.
    # Let's get the similarity score and see how many are below WRONG_LABEL_THRESHOLD (e.g., 0.20)
    # Let's count how many images have a low similarity score AND have at least one annotation
    cursor.execute("""
        SELECT COUNT(DISTINCT i.id) 
        FROM Images i
        JOIN Annotations a ON i.id = a.image_id
        WHERE i.project_id = ? 
          AND i.similarity_score IS NOT NULL 
          AND i.similarity_score < 0.20
    """, (project_id,))
    wrong_labels_count = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO Statistics (
            project_id, total_items, annotated_count, pending_count, 
            wrong_labels_count, duplicate_count, missing_labels_count, 
            corrupted_count, avg_annotation_time, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(project_id) DO UPDATE SET
            total_items = excluded.total_items,
            annotated_count = excluded.annotated_count,
            pending_count = excluded.pending_count,
            wrong_labels_count = excluded.wrong_labels_count,
            duplicate_count = excluded.duplicate_count,
            missing_labels_count = excluded.missing_labels_count,
            corrupted_count = excluded.corrupted_count,
            avg_annotation_time = excluded.avg_annotation_time,
            updated_at = CURRENT_TIMESTAMP
    """, (project_id, total_items, annotated_count, pending_count,
          wrong_labels_count, duplicate_count, missing_labels_count,
          corrupted_count, avg_annotation_time))
    
    conn.commit()
    conn.close()

def get_statistics(project_id):
    # First update stats so they are fresh
    update_statistics(project_id)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Statistics WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
