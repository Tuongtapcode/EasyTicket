from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from flask_login import UserMixin
from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, DateTime, ForeignKey, DECIMAL, Numeric, Index
)
from sqlalchemy.orm import relationship

from app import db


# ===== Enums (dùng UPPERCASE để khớp với MySQL enum trong ảnh) =====
class UserRole(PyEnum):
    USER = "USER"
    ORGANIZER = "ORGANIZER"
    ADMIN = "ADMIN"


class EventStatus(PyEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class TicketStatus(PyEnum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(PyEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(PyEnum):
    CREDIT_CARD   = "CREDIT_CARD"
    DEBIT_CARD    = "DEBIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    DIGITAL_WALLET= "DIGITAL_WALLET"


# ===== Models =====
class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    phone = Column(String(100), nullable=False, unique=True, index=True)
    avatar = Column(
        String(100),
        nullable=True,
        default="https://cdn.pixabay.com/photo/2023/02/18/11/00/icon-7797704_640.png",
    )
    active = Column(Boolean, default=True)
    user_role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login_at = Column(DateTime, default=datetime.now)

    # relationships
    orders = relationship("Order", back_populates="customer")
    organized_events = relationship("Event", back_populates="organizer")

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Category(db.Model):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(100), nullable=False)
    active = Column(Boolean, default=True)

    # Khớp với Event.category
    events = relationship("Event", back_populates="category")

    def __repr__(self):
        return f"<Category id={self.id} name={self.name!r}>"

    def __str__(self):
        return self.name

class EventType(db.Model):
    __tablename__ = "event_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, default=True)

    # Khớp với Event.event_type
    events = relationship("Event", back_populates="event_type")

    def __repr__(self):
        return f"<EventType id={self.id} name={self.name!r}>"

    def __str__(self):
        return self.name

class Event(db.Model):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)

    organizer_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(200), nullable=False)

    status = Column(Enum(EventStatus), default=EventStatus.DRAFT, nullable=False, index=True)

    event_type_id = Column(Integer, ForeignKey("event_type.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)

    # Event detail
    start_datetime = Column(DateTime, default=datetime.now, nullable=False)
    end_datetime = Column(DateTime, default=datetime.now, nullable=False)
    address = Column(String(200), nullable=False)
    banner_image = Column(String(200))

    # Time
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    published_at = Column(DateTime, default=datetime.now, nullable=False)

    # relationships
    organizer = relationship("User", back_populates="organized_events")
    event_type = relationship("EventType", back_populates="events")
    category = relationship("Category", back_populates="events")

    ticket_types = relationship("TicketType", back_populates="event")
    tickets = relationship("Ticket", back_populates="event")

    def __repr__(self):
        return f"<Event id={self.id} name={self.name!r}>"


class TicketType(db.Model):
    __tablename__ = "ticket_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    price = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # relationships
    event = relationship("Event", back_populates="ticket_types")
    order_details = relationship("OrderDetail", back_populates="ticket_type")
    tickets = relationship("Ticket", back_populates="ticket_type")

    def __repr__(self):
        return f"<TicketType id={self.id} name={self.name!r} event_id={self.event_id}>"


class Ticket(db.Model):
    __tablename__ = "ticket"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.ACTIVE, nullable=False, index=True)

    order_id = Column(Integer, ForeignKey("order.id"))
    ticket_type_id = Column(Integer, ForeignKey("ticket_type.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)

    # khi vé chưa sử dụng, nên để NULL
    use_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # relationships
    order = relationship("Order", back_populates="tickets")
    ticket_type = relationship("TicketType", back_populates="tickets")
    event = relationship("Event", back_populates="tickets")

    def __repr__(self):
        return f"<Ticket id={self.id} code={self.ticket_code!r}>"


class Order(db.Model):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    total_amount = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    extra_fee = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    discount = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    # relationships
    customer = relationship("User", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")
    order_details = relationship("OrderDetail", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order")

    def __repr__(self):
        return f"<Order id={self.id} code={self.order_code!r}>"


class OrderDetail(db.Model):
    __tablename__ = "order_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)
    ticket_type_id = Column(Integer, ForeignKey("ticket_type.id"), nullable=False)

    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)  # giá tại thời điểm mua

    # relationships
    order = relationship("Order", back_populates="order_details")
    ticket_type = relationship("TicketType", back_populates="order_details")

    # LƯU Ý: nếu muốn liên kết Ticket <-> OrderDetail, cần thêm FK ở Ticket.
    # Ở bản này bỏ để tránh back_populates tới thuộc tính không tồn tại.

    def __repr__(self):
        return f"<OrderDetail id={self.id} order_id={self.order_id} ticket_type_id={self.ticket_type_id}>"


class Payment(db.Model):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False)

    amount = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    transaction_id = Column(String(100), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    order = relationship("Order", back_populates="payments")

    def __repr__(self):
        return f"<Payment id={self.id} order_id={self.order_id} status={self.status.value}>"
# --- trong class Ticket (giữ nguyên các field khác) ---
class Ticket(db.Model):
    __tablename__ = "ticket"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_code = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.ACTIVE, nullable=False, index=True)

    order_id = Column(Integer, ForeignKey("order.id"))
    ticket_type_id = Column(Integer, ForeignKey("ticket_type.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("event.id"), nullable=False)

    # NEW: chuỗi QR đã ký + thời điểm phát hành
    qr_data = Column(String(256), unique=True, nullable=True, index=True)
    issued_at = Column(DateTime, nullable=True)

    # khi vé chưa sử dụng, để NULL
    use_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    order = relationship("Order", back_populates="tickets")
    ticket_type = relationship("TicketType", back_populates="tickets")
    event = relationship("Event", back_populates="tickets")
