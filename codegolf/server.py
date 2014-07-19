# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

import os
from threading import Timer
from datetime import datetime

try:
    from shlex import quote
except ImportError:
    from pipes import quote

import docker
from flask import Flask, render_template
from flask.ext.sqlalchemy import SQLAlchemy

from .forms import CompassSubmitForm


DOCKER_IMAGE = 'dbrgn/asm-codegolf'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../highscore.db'
db = SQLAlchemy(app)


class HighscoreEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.String(127), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('challenge', 'name'),
    )

    def __init__(self, challenge, name, size):
        self.challenge = challenge
        self.name = name
        self.size = size

    def __repr__(self):
        return '<HighscoreEntry %s/%s [%s]>' % (self.challenge, self.name, self.size)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/challenges/asm-compass/', methods=('GET',))
def asm_compass():
    context = {
        'solution_url': '/challenges/asm-compass/submit/',
        'highscores': HighscoreEntry.query.order_by(
            HighscoreEntry.size.asc(), HighscoreEntry.updated_on.asc()),
    }
    return render_template('challenges/compass_info.html', **context)


@app.route('/challenges/asm-compass/submit/', methods=('GET', 'POST'))
def asm_compass_submit():
    form = CompassSubmitForm()
    if form.validate_on_submit():
        if not os.path.exists('code'):
            os.makedirs('code')
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        safename = ''.join(c for c in form.name.data if c.isalpha())
        filepath = os.path.abspath('code/%s-%s.s' % (safename, timestamp))
        form.source.data.save(filepath)
        try:
            size = asm_compass_verify(filepath)
            success, msg = asm_compass_add_highscore(form.name.data, size)
            output = ''
        except RuntimeError as e:
            size = 0
            success = False
            msg = unicode(e)
            output = e.output
        data = {
            'name': form.name.data,
            'size': size,
            'date': datetime.now(),
            'source': filepath,
            'success': success,
            'msg': msg,
            'output': output,
        }
    else:
        data = {}
    data['highscores'] = HighscoreEntry.query.order_by(
        HighscoreEntry.size.asc(), HighscoreEntry.updated_on.asc())
    data['info_url'] = '/challenges/asm-compass/'
    data['solution_url'] = '/challenges/asm-compass/submit/'
    return render_template('challenges/compass_submit.html', form=form, **data)


def stop_long_running(args):
    args[0].kill()
    raise RuntimeError('the code runs too long')


def asm_compass_verify(filepath):
    """
    Verify an entry for the asm compass challenge.
    """
    dirname, filename = os.path.split(filepath)
    client = docker.Client()
    cid = client.create_container(DOCKER_IMAGE,
                'bash -c "cp /code/%s main.s && make -s && python test.py --short"' % quote(filename),
                user='compass',
                working_dir='/home/compass/codegolf',
                volumes=['/code'],
                network_disabled=True,
                mem_limit=20,
    )
    client.start(cid, binds={dirname: '/code'})

    # Start timer to ensure code does not run forever, timeout 10 seconds
    timer = Timer(10.0, stop_long_running, args=[client])
    timer.start()

    code = client.wait(cid)
    timer.cancel()
    output = client.logs(cid, stdout=True)
    if code != 0:
        ex = RuntimeError('building the sourcecode failed')
        ex.output = output
        raise ex
    client.remove_container(cid)
    return int(output)


def asm_compass_add_highscore(name, size):
    """
    Add or update a highscore entry for the asm compass challenge.

    Returns:
        Tuple containing the success value (True, None, False) and a message.

    """
    entry = HighscoreEntry.query.filter_by(name=name, challenge='asm-compass').first()
    if entry:
        app.logger.info('[asm-compass] Highscore entry found for %s.', name)
        if entry.size > size:
            entry.size = size
            db.session.commit()
            return True, 'updated score from %d to %d.' % (entry.size, size)
        else:
            return None, 'binary size (%d) is not smaller than the currently stored value (%d).' % \
                         (size, entry.size)
    else:
        app.logger.info('[asm-compass] No highscore entry found for %s.', name)
        new_entry = HighscoreEntry('asm-compass', name, size)
        db.session.add(new_entry)
        db.session.commit()
        return True, 'added your entry to the highscore list.'
