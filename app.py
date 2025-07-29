from flask import Flask, jsonify
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

user_data_store = {}

def read_collapse_file(collapse_type):
    """Read the collapse reading file for a given type"""
    file_path = f"final/{collapse_type}.txt"
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return None

def parse_collapse_sections(content):
    """Parse the collapse content into sections"""
    if not content:
        return {}
    
    sections = {}
    current_section = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section header (all caps, no punctuation)
        if line.isupper() and len(line) > 3 and not any(char in line for char in '.,!?'):
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line.lower().replace(' ', '_')
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections



@app.route('/result/<user_id>', methods=['GET'])
def get_result(user_id):
    if user_id in user_data_store:
        return jsonify({"user_id": user_id, "data": user_data_store[user_id]})
    else:
        return jsonify({ "error": "User ID not found" }), 404



if __name__ == '__main__':
    app.run(debug=True, port=5000)
