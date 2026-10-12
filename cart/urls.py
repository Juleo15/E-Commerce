from django.urls import path

from .views import (
    cart_detail,
    add_to_cart,
    increase_quantity,
    decrease_quantity,
    remove_from_cart,
    checkout,
    my_orders,
    order_detail,
    pay_order,
    payment_callback
)

app_name = "cart"


urlpatterns = [
    path(
        "",
        cart_detail,
        name="cart_detail"
    ),

    path(
        "add/<int:pk>/",
        add_to_cart,
        name="add_to_cart"
    ),

    path(
        "increase/<int:pk>/",
        increase_quantity,
        name="increase_quantity"
    ),

    path(
        "decrease/<int:pk>/",
        decrease_quantity,
        name="decrease_quantity"
    ),

    path(
        "remove/<int:pk>/",
        remove_from_cart,
        name="remove_from_cart"
    ),

    path(
        "checkout/",
        checkout,
        name="checkout"
    ),

    path(
        "orders/",
        my_orders,
        name="my_orders"
    ),

    path(
        "orders/<int:pk>/",
        order_detail,
        name="order_detail"
    ),
    path(
        "pay/<int:order_id>/",
        pay_order,
        name="pay_order"
    ),
    path(
        "payment/callback/",
        payment_callback,
        name="payment_callback"
    ),
]