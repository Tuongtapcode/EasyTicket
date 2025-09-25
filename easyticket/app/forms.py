from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField, TextAreaField,
    SelectField, IntegerField, DecimalField, DateTimeField,
)
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange

# Xử lý tương thích DateTimeLocalField
try:
    # WTForms 3.x
    from wtforms.fields import DateTimeLocalField
except ImportError:
    # Fallback: sử dụng DateTimeField thông thường
    DateTimeLocalField = DateTimeField

from app.models import User, Category, EventType  # tránh import từ app.__init__

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('That email is taken. Please choose a different one.')

    def validate_phone(self, phone):
        if User.query.filter_by(phone=phone.data).first():
            raise ValidationError('That phone number is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class EventForm(FlaskForm):
    name = StringField("Tên sự kiện", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Mô tả", validators=[DataRequired(), Length(max=200)])
    event_type_id = SelectField("Loại sự kiện", coerce=int, validators=[DataRequired()])
    category_id = SelectField("Danh mục", coerce=int, validators=[DataRequired()])
    start_datetime = DateTimeLocalField("Thời gian bắt đầu", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_datetime = DateTimeLocalField("Thời gian kết thúc", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    address = StringField("Địa điểm", validators=[DataRequired(), Length(max=200)])
    banner_image = FileField("Ảnh banner (URL)", validators=[
        FileAllowed(["jpg", "jpeg", "png", "gif"], "Chỉ hỗ trợ ảnh JPG, PNG, GIF.")
    ])
    submit = SubmitField("Tạo sự kiện")

    def set_choices(self):
        self.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(active=True).all()]
        self.event_type_id.choices = [(et.id, et.name) for et in EventType.query.filter_by(active=True).all()]

class TicketTypeForm(FlaskForm):
    name = StringField("Tên loại vé", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Mô tả", validators=[DataRequired(), Length(max=200)])
    quantity = IntegerField("Số lượng", validators=[DataRequired(), NumberRange(min=1, message="Số lượng phải lớn hơn 0")])
    price = DecimalField("Giá vé", places=2, validators=[DataRequired(), NumberRange(min=0, message="Giá vé không được âm")])
    active = SelectField("Trạng thái", coerce=int, choices=[(1, "Kích hoạt"), (0, "Không kích hoạt")])
    submit = SubmitField("Lưu loại vé")

    def set_active_value(self, ticket_type=None):
        if ticket_type:
            self.active.data = 1 if ticket_type.active else 0
