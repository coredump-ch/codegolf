# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

from flask import Flask, render_template


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/challenges/asm-compass/')
def asm_compass():
    solution_url = '/challenges/asm-compass/submit/'
    return render_template('challenges/compass.html', solution_url=solution_url)


if __name__ == "__main__":
    app.debug = True
    app.run()
