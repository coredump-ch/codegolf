Code Golf
=========

Prerequisites
-------------

- Python 3
- Docker

Setup
-----

Install Prerequisites on Ubuntu
++++++++++++++++++++++++++++++

::

    apt-get install docker.io
    ln -sf /usr/bin/docker.io /usr/local/bin/docker

Setup Code Golf Server
++++++++++++++++++++++

::

    pip install -r requirements.txt
    docker pull quay.io/coredump/codegolf-asm-compass
    python -c 'from codegolf.server import db; db.create_all()'

Start
-----

::

    python runserver.py
