from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time
import re
import html
from models import db, User
from forms import LoginForm, RegistrationForm

# Încarcă cheia API
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' # Only keep the users database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = ''
login_manager.login_message_category = 'info'

# Initialize SQLAlchemy
db.init_app(app)

# Create database tables (only for users now)
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# === Vector store-urile deja create (înlocuiește cu ID-urile reale obținute la upload) ===
vector_stores = {
    "9": client.vector_stores.retrieve("vs_68336c8213308191949fbb3b53d20e67"),
    "10": client.vector_stores.retrieve("vs_68336c5facbc8191becf60fe5b02fa8e"),
    "11-12": client.vector_stores.retrieve("vs_68336c5f54748191bc3a4e9e632103a4")
}

# === Instrucțiuni pentru AI ===
with open(os.path.join(os.path.dirname(__file__), "instructions.txt"), encoding="utf-8") as f:
    base_instructions = f.read()

# === Creează asistenții la pornirea aplicației ===
assistants = {}
for clasa in vector_stores:
    assistants[clasa] = client.beta.assistants.create(
        instructions=base_instructions + f"\n\nElevul este în clasa a {clasa}-a. Ajustează explicațiile pentru acest nivel.",
        name=f"infocoach_clasa_{clasa}",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_stores[clasa].id]}},
        model="gpt-4o",
        temperature=0.3,
        top_p=0.8
    )

# === Inițializare baza de date SQLite (Feedback) ===
def init_db():
    os.makedirs('feedback', exist_ok=True)
    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            clasa TEXT,
            user_input TEXT,
            ai_response TEXT,
            feedback TEXT,
            feedback_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize feedback database
init_db()

# === Funcție pentru gestionarea conversațiilor ===
def get_active_conversation(user_id, clasa):
    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    
    # Verifică dacă există o conversație activă
    c.execute('''
        SELECT id, message_count 
        FROM conversations 
        WHERE user_id = ? AND clasa = ? AND is_active = 1
    ''', (user_id, clasa))
    
    conversation = c.fetchone()
    
    if conversation:
        # Dacă conversația a atins limita, o închide
        if conversation[1] >= 10:
            c.execute('UPDATE conversations SET is_active = 0 WHERE id = ?', (conversation[0],))
            conn.commit()
            conn.close()
            return None
        return conversation[0]
    
    # Creează o nouă conversație
    c.execute('''
        INSERT INTO conversations (user_id, clasa, start_time, message_count)
        VALUES (?, ?, ?, 0)
    ''', (user_id, clasa, datetime.now().isoformat()))
    
    conn.commit()
    conversation_id = c.lastrowid
    conn.close()
    
    return conversation_id

# === Funcție pentru salvarea mesajelor ===
def save_message(conversation_id, user_input, ai_response):
    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    
    # Salvează mesajul
    c.execute('''
        INSERT INTO messages (conversation_id, user_input, ai_response, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (conversation_id, user_input, ai_response, datetime.now().isoformat()))
    
    # Incrementează contorul de mesaje
    c.execute('''
        UPDATE conversations 
        SET message_count = message_count + 1 
        WHERE id = ?
    ''', (conversation_id,))
    
    conn.commit()
    conn.close()

# === Funcție pentru obținerea istoricului conversației ===
def get_conversation_history(conversation_id):
    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT user_input, ai_response, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    ''', (conversation_id,))
    
    messages = c.fetchall()
    conn.close()
    
    return messages

# === Funcție pentru formatarea blocurilor de cod C++ ===
def format_code_blocks(text):
    def replacer(match):
        code = html.escape(match.group(1))
        return f'<pre><code class="cpp">{code}</code></pre>'
    return re.sub(r'```cpp\s*([\s\S]*?)```', replacer, text)

# === Funcție pentru formatarea pașilor, alineatelor, variabilelor și bold ===
def format_steps_and_paragraphs(text):
    # Separă blocurile de cod deja formatate
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            # Nu modifica blocurile de cod!
            formatted.append(part)
        else:
            # Aplicați regex DOAR pe textul non-cod!
            lines = part.split('\n')
            in_list = False
            list_items = []
            new_lines = []
            for line in lines:
                # Tratează header-ele H3 (Explicații:) specific
                if line.strip().startswith('###'):
                    new_lines.append(line) # Lăsăm header-ul așa cum e
                    continue # Treci la linia următoare după header

                # Evidențiază textul bold marcat cu **text**
                line = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", line)

                # Găsește și formatează itemii listelor ordonate (dacă există)
                m = re.match(r'^\s*(\d+)\.\s+(.*)', line)
                if m:
                    # Dacă nu eram într-o listă, începe o listă nouă
                    if not in_list:
                         in_list = True
                         if new_lines and not new_lines[-1].startswith('<p>') and not new_lines[-1].startswith('<ol>'):
                             pass

                    # Adaugă itemul curent la lista
                    list_items.append(f"<li>{m.group(2).strip()}</li>")
                else:
                    # Dacă eram într-o listă și linia curentă nu e un item de listă,
                    # încheie lista și adaugă la new_lines
                    if in_list:
                        new_lines.append("<ol>" + "".join(list_items) + "</ol>")
                        list_items = []
                        in_list = False
                    
                    # Adaugă linia non-listă ca un paragraf, dacă nu e goală
                    if line.strip():
                        new_lines.append(f"<p>{line.strip()}</p>")

            # După buclă, dacă s-a terminat cu o listă, adaug-o
            if in_list:
                new_lines.append("<ol>" + "".join(list_items) + "</ol>")

            # Alătură liniile procesate pentru această parte
            formatted.append('\n'.join(new_lines))
    
    # Alătură toate părțile (cod și non-cod) înapoi
    return ''.join(formatted)

# === Funcție pentru formatarea cuvintelor între backticks ===
def format_inline_code(text):
    # Verifică dacă textul conține deja HTML formatat
    if '<pre><code class="cpp">' in text:
        return text
        
    def replacer(match):
        code = html.escape(match.group(1))
        return f'<span style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace; color: #333;">{code}</span>'
    
    # Găsește toate aparițiile de text între backticks, inclusiv cele cu caractere speciale
    pattern = r'`([^`]+?)`'
    
    # Împarte textul în părți pentru a evita formatarea în blocurile de cod
    parts = re.split(r'(<pre><code class="cpp">[\s\S]*?<\/code><\/pre>)', text)
    formatted = []
    
    for part in parts:
        if part.startswith('<pre><code class="cpp">'):
            # Nu modifica blocurile de cod
            formatted.append(part)
        else:
            # Aplică formatarea pentru backticks în restul textului
            # Înlocuiește temporar caracterele speciale pentru a evita conflictele
            temp_part = part.replace('#', '___HASH___')
            temp_part = re.sub(pattern, replacer, temp_part)
            # Restaurează caracterele speciale
            temp_part = temp_part.replace('___HASH___', '#')
            formatted.append(temp_part)
    
    return ''.join(formatted)

# === Ruta pentru login ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Autentificare reușită!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Nume de utilizator sau parolă incorectă', 'danger')
    return render_template('login.html', form=form)

# === Ruta pentru register ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Înregistrare reușită! Te rugăm să te autentifici.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# === Ruta pentru logout ===
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ai fost deconectat cu succes.', 'info')
    return redirect(url_for('index'))

# === Ruta principală ===
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_input = ''
    output = ''
    clasa = '9'

    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        clasa = request.form.get('clasa', '9')

        # Nu mai escapăm HTML pentru input-ul utilizatorului
        prompt_content = (
            f"{user_input}\n"
            "Te rog să folosești cât mai mult informațiile din resursele disponibile."
        )

        assistant = assistants[clasa]

        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt_content)

        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

        while run.status not in ["completed", "failed"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread.id)

        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for m in reversed(messages.data):
                if m.role == "assistant":
                    output = m.content[0].text.value
                    
                    # Filter out references like 【4:0†source】
                    output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
                    
                    # Format the output for HTML display
                    formatted_output = format_code_blocks(output)
                    formatted_output = format_steps_and_paragraphs(formatted_output)

                    # Render the assistant message fragment and return it
                    return render_template('assistant_message.html', 
                                        output=formatted_output,
                                        user_input=user_input, 
                                        clasa=clasa)

        # If the run failed or no assistant message was found
        return "A apărut o problemă la generarea răspunsului asistentului.", 500

    # For GET requests, render the full index page with initial (or last) data
    return render_template('index.html', user_input=user_input, output=output, clasa=clasa)

# === Ruta pentru API chat ===
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    user_input = request.form.get('user_input', '')
    clasa = request.form.get('clasa', '9')

    if not user_input:
        return jsonify({'error': 'Lipsește input-ul utilizatorului'}), 400

    # Nu mai escapăm HTML pentru input-ul utilizatorului
    prompt_content = (
        f"{user_input}\n"
        "Te rog să folosești cât mai mult informațiile din resursele disponibile."
    )

    assistant = assistants[clasa]

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt_content)

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

    while run.status not in ["completed", "failed"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(run_id=run.id, thread_id=thread.id)

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for m in reversed(messages.data):
            if m.role == "assistant":
                output = m.content[0].text.value
                
                # Filter out references like 【4:0†source】
                output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
                
                # Format the output for HTML display
                formatted_output = format_code_blocks(output)
                formatted_output = format_steps_and_paragraphs(formatted_output)

                return jsonify({
                    'success': True,
                    'response': formatted_output
                })

    return jsonify({
        'success': False,
        'error': 'A apărut o problemă la generarea răspunsului asistentului.'
    }), 500

# === Ruta pentru salvare feedback ===
@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    try:
        # Get and validate required fields
        user_input = request.form.get('user_input', '').strip()
        ai_response = request.form.get('ai_response', '').strip()
        clasa = request.form.get('clasa', '').strip()
        fb = request.form.get('feedback', '').strip()
        feedback_text = request.form.get('feedback_text', '').strip()
        
        app.logger.info(f"Received feedback request - Clasa: {clasa}, Feedback: {fb}, Text: {feedback_text}")
        
        # Validate inputs
        if not user_input:
            app.logger.warning("Missing user input")
            return jsonify({'error': 'Lipsește input-ul utilizatorului'}), 400
        if not ai_response:
            app.logger.warning("Missing AI response")
            return jsonify({'error': 'Lipsește răspunsul asistentului'}), 400
        if not clasa:
            app.logger.warning("Missing class")
            return jsonify({'error': 'Lipsește clasa'}), 400
        if not fb:
            app.logger.warning("Missing feedback")
            return jsonify({'error': 'Lipsește feedback-ul'}), 400
            
        # Sanitize inputs
        user_input = html.escape(user_input)
        # Nu mai escapăm HTML pentru răspunsul AI, îl salvăm așa cum este
        clasa = html.escape(clasa)
        fb = html.escape(fb)
        feedback_text = html.escape(feedback_text)
        
        # Ensure feedback directory exists
        feedback_dir = os.path.join(os.path.dirname(__file__), 'feedback')
        os.makedirs(feedback_dir, exist_ok=True)
        app.logger.info(f"Feedback directory: {feedback_dir}")
        
        # Database path
        db_path = os.path.join(feedback_dir, 'feedback.db')
        app.logger.info(f"Database path: {db_path}")
        
        # Save to database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        try:
            # Verifică dacă coloana feedback_text există
            c.execute("PRAGMA table_info(feedback)")
            columns = [column[1] for column in c.fetchall()]
            app.logger.info(f"Existing columns: {columns}")
            
            # Dacă coloana nu există, o adaugă
            if 'feedback_text' not in columns:
                app.logger.info("Adding feedback_text column")
                c.execute('ALTER TABLE feedback ADD COLUMN feedback_text TEXT')
                conn.commit()
                app.logger.info("Added feedback_text column to feedback table")
        except sqlite3.OperationalError as e:
            # Dacă tabela nu există, o creează cu toate coloanele
            app.logger.info("Creating feedback table")
            c.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    clasa TEXT,
                    user_input TEXT,
                    ai_response TEXT,
                    feedback TEXT,
                    feedback_text TEXT
                )
            ''')
            conn.commit()
            app.logger.info("Created feedback table with all columns")
        
        # Insert feedback
        app.logger.info("Inserting feedback")
        c.execute('''
            INSERT INTO feedback (timestamp, clasa, user_input, ai_response, feedback, feedback_text)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), clasa, user_input, ai_response, fb, feedback_text))
        
        conn.commit()
        conn.close()
        
        app.logger.info("Feedback saved successfully")
        return jsonify({'message': 'Feedback salvat cu succes!'})
        
    except sqlite3.Error as e:
        app.logger.error(f"Database error: {str(e)}")
        return jsonify({'error': f'Eroare la salvarea în baza de date: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'A apărut o eroare neașteptată: {str(e)}'}), 500

# === Ruta pentru vizualizare feedback ===
@app.route('/view-feedback')
@login_required
def view_feedback():
    # Obține parametrii de filtrare din query string
    clasa_filter = request.args.get('clasa', '')
    feedback_filter = request.args.get('feedback', '')
    
    # Conectare la baza de date
    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    
    # Construiește query-ul SQL cu filtre
    query = 'SELECT * FROM feedback WHERE 1=1'
    params = []
    
    if clasa_filter:
        query += ' AND clasa = ?'
        params.append(clasa_filter)
    
    if feedback_filter:
        query += ' AND feedback = ?'
        params.append(feedback_filter)
    
    query += ' ORDER BY timestamp DESC'
    
    # Execută query-ul cu parametrii
    c.execute(query, params)
    feedback_entries = c.fetchall()
    
    # Închide conexiunea
    conn.close()
    
    # Convertește rezultatele în format ușor de folosit în template
    entries = []
    for entry in feedback_entries:
        # Verifică dacă răspunsul conține deja HTML
        if '<pre><code class="cpp">' in entry[4]:
            # Dacă conține deja HTML, îl folosim direct
            formatted_response = entry[4]
        else:
            # Dacă nu conține HTML, aplicăm formatarea
            formatted_response = format_code_blocks(entry[4])
            formatted_response = format_steps_and_paragraphs(formatted_response)
            # Aplică formatarea pentru cuvintele între backticks
            formatted_response = format_inline_code(formatted_response)
        
        entries.append({
            'timestamp': entry[1],
            'clasa': entry[2],
            'user_input': entry[3],
            'ai_response': formatted_response,
            'feedback': entry[5],
            'feedback_text': entry[6] if len(entry) > 6 else ''
        })
    
    return render_template('view_feedback.html', 
                         feedback_entries=entries,
                         current_clasa=clasa_filter,
                         current_feedback=feedback_filter)

# === Ruta pentru creare admin ===
@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    # Verifică dacă există deja un admin
    admin_exists = User.query.filter_by(is_admin=True).first()
    if admin_exists:
        flash('Un cont de administrator există deja.', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('Toate câmpurile sunt obligatorii.', 'danger')
            return render_template('create_admin.html')
        
        # Verifică dacă username-ul sau email-ul există deja
        if User.query.filter_by(username=username).first():
            flash('Acest nume de utilizator există deja.', 'danger')
            return render_template('create_admin.html')
        
        if User.query.filter_by(email=email).first():
            flash('Acest email există deja.', 'danger')
            return render_template('create_admin.html')
        
        # Creează utilizatorul admin
        admin = User(username=username, email=email, is_admin=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        
        flash('Contul de administrator a fost creat cu succes!', 'success')
        return redirect(url_for('login'))
    
    return render_template('create_admin.html')

# === Pornire aplicație ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)