
from flask import Blueprint, render_template, url_for, flash, redirect
from app import dao
from app.forms import RegistrationForm

#Blue print dùng để nhóm các routes lại cho gọn hơn
auth = Blueprint('auth', __name__, template_folder='templates')

@auth.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Gọi hàm từ DAO để thêm người dùng
            dao.add_user(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                username=form.username.data,
                email=form.email.data,
                phone=form.phone.data,
                password=form.password.data
            )
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('register.html', title='Register', form=form)



