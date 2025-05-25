#
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), 'feedback.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("Scrie o comandă SQL (sau 'exit' pentru a ieși):")
while True:
    cmd = input("sqlite> ")
    if cmd.lower() in ("exit", "quit"):
        break
    if cmd.strip() == ".schema":
        try:
            for row in c.execute("SELECT sql FROM sqlite_master WHERE type='table'"):
                print(row[0])
        except Exception as e:
            print("Eroare:", e)
        continue
    try:
        for row in c.execute(cmd):
            print(row)
        conn.commit()
    except Exception as e:
        print("Eroare:", e)

conn.close()