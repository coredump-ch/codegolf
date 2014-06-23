# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

import os
import time
from datetime import datetime

import docker
from flask import Flask, render_template
from werkzeug import secure_filename

from .forms import CompassSubmitForm


DOCKER_IMAGE = 'dbrgn/codegolf:v1'

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/challenges/asm-compass/', methods=('GET',))
def asm_compass():
    solution_url = '/challenges/asm-compass/submit/'
    return render_template('challenges/compass.html', solution_url=solution_url)


@app.route('/challenges/asm-compass/submit/', methods=('GET', 'POST'))
def asm_compass_submit():
    form = CompassSubmitForm()
    if form.validate_on_submit():
        if not os.path.exists('code'):
            os.makedirs('code')
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filepath = os.path.abspath('code/%s.s' % timestamp)
        form.source.data.save(filepath)
        size = asm_compass_verify(filepath)
        data = {
            'name': form.name.data,
            'size': size,
            'date': datetime.now(),
            'source': filepath,
        }
    else:
        data = {}
    return render_template('challenges/compass_submit.html', form=form, **data)


def asm_compass_verify(filepath):
    dirname, filename = os.path.split(filepath)
    client = docker.Client()
    cid = client.create_container(DOCKER_IMAGE,
            'bash -c "cp /code/%s main.s && make -s && python test.py --short"' % filename,
            user='compass',
            working_dir='/home/compass/codegolf',
            volumes=['/code'])
    client.start(cid, binds={dirname: '/code'})
    code = client.wait(cid)
    if code != 0:
        raise RuntimeError('Building failed.')
    output = client.logs(cid, stdout=True)
    client.remove_container(cid)
    return int(output)
