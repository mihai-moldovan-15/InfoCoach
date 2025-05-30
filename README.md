# InfoCoach - Asistent AI pentru Informatică

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-web--framework-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

O aplicație web bazată pe Flask care oferă un asistent AI specializat pentru învățarea informaticii, adaptat pentru clasele 9-12. Aplicația folosește OpenAI GPT-4 pentru a oferi răspunsuri personalizate și interactive, cu suport pentru C++ și salvarea conversațiilor.

---

## ⚙️ Funcționalități Principale

- 🤖 Asistent AI specializat pentru informatică  
- 📚 Conținut adaptat pentru clasele 9-12  
- 💬 Interfață de chat interactivă, în stil ChatGPT  
- 🧠 Istoric conversații pentru fiecare utilizator  
- ✍️ Rezumare automată a fiecărei conversații  
- 📝 Sistem de feedback pentru îmbunătățirea răspunsurilor  
- 🔒 Sistem de autentificare și înregistrare  
- 📊 Vizualizare și filtrare feedback  
- 💻 Suport pentru cod C++ cu formatare și syntax highlighting  

---

## 🖥️ Cerințe Sistem

- Python 3.8 sau mai nou  
- pip (Python package installer)  
- SQLite3  
- Cont OpenAI cu acces la API GPT-4  

---

## 🚀 Instalare

1. Clonează repository-ul:
```bash
git clone https://github.com/<utilizator>/InfoCoach.git
cd InfoCoach
```

2. Creează și activează un mediu virtual:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix/MacOS
source .venv/bin/activate
```

3. Instalează dependențele:
```bash
pip install -r requirements.txt
```

4. Creează un fișier `.env` cu variabilele de configurare:
```
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key
```

---

## 🗂️ Structura Proiectului

```
.
├── app.py              # Aplicația principală Flask
├── models.py           # Modelele bazei de date (utilizatori, feedback, conversații)
├── forms.py            # Formulare web (login, register, feedback)
├── chat/               # Logica pentru gestionarea conversațiilor
├── feedback/           # Gestionarea feedback-ului
├── static/             # Fișiere CSS și JavaScript
├── templates/          # Pagini HTML (chat, login, dashboard etc.)
├── requirements.txt    # Lista cu dependențe Python
└── resources/          # Resurse educaționale suplimentare
```

---

## ▶️ Rulare Locală

1. Asigură-te că mediul virtual este activat  
2. Rulează aplicația Flask:
```bash
python app.py
```
3. Deschide browser-ul și accesează `http://localhost:5000`

---

## 🧑‍🏫 Utilizare

1. Creează un cont nou sau autentifică-te  
2. Selectează clasa (9-12)  
3. Scrie întrebările tale despre informatică (teorie sau cod)  
4. Primește răspunsuri personalizate cu explicații detaliate  
5. Oferă feedback pentru a îmbunătăți calitatea răspunsurilor  
6. Accesează istoricul conversațiilor și vezi rezumate rapide  

---

## 🔐 Caracteristici Tehnice

- **Autentificare securizată** (hashing parole, CSRF protection)  
- **Bază de date relațională** cu SQLite + SQLAlchemy  
- **Interfață modernă** și responsive  
- **Persistență conversații** și generare de rezumate cu AI  
- **Highlight cod C++** pentru răspunsuri tehnice  

---

## 🤝 Contribuție

1. Fork acest repository  
2. Creează un branch nou (`git checkout -b feature-nou`)  
3. Commit modificările tale (`git commit -am 'Adaug funcționalitate X'`)  
4. Push la branch (`git push origin feature-nou`)  
5. Creează un Pull Request 🙌  

---

## 📄 Licență

Acest proiect este licențiat sub [MIT License](LICENSE).

---

## 📬 Suport

Pentru suport sau întrebări:

- Deschide un [issue pe GitHub](https://github.com/<utilizator>/InfoCoach/issues)  
- Trimite un email la: `mihai.moldovan152007 [at] gmail [dot] com`  
