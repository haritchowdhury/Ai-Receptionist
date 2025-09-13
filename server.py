from flask import Flask, render_template, jsonify
from membership_operations import MembershipOperations
import json
from datetime import datetime

app = Flask(__name__)
db = MembershipOperations()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/member-sessions')
def get_member_sessions():
    try:
        sessions = db.get_all_member_sessions()
        print(sessions)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)