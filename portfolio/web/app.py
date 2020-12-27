from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY='123456'
    )

    from portfolio.web.routes import tables, forms, pages
    app.register_blueprint(tables.tables)
    app.register_blueprint(forms.forms)
    app.register_blueprint(pages.pages)
    return app
