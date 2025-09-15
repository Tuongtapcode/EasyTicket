from app.models import Order

def get_order_by_id(order_id):
    order = Order.query.get(order_id)
    return order