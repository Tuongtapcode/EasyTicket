from app.models import db, Category


def get_all_categories():
    return Category.query.all()