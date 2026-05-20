from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from flask import Flask, render_template, Response, request
from flask_cors import CORS
import threading
import json
import queue
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return "hello"


if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'True').lower() in ('1', 'true', 'yes')
    
    # Disable Flask reloader to prevent multiple MQTT client instances
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)