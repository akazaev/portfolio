from flask import Blueprint, templating


pages = Blueprint('pages', __name__, url_prefix='/')


@pages.route('/')
def index():
    return templating.render_template('index.html')
