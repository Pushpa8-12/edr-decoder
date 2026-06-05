from flask import Flask, request, send_file, jsonify
import tempfile
import os
from datetime import datetime

# ✅ Import your existing decoder logic
from SignalEDRExecutable_1_1_3 import process_txt_file

app = Flask(__name__)

@app.route('/decode-edr', methods=['POST'])
def decode_edr():
    try:
        # ✅ Check if files are present
        if 'txt_file' not in request.files or 'excel_file' not in request.files:
            return jsonify({"error": "Both txt_file and excel_file are required"}), 400

        txt_file = request.files['txt_file']
        excel_file = request.files['excel_file']

        # ✅ Create temp directory
        temp_dir = tempfile.mkdtemp()

        txt_path = os.path.join(temp_dir, txt_file.filename)
        excel_path = os.path.join(temp_dir, excel_file.filename)

        # ✅ Save uploaded files
        txt_file.save(txt_path)
        excel_file.save(excel_path)

        # ✅ Create output filename based on input txt file
        input_filename = os.path.splitext(txt_file.filename)[0]
        output_file = f"{input_filename}.xlsx"
        output_path = os.path.join(temp_dir, output_file)

        print(f"Processing file: {txt_file.filename}")
        print("Decoding started...")

        # ✅ Call your existing logic
        process_txt_file(txt_path, excel_path, output_path)

        print("Decoding completed ✅")

        # ✅ Return Excel file
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500


# ✅ Run server
import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
