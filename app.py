from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
# import sqlite3 # Removed as feedback database is removed
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

# === Inițializare baza de date SQLite (Feedback) - Removed ===
# def init_db():
#     os.makedirs('feedback', exist_ok=True)
#     conn = sqlite3.connect('feedback/feedback.db')
#     c = conn.cursor()
#     c.execute('''
#         CREATE TABLE IF NOT EXISTS feedback (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             timestamp TEXT,
#             clasa TEXT,
#             user_input TEXT,
#             ai_response TEXT,
#             feedback TEXT
#         )
#     ''')
#     conn.commit()
#     conn.close()

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
                    
                    # === Filter out references like 【4:0†source】 ===
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

# === Ruta pentru salvare feedback === # Removed
# @app.route('/feedback', methods=['POST'])
# @login_required
# def feedback():
#     user_input = request.form.get('user_input', '')
#     ai_response = request.form.get('ai_response', '')
#     clasa = request.form.get('clasa', '')
#     fb = request.form.get('feedback', '')

#     conn = sqlite3.connect('feedback/feedback.db')
#     c = conn.cursor()
#     c.execute('INSERT INTO feedback (timestamp, clasa, user_input, ai_response, feedback) VALUES (?, ?, ?, ?, ?)',
#               (datetime.now().isoformat(), clasa, user_input, ai_response, fb))
#     conn.commit()
#     conn.close()

#     return '', 204

# === Pornire aplicație ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    # init_db() # Removed feedback db initialization
    app.run(debug=True)