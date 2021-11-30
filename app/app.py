#!/usr/bin/python

from datetime import datetime
from flask import *
import psycopg2
import os
import time

while True:
    try:
        conn = psycopg2.connect(database="postgresdb", user="postgres", password=os.environ.get("POSTGRES_PASSWORD"), host="postgres", port="5432")
        print("Opened database successfully", flush=True)
        break
    except Exception as e:
        print(e, flush=True)
        time.sleep(5)

cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS actuals (ts TIMESTAMP, value float);")
conn.commit()

cur.execute("SELECT * FROM actuals;")
if (cur.rowcount == 0):
    cur.execute("INSERT INTO actuals(ts, value) VALUES ('%s', 55) RETURNING *;" % datetime.now())
    conn.commit()

cur.execute("SELECT * FROM actuals;")

app = Flask(__name__)

@app.route('/')
def index():
    cur.execute("SELECT * FROM actuals;")
    data = [{"date": d[0], "value": d[1]} for d in cur.fetchall()] 
    return render_template('table.html', title='Actuals', data=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

