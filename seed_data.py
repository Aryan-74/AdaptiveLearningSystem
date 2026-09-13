import json
from db import get_db, init_db

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing seed metadata (not student responses)
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DELETE FROM survey_questions;")
    cursor.execute("DELETE FROM knowledge_questions;")
    cursor.execute("DELETE FROM knowledge_components;")
    cursor.execute("DELETE FROM knowledge_topics;")
    cursor.execute("DELETE FROM domains;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 0. SEED DOMAINS
    domains = [
        ("python", "Python Programming", "Programming using the Python language"),
        ("mathematics", "Mathematics", "Fundamental and advanced mathematical concepts"),
        ("physics", "Physics", "Fundamental physics principles, mechanics, and thermodynamics")
    ]
    for did, dname, ddesc in domains:
        cursor.execute(
            "INSERT INTO domains (id, name, description) VALUES (?, ?, ?);",
            (did, dname, ddesc)
        )

    # 1. SEED SURVEY QUESTIONS (24 domain-agnostic questions total)
    survey_questions = [
        # VARK Visual
        ("VARK_V1", "I remember concepts best when presented in visual diagrams, flowcharts, or graphics.", "VARK", "VARK_visual", 0),
        ("VARK_V2", "I prefer video demonstrations and visual slide presentations over plain spoken explanations.", "VARK", "VARK_visual", 0),

        # VARK Aural
        ("VARK_A1", "I learn efficiently through audio lectures, podcasts, and verbal discussions with others.", "VARK", "VARK_aural", 0),
        ("VARK_A2", "Explaining concepts aloud to someone else helps solidify my understanding.", "VARK", "VARK_aural", 0),

        # VARK Read/Write
        ("VARK_R1", "I prefer reading detailed documentation, textbooks, and writing comprehensive text notes.", "VARK", "VARK_read_write", 0),
        ("VARK_R2", "Writing summaries and organizing information into written bullet points is key to my learning process.", "VARK", "VARK_read_write", 0),

        # VARK Kinesthetic
        ("VARK_K1", "I learn best by hands-on practice, physical application, and experimenting directly.", "VARK", "VARK_kinesthetic", 0),
        ("VARK_K2", "Interactive practice exercises and real-world application scenarios keep me engaged.", "VARK", "VARK_kinesthetic", 0),

        # Motivation - Intrinsic
        ("MOT_INT1", "I study new topics primarily because I enjoy curiosity, problem-solving, and acquiring knowledge.", "Motivation", "intrinsic_motivation", 0),
        ("MOT_INT2", "I feel a deep sense of personal satisfaction when I master a complex concept.", "Motivation", "intrinsic_motivation", 0),

        # Motivation - Extrinsic
        ("MOT_EXT1", "Getting high grades, formal qualifications, or external recognition drives my learning effort.", "Motivation", "extrinsic_motivation", 0),
        ("MOT_EXT2", "Career advancement and credential requirements are my main reasons for pursuing learning.", "Motivation", "extrinsic_motivation", 0),

        # Motivation - Learning Goal Orientation
        ("MOT_LGO1", "I view mistakes and incorrect answers as valuable opportunities to improve my mastery.", "Motivation", "learning_goal_orientation", 0),
        ("MOT_LGO2", "I prefer challenging learning tasks that stretch my skills over easy, familiar tasks.", "Motivation", "learning_goal_orientation", 0),

        # Motivation - Task Value
        ("MOT_TV1", "Acquiring new knowledge in my study areas is highly relevant and valuable for my future goals.", "Motivation", "task_value", 0),
        ("MOT_TV2", "The concepts covered in my learning tasks are important and useful to me.", "Motivation", "task_value", 0),

        # Self-Regulation - Goal Setting
        ("SR_GS1", "Before beginning a study session, I set specific, realistic learning goals.", "Self-Regulation", "goal_setting", 0),
        ("SR_GS2", "I define clear milestones for completing my learning tasks on schedule.", "Self-Regulation", "goal_setting", 0),

        # Self-Regulation - Planning
        ("SR_PL1", "I break down complex learning tasks into smaller, manageable steps before starting.", "Self-Regulation", "planning", 0),
        ("SR_PL2", "I allocate dedicated time blocks for studying and practice each week.", "Self-Regulation", "planning", 0),

        # Self-Regulation - Self-Monitoring
        ("SR_SM1", "I regularly evaluate whether I truly understand a concept while working through material.", "Self-Regulation", "self_monitoring", 0),
        ("SR_SM2", "When I encounter a difficult problem, I pause to reflect on my problem-solving strategy.", "Self-Regulation", "self_monitoring", 0),

        # Self-Regulation - Revision Behavior
        ("SR_RB1", "I review previous notes and study materials to reinforce my retention over time.", "Self-Regulation", "revision_behavior", 0),
        ("SR_RB2", "When I receive feedback or encounter errors, I revise my approach immediately.", "Self-Regulation", "revision_behavior", 0)
    ]

    for qid, text, cat, param, rev in survey_questions:
        cursor.execute(
            "INSERT INTO survey_questions (question_id, question_text, category, parameter, reverse_scored) VALUES (?, ?, ?, ?, ?)",
            (qid, text, cat, param, rev)
        )

    # 2. SEED KNOWLEDGE TOPICS
    topics = [
        # Python Programming
        ("variables", "python", "Variables", "Storing, naming, and reassigning data values in memory"),
        ("data_types", "python", "Data Types", "Primitive and dynamic type system (int, float, str, bool)"),
        ("operators", "python", "Operators", "Arithmetic, comparison, logical, and assignment operators"),
        ("conditions", "python", "Conditions", "Conditional branching using if, elif, and else statements"),
        ("loops", "python", "Loops", "Iterative execution using for loops and while loops"),
        ("functions", "python", "Functions", "Defining reusable logic, parameters, arguments, and return values"),
        ("lists", "python", "Lists", "Ordered, mutable sequential data structures"),
        ("dictionaries", "python", "Dictionaries", "Key-value pair associative mappings"),

        # Mathematics
        ("linear_algebra", "mathematics", "Linear Algebra", "Vector spaces, matrices, linear transformations, and system solving"),
        ("calculus", "mathematics", "Calculus", "Limits, derivatives, integrals, and differential equations"),
        ("probability_stats", "mathematics", "Probability & Statistics", "Probability distributions, hypothesis testing, and statistical inference"),
        ("discrete_math", "mathematics", "Discrete Mathematics", "Logic, sets, relations, graph theory, and combinatorics"),

        # Physics
        ("classical_mechanics", "physics", "Classical Mechanics", "Newton's laws of motion, momentum, energy conservation, and kinematics"),
        ("thermodynamics", "physics", "Thermodynamics", "Heat, work, laws of thermodynamics, entropy, and thermal physics"),
        ("electromagnetism", "physics", "Electromagnetism", "Electric fields, magnetic forces, circuits, and Maxwell's equations"),
        ("quantum_physics", "physics", "Quantum Physics", "Wave-particle duality, Schrödinger equation, and atomic structure")
    ]

    for tid, did, tname, tdesc in topics:
        cursor.execute(
            "INSERT INTO knowledge_topics (topic_id, domain_id, topic_name, description) VALUES (?, ?, ?, ?)",
            (tid, did, tname, tdesc)
        )

    # 3. SEED KNOWLEDGE COMPONENTS (KCs)
    kcs = [
        # Python KCs
        ("kc_var_assignment", "variables", "Variable Assignment", "Assigning values to variable names and re-assignment"),
        ("kc_var_scope", "variables", "Variable Naming & Scope", "Valid variable names, case-sensitivity, and basic scope"),
        
        ("kc_dt_types", "data_types", "Data Type Identification", "Recognizing int, float, str, bool, and type() output"),
        ("kc_dt_casting", "data_types", "Type Casting", "Converting values between int, float, and str"),
        
        ("kc_op_arithmetic", "operators", "Arithmetic Operators", "Evaluation of +, -, *, /, //, %, and ** operations"),
        ("kc_op_logical", "operators", "Comparison & Logical Operators", "Evaluating ==, !=, >, <, and, or, not expressions"),
        
        ("kc_cond_if_else", "conditions", "If-Else Branching", "Basic conditional execution paths with if and else"),
        ("kc_cond_nested", "conditions", "Elif & Compound Logic", "Multi-way branching with elif and combined boolean conditions"),
        
        ("kc_loop_for", "loops", "For Loops", "Iterating over ranges and sequences using for loops"),
        ("kc_loop_while", "loops", "While Loops", "Conditional iteration and loop control using while loops"),
        
        ("kc_fn_def", "functions", "Function Definition & Parameters", "Declaring def function_name(args) and passing arguments"),
        ("kc_fn_return", "functions", "Return Values", "Returning values from functions vs side-effect print()"),
        
        ("kc_list_creation", "lists", "List Creation & Operations", "Constructing lists, appending, popping, and slicing"),
        ("kc_list_indexing", "lists", "List Indexing & Iteration", "Accessing elements by 0-based index and looping through lists"),
        
        ("kc_dict_access", "dictionaries", "Dictionary Access & Modification", "Key lookup, value updates, and adding new keys"),
        ("kc_dict_iteration", "dictionaries", "Dictionary Iteration", "Looping through dict keys, values, and .items()"),

        # Mathematics KCs
        ("kc_matrix_ops", "linear_algebra", "Matrix Operations", "Matrix addition, scalar multiplication, and matrix multiplication"),
        ("kc_eigenvalues", "linear_algebra", "Eigenvalues & Eigenvectors", "Characteristic equations and linear transformation axes"),
        ("kc_derivatives", "calculus", "Derivatives & Chain Rule", "Rates of change, differentiation rules, and optimization"),
        ("kc_integrals", "calculus", "Integrals & Fundamental Theorem", "Definite and indefinite integrals, area under curves"),

        # Physics KCs
        ("kc_kinematics", "classical_mechanics", "Kinematics Equations", "Displacement, velocity, acceleration, and projectile motion"),
        ("kc_newton_laws", "classical_mechanics", "Newtonian Dynamics", "Forces, free-body diagrams, friction, and tension"),
        ("kc_first_law_thermo", "thermodynamics", "First Law of Thermodynamics", "Internal energy, heat exchange, and work done by gas"),
        ("kc_circuits", "electromagnetism", "DC Electric Circuits", "Ohm's law, Kirchhoff's voltage/current laws, and resistance")
    ]

    for kcid, tid, kname, kdesc in kcs:
        cursor.execute(
            "INSERT INTO knowledge_components (kc_id, topic_id, kc_name, description) VALUES (?, ?, ?, ?)",
            (kcid, tid, kname, kdesc)
        )

    # 4. SEED KNOWLEDGE QUESTIONS (24 questions total across Easy, Medium, Hard)
    questions = [
        # Variables
        ("Q_VAR_1", "variables", "kc_var_assignment",
         "What is the value of `x` after executing:\n```python\nx = 5\nx = x + 3\nx = x * 2\n```",
         "mcq", "Easy",
         json.dumps(["16", "13", "10", "8"]), "16",
         "First x becomes 5 + 3 = 8. Then x is multiplied by 2, resulting in 16."),

        ("Q_VAR_2", "variables", "kc_var_scope",
         "Which of the following is a valid Python variable name?",
         "mcq", "Easy",
         json.dumps(["2nd_value", "total-amount", "_user_score", "class"]), "_user_score",
         "Variable names can start with letters or underscores, but not digits or hyphens, and cannot be reserved keywords like 'class'."),

        ("Q_VAR_3", "variables", "kc_var_assignment",
         "What happens when you execute:\n```python\na, b = 10, 20\na, b = b, a\n```",
         "mcq", "Medium",
         json.dumps(["a becomes 20, b becomes 10", "a becomes 10, b becomes 20", "SyntaxError", "Both become 20"]), "a becomes 20, b becomes 10",
         "Tuple unpacking evaluates the right side first (20, 10) and assigns a = 20 and b = 10, swapping their values."),

        # Data Types
        ("Q_DT_1", "data_types", "kc_dt_types",
         "What is the result of `type(3.0)` in Python?",
         "mcq", "Easy",
         json.dumps(["<class 'int'>", "<class 'float'>", "<class 'str'>", "<class 'double'>"]), "<class 'float'>",
         "In Python, numbers with decimal points are represented as floating-point floats."),

        ("Q_DT_2", "data_types", "kc_dt_casting",
         "What will `int('15') + float('2.5')` evaluate to?",
         "mcq", "Medium",
         json.dumps(["17.5", "17", "'152.5'", "TypeError"]), "17.5",
         "int('15') becomes integer 15, float('2.5') becomes float 2.5. Adding them yields 17.5."),

        ("Q_DT_3", "data_types", "kc_dt_casting",
         "What happens when running `int('12.5')` directly?",
         "mcq", "Hard",
         json.dumps(["12", "12.5", "ValueError", "13"]), "ValueError",
         "int() cannot parse string representations of floats directly. You would need int(float('12.5'))."),

        # Operators
        ("Q_OP_1", "operators", "kc_op_arithmetic",
         "What is the output of `19 // 4` and `19 % 4`?",
         "mcq", "Easy",
         json.dumps(["4 and 3", "4.75 and 3", "4 and 0.75", "5 and 3"]), "4 and 3",
         "// performs integer floor division (19 // 4 = 4), % returns remainder (19 % 4 = 3)."),

        ("Q_OP_2", "operators", "kc_op_logical",
         "What is the boolean evaluation of `(True or False) and not (False and True)`?",
         "mcq", "Medium",
         json.dumps(["True", "False", "None", "SyntaxError"]), "True",
         "(True or False) is True. (False and True) is False. not (False) is True. True and True is True."),

        ("Q_OP_3", "operators", "kc_op_arithmetic",
         "What is the result of `2 ** 3 ** 2` due to exponentiation operator associativity?",
         "mcq", "Hard",
         json.dumps(["512", "64", "36", "12"]), "512",
         "Exponentiation operator `**` evaluates right-to-left: 3 ** 2 = 9, then 2 ** 9 = 512."),

        # Conditions
        ("Q_COND_1", "conditions", "kc_cond_if_else",
         "What is printed by:\n```python\nscore = 75\nif score >= 80:\n    print('A')\nelif score >= 70:\n    print('B')\nelse:\n    print('C')\n```",
         "mcq", "Easy",
         json.dumps(["B", "A", "C", "A and B"]), "B",
         "score 75 fails `score >= 80` but satisfies `score >= 70`, so 'B' is printed."),

        ("Q_COND_2", "conditions", "kc_cond_nested",
         "What is the output of:\n```python\nx = 10\ny = 5\nif x > 5:\n    if y > 10:\n        print('X')\n    else:\n        print('Y')\nelse:\n    print('Z')\n```",
         "mcq", "Medium",
         json.dumps(["Y", "X", "Z", "Nothing"]), "Y",
         "x > 5 is True. Inner condition y > 10 is False, executing the inner else block which prints 'Y'."),

        ("Q_COND_3", "conditions", "kc_cond_nested",
         "In Python, what is short-circuit evaluation in `if A and B:`?",
         "mcq", "Hard",
         json.dumps([
             "If A is False, B is not evaluated at all",
             "If A is True, B is not evaluated at all",
             "Both A and B are always evaluated simultaneously",
             "B is evaluated before A"
         ]), "If A is False, B is not evaluated at all",
         "With logical `and`, if the left operand is False, the overall expression must be False, so Python skips evaluating B."),

        # Loops
        ("Q_LOOP_1", "loops", "kc_loop_for",
         "What does `list(range(2, 8, 2))` generate?",
         "mcq", "Easy",
         json.dumps(["[2, 4, 6]", "[2, 4, 6, 8]", "[2, 3, 4, 5, 6, 7, 8]", "[4, 6, 8]"]), "[2, 4, 6]",
         "range(start, stop, step) starts at 2, steps by 2, and stops before reaching 8: [2, 4, 6]."),

        ("Q_LOOP_2", "loops", "kc_loop_while",
         "What will be printed by:\n```python\ncount = 1\nwhile count < 4:\n    print(count, end=' ')\n    count += 1\n```",
         "mcq", "Medium",
         json.dumps(["1 2 3", "1 2 3 4", "0 1 2 3", "2 3 4"]), "1 2 3",
         "The loop runs for count = 1, 2, 3. When count reaches 4, count < 4 is False and the loop stops."),

        ("Q_LOOP_3", "loops", "kc_loop_for",
         "What is printed by:\n```python\ntotal = 0\nfor i in range(3):\n    for j in range(2):\n        total += 1\nprint(total)\n```",
         "mcq", "Hard",
         json.dumps(["6", "5", "3", "2"]), "6",
         "Outer loop runs 3 times, inner loop runs 2 times per outer iteration. Total executions = 3 * 2 = 6."),

        # Functions
        ("Q_FN_1", "functions", "kc_fn_def",
         "What is the output of:\n```python\ndef greet(name='Student'):\n    return 'Hello ' + name\nprint(greet())\n```",
         "mcq", "Easy",
         json.dumps(["Hello Student", "Hello", "TypeError", "None"]), "Hello Student",
         "When called with no arguments, default parameter `name='Student'` is used."),

        ("Q_FN_2", "functions", "kc_fn_return",
         "Consider:\n```python\ndef add(a, b):\n    result = a + b\nres = add(3, 4)\nprint(res)\n```\nWhat is printed?",
         "mcq", "Medium",
         json.dumps(["None", "7", "TypeError", "0"]), "None",
         "The function lacks an explicit `return` statement, so it returns Python's default `None` value."),

        ("Q_FN_3", "functions", "kc_fn_def",
         "What is printed by:\n```python\ndef modify(val, items=[]):\n    items.append(val)\n    return items\nmodify(1)\nprint(modify(2))\n```",
         "mcq", "Hard",
         json.dumps(["[1, 2]", "[2]", "[1]", "TypeError"]), "[1, 2]",
         "Default mutable arguments like `items=[]` are evaluated once when the function is defined, sharing state across calls."),

        # Lists
        ("Q_LIST_1", "lists", "kc_list_creation",
         "Given `nums = [10, 20, 30, 40]`, what is `nums[1:3]`?",
         "mcq", "Easy",
         json.dumps(["[20, 30]", "[10, 20]", "[20, 30, 40]", "[30, 40]"]), "[20, 30]",
         "Slice [1:3] takes elements from index 1 up to (excluding) index 3: indices 1 and 2 ([20, 30])."),

        ("Q_LIST_2", "lists", "kc_list_indexing",
         "Given `vals = [1, 2, 3]`, what happens when you run `vals.append([4, 5])` vs `vals.extend([4, 5])`?",
         "mcq", "Medium",
         json.dumps([
             "append yields [1, 2, 3, [4, 5]], extend yields [1, 2, 3, 4, 5]",
             "Both yield [1, 2, 3, 4, 5]",
             "Both yield [1, 2, 3, [4, 5]]",
             "append raises AttributeError"
         ]), "append yields [1, 2, 3, [4, 5]], extend yields [1, 2, 3, 4, 5]",
         "`append` adds the object as a single element, while `extend` iterates over elements and appends each."),

        ("Q_LIST_3", "lists", "kc_list_indexing",
         "What is the output of `[x ** 2 for x in range(5) if x % 2 == 0]`?",
         "mcq", "Hard",
         json.dumps(["[0, 4, 16]", "[0, 1, 4, 9, 16]", "[4, 16]", "[1, 9]"]), "[0, 4, 16]",
         "range(5) gives 0, 1, 2, 3, 4. Even numbers are 0, 2, 4. Their squares are 0, 4, 16."),

        # Dictionaries
        ("Q_DICT_1", "dictionaries", "kc_dict_access",
         "How do you safely access value for key `'age'` in `user = {'name': 'Alice'}` without throwing KeyError if missing?",
         "mcq", "Easy",
         json.dumps(["user.get('age')", "user['age']", "user.find('age')", "user.age"]), "user.get('age')",
         "`dict.get(key)` returns None (or default) if key is not found instead of raising KeyError."),

        ("Q_DICT_2", "dictionaries", "kc_dict_access",
         "What is printed by:\n```python\nd = {'a': 1, 'b': 2}\nd['c'] = 3\nd['a'] = 10\nprint(len(d))\n```",
         "mcq", "Medium",
         json.dumps(["3", "4", "2", "KeyError"]), "3",
         "d['c'] = 3 adds a new key. d['a'] = 10 updates key 'a'. Dict length is 3 unique keys ('a', 'b', 'c')."),

        ("Q_DICT_3", "dictionaries", "kc_dict_iteration",
         "What is printed by:\n```python\nd = {'x': 10, 'y': 20}\nfor k, v in d.items():\n    print(k, v, end=' ')\n```",
         "mcq", "Hard",
         json.dumps(["x 10 y 20", "x y", "10 20", "('x', 10) ('y', 20)"]), "x 10 y 20",
         "d.items() yields (key, value) tuples unpacked into k and v, printing 'x 10 y 20'.")
    ]

    for qid, tid, kcid, qtext, qtype, diff, opts, ans, expl in questions:
        cursor.execute(
            """INSERT INTO knowledge_questions 
               (question_id, topic_id, kc_id, question_text, question_type, difficulty, options, correct_answer, explanation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (qid, tid, kcid, qtext, qtype, diff, opts, ans, expl)
        )

    conn.commit()
    conn.close()

    # 5. SEED COMPLETED DEMO ADMIN USER FOR TESTING
    seed_demo_admin_user()
    print("Database successfully seeded with survey questions, topics, KCs, baseline questions, and demo admin account.")

def seed_demo_admin_user():
    from werkzeug.security import generate_password_hash
    from profiling_engine import process_survey_responses, process_baseline_attempt

    conn = get_db()
    cursor = conn.cursor()

    student_id = "STU-ADMIN01"
    email = "admin@example.com"
    name = "Demo Admin Student"
    pwd_hash = generate_password_hash("admin123")

    # Insert or update student
    cursor.execute("""
        INSERT INTO students (student_id, name, email, password_hash, current_step)
        VALUES (?, ?, ?, ?, 'completed')
        ON CONFLICT(student_id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            password_hash=excluded.password_hash,
            current_step='completed';
    """, (student_id, name, email, pwd_hash))
    conn.commit()
    conn.close()

    # Seed 24 Survey Responses
    survey_responses = {
        "VARK_V1": 5, "VARK_V2": 4, # Visual = 0.875
        "VARK_A1": 2, "VARK_A2": 3, # Aural = 0.375
        "VARK_R1": 4, "VARK_R2": 4, # Read/Write = 0.75
        "VARK_K1": 1, "VARK_K2": 2, # Kinesthetic = 0.125
        "MOT_INT1": 5, "MOT_INT2": 5, # Intrinsic = 1.0
        "MOT_EXT1": 3, "MOT_EXT2": 3, # Extrinsic = 0.5
        "MOT_LGO1": 4, "MOT_LGO2": 4, # LGO = 0.75
        "MOT_TV1": 5, "MOT_TV2": 4,  # Task Value = 0.875
        "SR_GS1": 4, "SR_GS2": 4,    # Goal Setting = 0.75
        "SR_PL1": 3, "SR_PL2": 3,    # Planning = 0.50
        "SR_SM1": 5, "SR_SM2": 5,    # Self Monitoring = 1.0
        "SR_RB1": 2, "SR_RB2": 3     # Revision = 0.375
    }
    process_survey_responses(student_id, survey_responses)

    # Seed Baseline Test Attempt
    attempt_id = "ATT-ADMIN01"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO baseline_attempts (attempt_id, student_id)
        VALUES (?, ?);
    """, (attempt_id, student_id))

    cursor.execute("SELECT question_id, correct_answer FROM knowledge_questions;")
    questions = cursor.fetchall()
    conn.commit()
    conn.close()

    test_responses = []
    # Seed dynamic performance: high on variables/lists, medium on data_types/functions, low on conditions/dictionaries/operators
    wrong_qids = {"Q_OP_2", "Q_OP_3", "Q_COND_1", "Q_COND_2", "Q_COND_3", "Q_LOOP_2", "Q_LOOP_3", "Q_DICT_1", "Q_DICT_2", "Q_DICT_3", "Q_DT_3"}

    for q in questions:
        qid = q["question_id"]
        ans = q["correct_answer"] if qid not in wrong_qids else "WRONG_ANSWER"
        test_responses.append({
            "question_id": qid,
            "selected_answer": ans,
            "response_time_seconds": 14.5
        })

    process_baseline_attempt(student_id, attempt_id, test_responses)

    # Generate initial AI recommendations for Python, Math, Physics for admin user
    try:
        from services.recommendation_service import generate_learning_recommendation
        for d in ["python", "mathematics", "physics"]:
            generate_learning_recommendation(student_id, d, force_mock=True)
    except Exception as e:
        pass

if __name__ == "__main__":
    seed_database()
