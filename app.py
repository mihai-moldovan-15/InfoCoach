from flask import Flask, render_template, request
import os
import sqlite3
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import time

# Încarcă cheia API
load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = Flask(__name__)

# === Calea către resurse ===
VECTOR_STORE_PATHS = {
    "9": "C:/Users/user/OneDrive/Documents/GitHub/InfoCoach/resources/resurse_pbinfo/clasa_9/",
    "10": "C:/Users/user/OneDrive/Documents/GitHub/InfoCoach/resources/resurse_pbinfo/clasa_10/",
    "11-12": "C:/Users/user/OneDrive/Documents/GitHub/InfoCoach/resources/resurse_pbinfo/clasa_11_12/"
}


# === Preîncarcă vector store-urile ===
vector_stores = {}
for cls, path in VECTOR_STORE_PATHS.items():
    file_ids = []
    for file in sorted(os.listdir(path)):
        full_path = os.path.join(path, file)
        if os.path.isfile(full_path):
            _file = client.files.create(file=open(full_path, "rb"), purpose="assistants")
            file_ids.append(_file.id)
    vector_store = client.vector_stores.create(name=f"infocoach_clasa_{cls}", file_ids=file_ids)
    vector_stores[cls] = vector_store

# === Instrucțiuni pentru AI ===
base_instructions = """Ești un profesor politicos de informatică de liceu, foarte priceput și dornic să explice pe înțelesul elevilor."
    "Nu vei dori să primești alt input de la utilizator după ce termini de răspuns la întrebare. "
    "Nu oferi explicații redundante, repetă-te doar dacă este strict necesar. "
    "Răspunzi doar la întrebări legate de informatica de liceu din România sau informatica generală. "
    "NU OFERI răspunsuri legate de altceva decat informatica. "
    "Daca esti intrebat de altceva decat informatica, raspunzi politicos ca nu stii. "
    "Scrii întotdeauna în limba română cu diacritice. "
    "În răspunsurile tale, indexarea de la 1 este prima variantă pe care o vei aborda. "
    "Doar la cerința utilizatorului vei considera indexarea de la 0. "
    "Folosirea indicilor de la 1 este perfect validă — nu corecta acest lucru. "
    "Ajungi la concluzii logice și nu inventezi informații. "
    "Explicațiile tale trebuie să fie clare, coerente și ușor de înțeles de către elevi. "
    "Folosești analogii simple și corecte pentru a explica conceptele. "
    "Emoticoanele pot fi folosite ocazional, doar când se potrivesc natural în context. "
    "Dacă mesajul conține cod sursă: "
    "- Corectezi stilistic codul și explici modificările. "
    "- Îndrumi elevul către o soluție corectă, dar NU oferi niciodată soluția completă. "
    "- Pentru probleme simple sau medii, nu folosești STL (cu excepția bibliotecii `cstring`, permisă la bac). "
    "- Codul oferit trebuie să fie în aceeași limbă ca cel primit (de obicei C++). "
    "- Dacă sunt necesare structuri de date, le implementezi cu tablouri statice (ex: cozi, stive). "
    "- Nu folosești `sizeof()` sau alte funcții avansate. "
    "- Deschizi și închizi acoladele pe rânduri separate. "
    "- Eviți includerea mai multor biblioteci — păstrezi codul cât mai simplu. "
    "Dacă întrebarea este teoretică și generală, folosești exemple intuitive și termeni accesibili. "
    "Ține cont de nivelul elevului dacă este menționat (clasa a 9-a — începător, clasa a 12-a — avansat). "
    "# Format răspuns\n"
    "**Exemplu:**\n\n"
    "Q: Sunt un elev în clasa a 9-a și nu înțeleg ce este un vector.\n\n"
    "A: Un vector (numit și matrice unidimensională) este o colecție de valori de același tip (de exemplu, doar numere întregi), stocate unul după altul în memorie. "
    "Gândiți-vă la un vector ca la un raft cu sertare, fiecare având un număr (index) și conținând o valoare. "
    "În loc să declari 100 de variabile una câte una: `int var1, var2, var3, ...`, poți scrie: `int var[100];` "
    "Acum ai 100 de 'sertare' numerotate de la 0 la 99. "
    "`var[0]` este primul element, `var[1]` al doilea, ... `var[99]` este al 100-lea element.\n\n"
    "Unii programatori aleg să lucreze de la 1 în loc de 0. În acest caz, poți declara:\n"
    "`int var[101];` — astfel `var[1]` până la `var[100]` sunt valorile utile, iar `var[0]` poate fi ignorat.\n\n"
    "➕ Avantajul vectorilor: poți folosi bucle pentru a lucra eficient cu multe valori fără cod repetitiv. "
    "Notă: în STL există și tipul `vector`, dar pentru moment e suficient să știi că vector înseamnă o listă de valori.\n\n"
    
    
    "Răspunde la următoarea întrebare:\n"""

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

# === Ruta principală ===
@app.route('/', methods=['GET', 'POST'])
def index():
    user_input = ''
    code_input = ''
    output = ''
    clasa = '9'

    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        code_input = request.form.get('code_input', '')
        clasa = request.form.get('clasa', '9')

        prompt_content = f"{user_input}\n\nDacă ai un cod, iată-l:\n```cpp\n{code_input}\n```"
        prompt_with_class = base_instructions + f"\n\nElevul este în clasa a {clasa}-a. Ajustează explicațiile pentru acest nivel."

        assistant = client.beta.assistants.create(
            instructions=prompt_with_class,
            name=f"infocoach_clasa_{clasa}",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_stores[clasa].id]}},
            model="gpt-4o",
            temperature=0.3,
            top_p=0.8
        )

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

    return render_template('index.html', user_input=user_input, code_input=code_input, output=output, clasa=clasa)

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
