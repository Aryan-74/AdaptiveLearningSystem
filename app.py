import json
import uuid
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db, init_db
from seed_data import seed_database
from profiling_engine import process_survey_responses, process_baseline_attempt
from services.knowledge_service import get_all_domains, get_domain_by_id
from services.recommendation_service import (
    generate_learning_recommendation,
    get_latest_recommendation,
    get_recommendation_history
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Ensure database exists and is seeded on startup
with app.app_context():
    init_db()
    # Check if database is seeded
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM survey_questions;")
    if cursor.fetchone()[0] == 0:
        seed_database()
    conn.close()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_step():
    return dict(current_step=session.get('current_step', 'intro'))

@app.route('/')
def index():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    step = session.get('current_step', 'intro')
    if step == 'survey':
        return redirect(url_for('survey'))
    elif step == 'knowledge_test':
        return redirect(url_for('test'))
    elif step == 'completed':
        return redirect(url_for('profile'))
    return redirect(url_for('intro'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT student_id FROM students WHERE email = ?;", (email,))
        if cursor.fetchone():
            conn.close()
            flash("An account with this email already exists.", "danger")
            return render_template('register.html')

        student_id = f"STU-{uuid.uuid4().hex[:8].upper()}"
        pwd_hash = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO students (student_id, name, email, password_hash, current_step) VALUES (?, ?, ?, ?, 'intro');",
            (student_id, name, email, pwd_hash)
        )
        conn.commit()
        conn.close()

        session['student_id'] = student_id
        session['student_name'] = name
        session['current_step'] = 'intro'

        flash("Registration successful! Welcome to the Adaptive Learning System.", "success")
        return redirect(url_for('intro'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, password_hash, current_step FROM students WHERE email = ?;", (email,))
        student = cursor.fetchone()
        conn.close()

        if student and check_password_hash(student['password_hash'], password):
            session['student_id'] = student['student_id']
            session['student_name'] = student['name']
            session['current_step'] = student['current_step']
            flash(f"Welcome back, {student['name']}!", "success")
            return redirect(url_for('index'))

        flash("Invalid email or password.", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/intro')
@login_required
def intro():
    return render_template('intro.html')

@app.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    student_id = session['student_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        raw_responses = {}
        for key, val in request.form.items():
            if key.startswith("VARK_") or key.startswith("MOT_") or key.startswith("SR_"):
                raw_responses[key] = int(val)

        process_survey_responses(student_id, raw_responses)
        session['current_step'] = 'knowledge_test'
        flash("Survey responses submitted and continuous parameters extracted!", "success")
        return redirect(url_for('survey_results'))

    cursor.execute("SELECT question_id, question_text, category, parameter FROM survey_questions;")
    questions = cursor.fetchall()
    conn.close()

    categorized = {}
    for q in questions:
        cat = q['category']
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(dict(q))

    return render_template('survey.html', categorized_questions=categorized)

@app.route('/survey/results')
@login_required
def survey_results():
    student_id = session['student_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_psychological_profile WHERE student_id = ?;", (student_id,))
    profile = cursor.fetchone()
    conn.close()

    if not profile:
        flash("Please complete the survey first.", "warning")
        return redirect(url_for('survey'))

    return render_template('survey_results.html', profile=dict(profile))

@app.route('/test', methods=['GET', 'POST'])
@login_required
def test():
    student_id = session['student_id']
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        attempt_id = session.get('current_attempt_id')
        if not attempt_id:
            flash("Invalid test session. Please try again.", "danger")
            return redirect(url_for('test'))

        responses_data = []
        for key, val in request.form.items():
            if key.startswith("Q_"):
                qid = key
                selected_ans = val
                time_spent = request.form.get(f"time_{qid}", 0.0)
                responses_data.append({
                    "question_id": qid,
                    "selected_answer": selected_ans,
                    "response_time_seconds": float(time_spent)
                })

        results = process_baseline_attempt(student_id, attempt_id, responses_data)
        session['current_step'] = 'completed'
        session['last_attempt_id'] = attempt_id
        session.pop('current_attempt_id', None)

        # Regenerate recommendation for the current test domain so recommendations reflect new scores immediately
        try:
            from services.recommendation_service import generate_learning_recommendation
            generate_learning_recommendation(student_id, "python")
        except Exception as e:
            app.logger.warning(f"Failed to auto-generate recommendation after test: {e}")

        flash("Baseline knowledge assessment completed!", "success")
        return redirect(url_for('test_results'))

    # GET: Start new test attempt
    attempt_id = f"ATT-{uuid.uuid4().hex[:8].upper()}"
    cursor.execute(
        "INSERT INTO baseline_attempts (attempt_id, student_id) VALUES (?, ?);",
        (attempt_id, student_id)
    )
    conn.commit()
    session['current_attempt_id'] = attempt_id

    # Load questions
    cursor.execute("""
        SELECT q.question_id, q.question_text, q.difficulty, q.options,
               t.topic_name, k.kc_name
        FROM knowledge_questions q
        JOIN knowledge_topics t ON q.topic_id = t.topic_id
        JOIN knowledge_components k ON q.kc_id = k.kc_id
        ORDER BY q.topic_id, q.difficulty;
    """)
    rows = cursor.fetchall()
    conn.close()

    questions = []
    for r in rows:
        qdict = dict(r)
        qdict['options_list'] = json.loads(qdict['options'])
        questions.append(qdict)

    return render_template('test.html', questions=questions)

@app.route('/test/results')
@login_required
def test_results():
    attempt_id = session.get('last_attempt_id')
    if not attempt_id:
        return redirect(url_for('profile'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM baseline_attempts WHERE attempt_id = ?;", (attempt_id,))
    attempt = cursor.fetchone()

    cursor.execute("SELECT * FROM student_knowledge_profile WHERE attempt_id = ?;", (attempt_id,))
    k_prof = cursor.fetchone()

    cursor.execute("SELECT topic_id, topic_name FROM knowledge_topics;")
    topic_names = {r['topic_id']: r['topic_name'] for r in cursor.fetchall()}
    conn.close()

    results = {
        "overall_performance": k_prof['overall_performance'],
        "correct_count": attempt['correct_count'],
        "total_questions": attempt['total_questions'],
        "topic_scores": json.loads(k_prof['topic_scores']),
        "kc_scores": json.loads(k_prof['kc_scores'])
    }

    return render_template('test_results.html', results=results, topic_names=topic_names)

@app.route('/profile')
@login_required
def profile():
    student_id = session['student_id']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE student_id = ?;", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM student_psychological_profile WHERE student_id = ?;", (student_id,))
    psycho = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM student_knowledge_profile 
        WHERE student_id = ? 
        ORDER BY calculated_at DESC LIMIT 1;
    """, (student_id,))
    knowledge = cursor.fetchone()

    attempt = None
    if knowledge:
        cursor.execute("SELECT * FROM baseline_attempts WHERE attempt_id = ?;", (knowledge['attempt_id'],))
        attempt = cursor.fetchone()

    cursor.execute("SELECT kc_id, kc_name FROM knowledge_components;")
    kc_names = {r['kc_id']: r['kc_name'] for r in cursor.fetchall()}
    conn.close()

    return render_template(
        'profile.html',
        student=dict(student),
        psycho=dict(psycho) if psycho else None,
        knowledge=dict(knowledge) if knowledge else None,
        attempt=dict(attempt) if attempt else None,
        kc_names=json.dumps(kc_names)
    )

@app.route('/test/retake', methods=['POST'])
@login_required
def retake_test():
    student_id = session['student_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET current_step = 'knowledge_test' WHERE student_id = ?;", (student_id,))
    conn.commit()
    conn.close()
    session['current_step'] = 'knowledge_test'
    flash("New baseline test attempt started.", "info")
    return redirect(url_for('test'))

@app.route('/recommendations')
@login_required
def recommendations_page():
    domains = [d.to_dict() for d in get_all_domains()]
    selected_domain = request.args.get('domain_id', 'python')
    return render_template('recommendations.html', domains=domains, selected_domain=selected_domain)

@app.route('/api/domains', methods=['GET'])
def api_domains():
    domains = [d.to_dict() for d in get_all_domains()]
    return jsonify({"domains": domains})

@app.route('/api/recommendations/generate', methods=['POST'])
@login_required
def api_generate_recommendation():
    try:
        student_id = session['student_id']
        data = request.get_json(silent=True) or {}
        domain_id = data.get('domain_id', 'python')
        learning_goal = data.get('learning_goal')

        rec = generate_learning_recommendation(student_id, domain_id, learning_goal)
        return jsonify({"success": True, "recommendation": rec})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/recommendations/latest', methods=['GET'])
@login_required
def api_latest_recommendation():
    try:
        student_id = session['student_id']
        domain_id = request.args.get('domain_id', 'python')
        rec = get_latest_recommendation(student_id, domain_id)
        return jsonify({"success": True, "recommendation": rec})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/recommendations/history', methods=['GET'])
@login_required
def api_recommendation_history():
    try:
        student_id = session['student_id']
        domain_id = request.args.get('domain_id')
        history = get_recommendation_history(student_id, domain_id)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
