from app import my_app, db
from app.models import User, Post


@my_app.shell_context_processor
def make_shell_context():
    return {'my_app': my_app, 'db': db, 'User': User, 'Post': Post}
