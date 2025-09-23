from decimal import Decimal
from app.models import db, Payment, PaymentStatus, PaymentMethod


def create_payment(order_id: int, amount: int, method: PaymentMethod = PaymentMethod.DIGITAL_WALLET) -> Payment:
    pay = Payment(
        order_id=order_id,
        amount=Decimal(amount),
        payment_method=method,
        status=PaymentStatus.PENDING,
        transaction_id="init",   # sẽ update sau bằng vnp_TxnRef
    )
    db.session.add(pay)
    db.session.flush()  # để có pay.id
    db.session.commit()
    return pay


def update_payment_status(payment_id: int, status: PaymentStatus, transaction_id: str | None = None) -> None:
    pay = Payment.query.get(payment_id)
    if not pay:
        return
    pay.status = status
    if transaction_id:
        pay.transaction_id = transaction_id
    db.session.commit()