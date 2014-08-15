Code Golf
=========

Prerequisites
-------------

- Python 2
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
    docker pull dbrgn/asm-codegolf
    python -c 'from codegolf.server import db; db.create_all()'

Start
-----

::

    python runserver.py
