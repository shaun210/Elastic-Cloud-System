from flask import Flask
import sys
import time
app = Flask(__name__)

@app.route('/')
def light():
    if len(sys.argv) < 2:
        return 'Error: missing argument\n'
    print("app.py working")
    time.sleep(5)  # Pause for 5 seconds
    return 'Hello from:   + \n'

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 5000)
