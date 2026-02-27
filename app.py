from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from io import BytesIO
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from urllib.parse import unquote

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.secret_key = 'your-secret-key-change-this'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global storage for session data (in production, use Redis or database)
sessions = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded', 'success': False}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected', 'success': False}), 400

    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Please upload an Excel (.xlsx) file', 'success': False}), 400

    try:
        # Read Excel file
        df = pd.read_excel(file, engine='openpyxl')
        df.columns = [str(c).strip() for c in df.columns]

        # Check if required column exists
        if 'Data entry filter owner' not in df.columns:
            return jsonify({
                'error': 'Column "Data entry filter owner" not found in the file',
                'success': False
            }), 400

        # Clean the data entry filter owner column
        df['Data entry filter owner'] = df['Data entry filter owner'].fillna('(Empty)').astype(str)

        # Group by Data entry filter owner
        grouped = df.groupby('Data entry filter owner').size().reset_index(name='count')
        grouped = grouped.sort_values('count', ascending=False)

        # Store data in session
        session_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        sessions[session_id] = {
            'df': df,
            'decisions': {idx: 'keep' for idx in df.index}
        }

        # Prepare response - convert to native Python types
        owners = []
        for _, row in grouped.iterrows():
            owners.append({
                'Data entry filter owner': str(row['Data entry filter owner']),
                'count': int(row['count'])
            })

        return jsonify({
            'success': True,
            'session_id': session_id,
            'owners': owners,
            'total_rows': int(len(df))
        })

    except Exception as e:
        return jsonify({
            'error': f'Error processing file: {str(e)}',
            'success': False
        }), 500


@app.route('/get_all_rows/<session_id>')
def get_all_rows(session_id):
    try:
        if session_id not in sessions:
            return jsonify({'error': 'Session expired', 'success': False}), 404

        df = sessions[session_id]['df']
        decisions = sessions[session_id]['decisions']

        # Add decisions
        rows = []
        for idx, row in df.iterrows():
            row_data = {}
            for col, val in row.items():
                # Convert numpy/pandas types to Python types
                if pd.isna(val):
                    row_data[col] = None
                elif isinstance(val, pd.Timestamp):
                    row_data[col] = str(val)
                elif hasattr(val, 'item'):  # numpy types
                    row_data[col] = val.item()
                else:
                    row_data[col] = str(val) if not isinstance(val, (int, float, bool, str, type(None))) else val

            row_data['_index'] = int(idx)
            row_data['_decision'] = decisions.get(idx, 'keep')
            rows.append(row_data)

        return jsonify({
            'success': True,
            'rows': rows,
            'columns': list(df.columns)
        })

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/get_rows/<session_id>/<path:owner>')
def get_rows(session_id, owner):
    try:
        if session_id not in sessions:
            return jsonify({'error': 'Session expired', 'success': False}), 404

        df = sessions[session_id]['df']
        decisions = sessions[session_id]['decisions']

        # Decode the owner name from URL
        from urllib.parse import unquote
        owner = unquote(owner)

        # Filter by owner - convert both to string for safe comparison
        filtered_df = df[df['Data entry filter owner'].astype(str) == str(owner)].copy()

        if len(filtered_df) == 0:
            return jsonify({
                'success': True,
                'rows': [],
                'columns': list(df.columns),
                'message': f'No rows found for owner: {owner}'
            })

        # Add decisions
        rows = []
        for idx, row in filtered_df.iterrows():
            row_data = {}
            for col, val in row.items():
                # Convert numpy/pandas types to Python types
                if pd.isna(val):
                    row_data[col] = None
                elif isinstance(val, pd.Timestamp):
                    row_data[col] = str(val)
                elif hasattr(val, 'item'):  # numpy types
                    row_data[col] = val.item()
                else:
                    row_data[col] = str(val) if not isinstance(val, (int, float, bool, str, type(None))) else val

            row_data['_index'] = int(idx)
            row_data['_decision'] = decisions.get(idx, 'keep')
            rows.append(row_data)

        return jsonify({
            'success': True,
            'rows': rows,
            'columns': list(filtered_df.columns)
        })

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/update_decision', methods=['POST'])
def update_decision():
    data = request.json
    session_id = data.get('session_id')
    row_index = data.get('row_index')
    decision = data.get('decision')

    if session_id not in sessions:
        return jsonify({'error': 'Session expired'}), 404

    sessions[session_id]['decisions'][row_index] = decision

    return jsonify({'success': True})


@app.route('/bulk_update', methods=['POST'])
def bulk_update():
    data = request.json
    session_id = data.get('session_id')
    indices = data.get('indices', [])
    decision = data.get('decision')

    if session_id not in sessions:
        return jsonify({'error': 'Session expired'}), 404

    for idx in indices:
        sessions[session_id]['decisions'][idx] = decision

    return jsonify({'success': True, 'updated': len(indices)})


@app.route('/export/<session_id>', methods=['GET', 'POST'])
def export_data(session_id):
    if session_id not in sessions:
        return jsonify({'error': 'Session expired'}), 404

    df = sessions[session_id]['df'].copy()
    decisions = sessions[session_id]['decisions']

    # Add decision column
    df['Decision'] = df.index.map(lambda x: decisions.get(x, 'keep'))

    # If POST request with indices, filter the data
    if request.method == 'POST':
        indices_json = request.form.get('indices')
        if indices_json:
            import json
            indices = json.loads(indices_json)
            df = df[df.index.isin(indices)]

    # Create Excel file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Access Review')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'access_review_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


@app.route('/stats/<session_id>')
def get_stats(session_id):
    if session_id not in sessions:
        return jsonify({'error': 'Session expired'}), 404

    decisions = sessions[session_id]['decisions']
    keep_count = sum(1 for d in decisions.values() if d == 'keep')
    remove_count = sum(1 for d in decisions.values() if d == 'remove')

    return jsonify({
        'success': True,
        'total': len(decisions),
        'keep': keep_count,
        'remove': remove_count
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)