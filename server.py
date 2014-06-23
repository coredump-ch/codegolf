# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

from flask import Flask, render_template


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/challenges/asm-compass/')
def asm_compass():
    return render_template('challenges/compass.html')


if __name__ == "__main__":
    app.debug = True
    app.run()
