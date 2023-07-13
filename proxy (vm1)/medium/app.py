import math
import time
import sys
from flask import Flask


app = Flask(__name__)

@app.route('/')
def calculate_pi():
    # if len(sys.argv) < 2:
    #     return 'Error: missing argument\n'
    n = 500000000
    pi = 0.0
    for i in range(n):
        sign = (-1) ** i
        pi += sign * (1 / (2*i + 1))
    answer = 4 * pi
    return "success in medium server: " + str(answer)

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 6000)
