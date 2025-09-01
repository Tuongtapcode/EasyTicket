
from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import logout_user,current_user, login_user
from app.dao.user_dao import *
from app.forms import RegistrationForm, LoginForm
from werkzeug.security import  check_password_hash

#Blue print dùng để nhóm các routes lại cho gọn hơn
auth = Blueprint('auth', __name__, template_folder='templates')

@auth.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Gọi hàm từ DAO để thêm người dùng
            add_user(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                username=form.username.data,
                email=form.email.data,
                phone=form.phone.data,
                password=form.password.data
            )
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('auth/register.html', title='Register', form=form)


@auth.route("/login", methods=['GET', 'POST'])
def login():
    #Nếu đã đăng nhập, chuyển hướng về trang chủ
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user =get_user_by_username(form.username.data) #Trong dao có hàm này để check user
        if user and check_password_hash(user.password, form.password.data):
            # Mật khẩu đúng, đăng nhập người dùng
            login_user(user, remember=form.remember.data) #remeber để lưu lại người dùng khi bấm nhớ
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('auth/login.html', title='Log In', form=form)


@auth.route("/logout")
def logout():
    logout_user()#xoa user khoi flask login
    return redirect(url_for('main.index'))
