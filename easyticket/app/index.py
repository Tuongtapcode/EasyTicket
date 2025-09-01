from flask_login import current_user, login_required
from app import app
from flask import render_template, abort

from app.models import UserRole

@app.route('/dashboard')
@login_required
def dashboard():
    print("current_user:", current_user)
    print("role:", current_user.user_role, type(current_user.user_role))
    if current_user.user_role != UserRole.ORGANIZER:
        abort(403)
    return render_template("organizer/dashboard.html")

if __name__ == '__main__':
    app.run(debug=True)