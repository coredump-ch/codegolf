import os
import logging
import threading
import tarfile
from datetime import datetime
from io import BytesIO

import docker
from slugify import slugify
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from .forms import CompassSubmitForm


DOCKER_IMAGE = 'quay.io/coredump/codegolf-asm-compass'
DOCKER_TIMEOUT = 10.0

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../highscore.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY')
db = SQLAlchemy(app)

if not app.debug:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    app.logger.addHandler(stream_handler)


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
        # Create code directory
        if not os.path.exists('code'):
            os.makedirs('code')

        # Create a temporary directory for each submission
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        tmpdir = 'code/%s-%s' % (timestamp, slugify(form.name.data))
        os.makedirs(tmpdir)

        # Save submission into that directory
        filepath = os.path.abspath('%s/submission.s' % tmpdir)
        form.source.data.save(filepath)

        try:
            size = asm_compass_verify(filepath)
            success, msg = asm_compass_add_highscore(form.name.data, size)
            output = ''
        except RuntimeError as e:
            size = 0
            success = False
            msg = str(e)
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


def stop_long_running(client, cid, timed_out):
    timed_out.set()
    client.kill(cid)


def create_code_tar(filepath):
    """
    Create a tar file containing the ASM code as `main.s`.

    This is necessary because the Docker API deprecated copying of single files
    into a container.

    See https://github.com/docker/docker-py/issues/1027

    """
    tarstream = BytesIO()
    tar = tarfile.TarFile(fileobj=tarstream, mode='w')
    tar.add(filepath, arcname='main.s')
    tar.close()
    tarstream.seek(0)
    return tarstream


def asm_compass_verify(filepath):
    """
    Verify an entry for the asm compass challenge.
    """
    dirname, filename = os.path.split(filepath)
    client = docker.Client()

    # Pull latest image
    client.pull(DOCKER_IMAGE)

    # Create container
    cid = client.create_container(
        DOCKER_IMAGE,
        'sh -c "make -s && python3 test.py --short"',
        host_config=client.create_host_config(
            network_mode='none',
            mem_limit=1024 * 1024 * 32,  # 32 MB
            memswap_limit=-1,  # No swap
        ),
        user='codegolf',
        working_dir='/home/codegolf',
    )

    # Copy asm file into container
    tarstream = create_code_tar(filepath)
    client.put_archive(container=cid, path='/home/codegolf', data=tarstream)

    # Start container
    client.start(cid)

    # Start timer to ensure code does not run forever, timeout 10 seconds
    timed_out = threading.Event()
    timer = threading.Timer(DOCKER_TIMEOUT, stop_long_running, args=[client, cid, timed_out])
    timer.start()

    # Wait for container to stop
    code = client.wait(cid)
    timer.cancel()

    # If timeout happened, show error message
    if timed_out.is_set():
        ex = RuntimeError('the code runs for too long')
        ex.output = 'Timeout: Code took longer than %ds to execute!' % DOCKER_TIMEOUT
        raise ex

    # Otherwise, get output of test script
    output = client.logs(cid, stdout=True)
    if code != 0:
        ex = RuntimeError('building the sourcecode failed')
        ex.output = output.decode('utf8').strip()
        raise ex

    # Delete container
    client.remove_container(cid)

    # Return number of bytes
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
            old_size = entry.size
            entry.size = size
            db.session.commit()
            return True, 'updated score from %d to %d.' % (old_size, size)
        else:
            return None, 'binary size (%d) is not smaller than the currently stored value (%d).' % \
                         (size, entry.size)
    else:
        app.logger.info('[asm-compass] No highscore entry found for %s.', name)
        new_entry = HighscoreEntry('asm-compass', name, size)
        db.session.add(new_entry)
        db.session.commit()
        return True, 'added your entry to the highscore list.'
