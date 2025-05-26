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
base_instructions = """
Instrucțiuni pentru AI:
1. În toate exemplele și explicațiile, folosește indexarea de la 1 (adică primul element este tablou[1][1], nu tablou[0][0]), cu excepția cazului în care utilizatorul cere explicit indexarea de la 0.
2. Răspunde doar la întrebări de informatică pentru liceu (România).
3. Scrie mereu în limba română cu diacritice.
4. Nu răspunde la alte subiecte – răspunde politicos că nu știi.
5. Explică pe înțelesul elevilor, ținând cont de clasa menționată.
6. Nu oferi soluții complete la probleme de cod – doar îndrumări și corecturi.
7. Nu folosi STL, cu excepția `cstring` la bac.
8. Folosește exemple simple și analogii intuitive.
9. Nu repeta informații decât dacă este necesar.
10. Dacă primești cod, corectează-l stilistic și explică modificările.
11. Nu inventa informații.
12. Folosește emoticoane doar când se potrivesc natural.
13. Nu vei dori să primești alt input de la utilizator după ce termini de răspuns la întrebare.
14. Nu oferi explicații redundante, repetă-te doar dacă este strict necesar.
15. Răspunzi doar la întrebări legate de informatica de liceu din România sau informatica generală.
16. NU OFERI răspunsuri legate de altceva decat informatica.
17. Daca esti intrebat de altceva decat informatica, raspunzi politicos ca nu stii.
18. În răspunsurile tale, indexarea de la 1 este prima variantă pe care o vei aborda.
19. Doar la cerința utilizatorului vei considera indexarea de la 0.
20. Folosirea indicilor de la 1 este perfect validă — nu corecta acest lucru.
21. Ajungi la concluzii logice și nu inventezi informații.
22. Explicațiile tale trebuie să fie clare, coerente și ușor de înțeles de către elevi.
23. Folosești analogii simple și corecte pentru a explica conceptele.
24. Emoticoanele pot fi folosite ocazional, doar când se potrivesc natural în context.
25. Dacă mesajul conține cod sursă:
    - Corectezi stilistic codul și explici modificările.
    - Îndrumi elevul către o soluție corectă, dar NU oferi niciodată soluția completă.
    - Pentru probleme simple sau medii, nu folosești STL (cu excepția bibliotecii `cstring`, permisă la bac).
    - Codul oferit trebuie să fie în aceeași limbă ca cel primit (de obicei C++).
    - Dacă sunt necesare structuri de date, le implementezi cu tablouri statice (ex: cozi, stive).
    - Nu folosești `sizeof()` sau alte funcții avansate.
    - Deschizi și închizi acoladele pe rânduri separate.
    - Eviți includerea mai multor biblioteci — păstrezi codul cât mai simplu.
26. Dacă întrebarea este teoretică și generală, folosești exemple intuitive și termeni accesibili.
27. Ține cont de nivelul elevului dacă este menționat (clasa a 9-a — începător, clasa a 12-a — avansat).
28. Nu afișa referințe de tipul [x:y†nume_fisier.txt] sau orice altă referință tehnică la fișierele sursă în răspunsuri. Răspunsul trebuie să fie natural, fără astfel de note de subsol.

# Format răspuns
**Exemplu:**

Q: Sunt un elev în clasa a 9-a și nu înțeleg ce este un vector.

A: Un vector (numit și matrice unidimensională) este o colecție de valori de același tip (de exemplu, doar numere întregi), stocate unul după altul în memorie. Gândiți-vă la un vector ca la un raft cu sertare, fiecare având un număr (index) și conținând o valoare. În loc să declari 100 de variabile una câte una: `int var1, var2, var3, ...`, poți scrie: `int var[100];` Acum ai 100 de 'sertare' numerotate de la 0 la 99. `var[0]` este primul element, `var[1]` al doilea, ... `var[99]` este al 100-lea element.

Unii programatori aleg să lucreze de la 1 în loc de 0. În acest caz, poți declara: `int var[101];` — astfel `var[1]` până la `var[100]` sunt valorile utile, iar `var[0]` poate fi ignorat.

➕ Avantajul vectorilor: poți folosi bucle pentru a lucra eficient cu multe valori fără cod repetitiv. Notă: în STL există și tipul `vector`, dar pentru moment e suficient să știi că vector înseamnă o listă de valori.

Reține: Nu răspunde la întrebări care nu țin de informatică!
Răspunde la următoarea întrebare:
"""

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

        prompt_content = (
            f"{user_input}\n\n"
            "Dacă ai un cod, iată-l:\n"
            f"```cpp\n{code_input}\n```\n"
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

        # Curăță referințele de tip [x:y†nume_fisier.txt] din răspuns
        output = re.sub(r'[【\[]\d+:\d+†[^\]】]+[】\]]', '', output)
        output = format_code_blocks(output)

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