Code Golf
=========

Prerequisites
-------------

- Python 2
- Docker

Setup
-----

::

    pip install -r requirements.txt
    docker pull dbrgn/asm-codegolf
    python -c 'from codegolf.server import db; db.create_all()'

Start
-----

::

    python runserver.py
