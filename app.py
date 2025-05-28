from flask import Flask, render_template, request
import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time
import re
import html

# Încarcă cheia API
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = Flask(__name__)

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

# === Inițializare baza de date SQLite ===
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
            feedback TEXT
        )
    ''')
    conn.commit()
    conn.close()

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
                # Eliminat: Evidențiază variabilele marcate cu 'n' sau 'variabila'
                # Evidențiază textul bold marcat cu **text**
                line = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", line)
                m = re.match(r'^\s*(\d+)\.\s+(.*)', line)
                if m:
                    in_list = True
                    list_items.append(f"<li>{m.group(2).strip()}</li>")
                else:
                    if in_list:
                        new_lines.append("<ol>" + "".join(list_items) + "</ol>")
                        list_items = []
                        in_list = False
                    if line.strip():
                        new_lines.append(f"<p>{line.strip()}</p>")
            if in_list:
                new_lines.append("<ol>" + "".join(list_items) + "</ol>")
            formatted.append('\n'.join(new_lines))
    return ''.join(formatted)

# === Ruta principală ===
@app.route('/', methods=['GET', 'POST'])
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
                    break
        else:
            output = "A apărut o eroare la generarea răspunsului. Verifică conexiunea sau încearcă din nou."

        output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
        output = format_code_blocks(output)
        output = format_steps_and_paragraphs(output)

    return render_template('index.html', user_input=user_input, output=output, clasa=clasa)

# === Ruta pentru salvare feedback ===
@app.route('/feedback', methods=['POST'])
def feedback():
    user_input = request.form.get('user_input', '')
    ai_response = request.form.get('ai_response', '')
    clasa = request.form.get('clasa', '')
    fb = request.form.get('feedback', '')

    conn = sqlite3.connect('feedback/feedback.db')
    c = conn.cursor()
    c.execute('INSERT INTO feedback (timestamp, clasa, user_input, ai_response, feedback) VALUES (?, ?, ?, ?, ?)',
              (datetime.now().isoformat(), clasa, user_input, ai_response, fb))
    conn.commit()
    conn.close()

    return '', 204

# === Pornire aplicație ===
if __name__ == '__main__':
    init_db()
    app.run(debug=True)