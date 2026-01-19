from flask import Flask, jsonify
import os
import datetime

app = Flask(__name__)
TEMP_FILE = "temperature.txt"

@app.route('/temperature', methods=['GET'])
def get_temperature():
    if not os.path.exists(TEMP_FILE):
        return jsonify({"error": "Temperature data not available yet"}), 503
    
    try:
        with open(TEMP_FILE, "r") as f:
            content = f.read().strip()
            # Simple validation to ensure it's a number
            temperature = float(content)
            
        # Get file modification time as proxy for reading time
        mod_time = os.path.getmtime(TEMP_FILE)
        timestamp = datetime.datetime.fromtimestamp(mod_time).isoformat()
        
        return jsonify({
            "temperature": temperature,
            "unit": "Celsius",
            "last_read": timestamp
        })
    except ValueError:
        return jsonify({"error": "Invalid data in temperature file"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
