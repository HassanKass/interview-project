import os
import pandas as pd
import datetime
import threading
import time
import boto3
from flask import Flask, request, jsonify, render_template
from minio import Minio
from minio.error import S3Error
import psycopg2
import json 

# Initialize Flask App
app = Flask(__name__, template_folder="/app/templates")

AWS_REGION = "us-east-2"
secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
#Retrieve Credentials
def get_db_password():
    secret_name = "review_db_secret"
    region_name = "us-east-2" 

    try:
        client = boto3.client("secretsmanager", region_name=region_name)
        response = client.get_secret_value(SecretId=secret_name)
        
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            return secret.get("POSTGRES_PASSWORD")
        else:
            print("⚠️ No secret string found in AWS Secrets Manager response.")
            return None
    except Exception as e:
        print(f"⚠️ Error retrieving database secret: {e}")
        return None
    
def get_minio_credentials():
    secret_name = "minio_secret"
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            return (
                secret.get("MINIO_ACCESS_KEY"),
                secret.get("MINIO_SECRET_KEY"),
                secret.get("MINIO_ENDPOINT"),
                secret.get("BUCKET_NAME")
            )
    except Exception as e:
        print(f"⚠️ Error retrieving MinIO secret: {e}")
    return None, None, None, None
MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_ENDPOINT, BUCKET_NAME = get_minio_credentials()
# AWS CloudWatch Configuration
CLOUDWATCH_NAMESPACE = "CSVProcessing"
cloudwatch_client = boto3.client("cloudwatch", region_name="us-east-2")

# Database Configuration
DB_HOST = "review-db-service"
DB_NAME = "reviewdb"
DB_USER = "postgres"
DB_PASSWORD = get_db_password() 

# Initialize MinIO Client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure MinIO Bucket Exists
try:
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        print(f"✅ MinIO Bucket Created: {BUCKET_NAME}")
    else:
        print(f"✅ MinIO Bucket Exists: {BUCKET_NAME}")
except S3Error as e:
    print(f"⚠️ MinIO Error: {e}")

# Connect to Database
def connect_db():
    """Establishes a connection to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port="5432"
        )
        print("✅ Database connected successfully")
        return conn
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        return None

conn = connect_db()
cur = conn.cursor() if conn else None

# Flask Routes
@app.route("/")
def index():
    """Renders the main CSV upload form and data table"""
    return render_template("review_form.html")

@app.route("/admin")
def admin():
    """Renders the Admin Panel for CSV Upload"""
    return render_template("admin_dashboard.html")

@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    """Handles CSV uploads, stores them in MinIO, and auto-syncs to PostgreSQL"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = f"/tmp/{file.filename}"
    file.save(file_path)  

    print(f" Checking local file: {file_path}")
    if not os.path.exists(file_path):
        print(f"⚠️ Local file {file_path} does not exist.")
        return jsonify({"error": "File not found after saving locally"}), 500

    try:
        minio_client.fput_object(BUCKET_NAME, file.filename, file_path)
        print(f"✅ File uploaded to MinIO: {file.filename}")

        # Auto-sync CSV data to PostgreSQL immediately after upload
        sync_csv_to_db(file.filename)

        return jsonify({"message": "File uploaded and synced successfully"}), 201
    except S3Error as e:
        print(f"⚠️ MinIO Upload Error: {e}")
        return jsonify({"error": "An error occurred while uploading the file"}), 500
    
def log_to_cloudwatch(metric_name, value):
    """Sends custom metrics to AWS CloudWatch"""
    try:
        cloudwatch_client.put_metric_data(
            Namespace="CSVProcessing",
            MetricData=[{"MetricName": metric_name, "Value": value, "Unit": "Count"}]
        )
        print(f"✅ CloudWatch Metric Sent: {metric_name} = {value}")
    except Exception as e:
        print(f"⚠️ CloudWatch Error: {e}")    

def sync_csv_to_db(file_name):
    """Fetches a CSV from MinIO, processes it, and stores it in PostgreSQL without duplicates"""
    try:
        file_path = f"/tmp/{file_name}"
        minio_client.fget_object(BUCKET_NAME, file_name, file_path)
        df = pd.read_csv(file_path)

        #  If CSV contains 'ts' and 'value', store it in 'time_series_data' table
        if "ts" in df.columns and "value" in df.columns:
            table_name = "time_series_data"
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    ts TIMESTAMP UNIQUE,
                    value FLOAT,
                    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            count = 0
            for _, row in df.iterrows():
                cur.execute(f"""
                    INSERT INTO {table_name} (ts, value, upload_timestamp)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ts) DO NOTHING;
                """, (row['ts'], row['value'], datetime.datetime.now()))
                count += 1
            conn.commit()

        else:
            table_name = "uploaded_data"
            cur.execute(f"SELECT company, product FROM {table_name};")
            existing_rows = set(cur.fetchall())
            count = 0
            for _, row in df.iterrows():
                if (row["company"], row["product"]) not in existing_rows:
                    cur.execute(f"INSERT INTO {table_name} (company, product, upload_timestamp) VALUES (%s, %s, %s);", (row['company'], row['product'], datetime.datetime.now()))
                    count += 1
            conn.commit()

            log_to_cloudwatch("RowsInserted", count)
            log_to_cloudwatch("FilesProcessed", 1)

            print(f"✅ {file_name} processed and stored in {table_name}, inserting {count} rows.")
    except Exception as e:
        print(f"⚠️ Error syncing CSV to database: {e}")
        conn.rollback()
#get data ti the form.html        
@app.route("/get-data", methods=["GET"])
def get_data():
    """Fetches all uploaded CSV data from the database"""
    try:
        table_name = "uploaded_data"
        print(f" Fetching data from table: {table_name}")

        cur.execute(f"SELECT * FROM {table_name};")
        rows = cur.fetchall()

        if not rows:
            return jsonify({"error": "No data found"}), 404

        # Fetch column names dynamically
        columns = [desc[0] for desc in cur.description]
        data = [dict(zip(columns, row)) for row in rows]

        print(f"✅ Data Retrieved: {data}")
        return jsonify(data)

    except Exception as e:
        print(f"⚠️ Error fetching data: {e}")
        return jsonify({"error": "Failed to fetch data"}), 500
# Background process to monitor MinIO for new files
def monitor_minio():
    print("🔄 Starting MinIO file watcher...")
    processed_files = set()
    while True:
        try:
            objects = list(minio_client.list_objects(BUCKET_NAME))
            for obj in objects:
                file_name = obj.object_name
                if file_name not in processed_files:
                    print(f" New file detected: {file_name}. Processing...")
                    sync_csv_to_db(file_name)
                    processed_files.add(file_name)
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Error monitoring MinIO: {e}")

# Start MinIO monitoring as a background thread
threading.Thread(target=monitor_minio, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
