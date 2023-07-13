import math
import time
import sys

from flask import Flask


app = Flask(__name__)

@app.route('/')
def calculate_pi():
    n = 2500000000
    pi = 0.0
    for i in range(n):
        sign = (-1) ** i
        pi += sign * (1 / (2*i + 1))
    return 4 * pi

if __name__ == '__main__':
    app.run(debug = True, host = '0.0.0.0', port = 7000)