from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from pymongo import MongoClient
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key'

UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

client = MongoClient("mongodb://localhost:27017/")
db = client['smart_factory']
collection = db['machine_data']


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def train_and_predict(machine_id):
    try:
        cursor = collection.find(
            {'machine_id': machine_id},
            {'_id': 0, 'timestamp': 1, 'temperature': 1}
        ).sort('timestamp', 1).limit(50)

        data = list(cursor)
        if not data or len(data) < 10:
            return None, []

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time_index'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()

        X = df[['time_index']]
        y = df['temperature']

        model = LinearRegression()
        model.fit(X, y)

        future_time = X['time_index'].max() + 300
        predicted_temp = model.predict([[future_time]])[0]

        last_timestamp = df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
        return round(predicted_temp, 2), last_timestamp

    except Exception as e:
        return f"Prediction error: {str(e)}", None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/report')
def report():
    predictions = {}
    machine_ids = collection.distinct('machine_id')

    for mid in machine_ids:
        prediction, last_time = train_and_predict(mid)
        predictions[mid] = {
            "value": f"{prediction} \u00b0C" if isinstance(prediction, (int, float)) else prediction,
            "timestamp": last_time or "N/A"
        }
    return render_template("report.html", predictions=predictions)


@app.route('/download')
def download_report():
    path = os.path.join(app.config['UPLOAD_FOLDER'], 'machine_data.csv')
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    else:
        flash("\u26A0\uFE0F No report available to download.")
        return redirect(url_for('report'))


@app.route('/upload', methods=['POST'])
def upload():
    if 'csv_file' not in request.files:
        flash('No file part found')
        return redirect(url_for('index'))

    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename("machine_data.csv")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            df = pd.read_csv(filepath)
            df.dropna(inplace=True)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            if 'machine_id' in df.columns and 'temperature' in df.columns:
                collection.delete_many({})  # clear previous data
                collection.insert_many(df.to_dict(orient='records'))
                flash(f"\u2705 {len(df)} rows inserted into MongoDB.")
            else:
                flash("\u26A0\uFE0F Required columns (machine_id, temperature, timestamp) missing.")
        except Exception as e:
            flash(f"\u274C Error while processing file: {str(e)}")


    return redirect(url_for('index'))


if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
