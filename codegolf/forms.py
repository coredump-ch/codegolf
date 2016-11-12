from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField
from wtforms.validators import InputRequired


class CompassSubmitForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired()],
        description='Your name as it should appear in the high score list.')
    source = FileField('Source', validators=[
        FileRequired(),
        FileAllowed(['s'], 'Assembly source code (.s) only!'),
    ], description='The NASM assembly source file, ending with <code>.s</code>.')
