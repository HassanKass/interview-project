import os
import time
import json
import boto3
import psycopg2
import openai
from minio import Minio
from flask import Flask, request, jsonify, render_template

# Initialize Flask App
app = Flask(__name__, template_folder="/app/templates")

# MinIO Configuration
MINIO_ENDPOINT = "minio-service:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "miniosecret123"
BUCKET_NAME = "review-uploads"

# Database Configuration
DB_HOST = "review-db-service"
DB_NAME = "reviewdb"
DB_USER = "postgres"

# AWS Secrets Manager Configuration
AWS_REGION = "us-east-2"
DB_SECRET_NAME = "review_db_secret"
OPENAI_SECRET_NAME = "Discord_bot"

# Retrieve Secrets from AWS Secrets Manager
def get_secret(secret_name):
    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret
    except Exception as e:
        print(f"❌ Error retrieving secret {secret_name}: {e}")
        return None

# Fetch Database Credentials
db_secrets = get_secret(DB_SECRET_NAME)
DB_PASSWORD = db_secrets.get("POSTGRES_PASSWORD") if db_secrets else "Password123"

# Fetch OpenAI API Key
openai_secrets = get_secret(OPENAI_SECRET_NAME)
OPENAI_API_KEY = openai_secrets.get("OPENAI_API_KEY") if openai_secrets else None

if not OPENAI_API_KEY:
    print("⚠️ OpenAI API key is missing!")

# AI Customer Service Agent Prompt
AI_PROMPT = """
You are a professional customer service agent specializing in mobile products. 
Your responses should be short (1-5 lines) and professional. 
Analyze the review and provide a helpful response, or flag it for customer support if needed.
"""

# AI Review Analysis Function
def analyze_review(review_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": AI_PROMPT},
                {"role": "user", "content": review_text}
            ],
            api_key=OPENAI_API_KEY
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"⚠️ Error in OpenAI API call: {e}")
        return "Error analyzing review."

# Connect to Database
def connect_db():
    try:
        conn = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port="5432")
        print("✅ Database connected successfully", flush=True)
        return conn
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        return None

conn = connect_db()
cur = conn.cursor() if conn else None

# Create Reviews Table if not exists
if cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            user_name TEXT,
            product TEXT,
            review TEXT,
            rating INT,
            ai_response TEXT,
            flagged BOOLEAN DEFAULT FALSE
        );
    """)
    conn.commit()

# MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Flask Routes
@app.route("/")
def index():
    return render_template("review_form.html")

@app.route("/admin")
def admin():
    return render_template("admin_dashboard.html")

# Route to Submit a Review
@app.route("/submit-review", methods=["POST"])
def submit_review():
    if not cur:
        return jsonify({"error": "Database connection failed"}), 500

    data = request.json
    user_name = data.get("user_name")
    product = data.get("product")
    review_text = data.get("review")
    rating = data.get("rating", 5)

    ai_response = analyze_review(review_text)

    cur.execute("""
        INSERT INTO reviews (user_name, product, review, rating, ai_response) 
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
    """, (user_name, product, review_text, rating, ai_response))
    
    conn.commit()
    review_id = cur.fetchone()[0]

    return jsonify({
        "message": "Review submitted successfully",
        "review_id": review_id,
        "ai_response": ai_response
    }), 201

# Route to Fetch Flagged Reviews
@app.route("/flagged-reviews", methods=["GET"])
def get_flagged_reviews():
    if not cur:
        return jsonify({"error": "Database connection failed"}), 500

    cur.execute("SELECT id, user_name, product, review, ai_response FROM reviews WHERE flagged = TRUE;")
    flagged_reviews = cur.fetchall()

    return jsonify([{
        "id": r[0],
        "user_name": r[1],
        "product": r[2],
        "review": r[3],
        "ai_response": r[4]
    } for r in flagged_reviews])

# Process CSV Files from MinIO
def process_csv_files():
    while True:
        try:
            objects = minio_client.list_objects(BUCKET_NAME)
            for obj in objects:
                file_name = obj.object_name
                print(f"📥 Processing file: {file_name}")

                # Download and process CSV
                minio_client.fget_object(BUCKET_NAME, file_name, f"/tmp/{file_name}")
                insert_csv_into_db(f"/tmp/{file_name}")

                # Optionally delete the file after processing
                # minio_client.remove_object(BUCKET_NAME, file_name)

        except Exception as e:
            print(f"⚠️ Error processing files: {e}")

        time.sleep(10)  # Check every 10 seconds

# Run Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
