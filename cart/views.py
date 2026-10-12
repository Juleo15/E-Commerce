
import uuid
import requests

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Cart, CartItem, Order, OrderItem, Payment
from .forms import CheckoutForm
from Products.models import Product


def cart_detail(request):
    cart = None
    total = 0

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        for item in cart.items.all():
            total += item.product.price * item.quantity

    return render(
        request,
        "cart/cart_detail.html",
        {"cart": cart, "total": total}
    )


@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect("cart:cart_detail")


@login_required
def increase_quantity(request, pk):
    cart_item = get_object_or_404(
        CartItem,
        pk=pk,
        cart__user=request.user
    )

    cart_item.quantity += 1
    cart_item.save()

    return redirect("cart:cart_detail")


@login_required
def decrease_quantity(request, pk):
    cart_item = get_object_or_404(
        CartItem,
        pk=pk,
        cart__user=request.user
    )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    return redirect("cart:cart_detail")


@login_required
def remove_from_cart(request, pk):
    cart_item = get_object_or_404(
        CartItem,
        pk=pk,
        cart__user=request.user
    )

    cart_item.delete()

    return redirect("cart:cart_detail")


@login_required
def checkout(request):
    cart = get_object_or_404(
        Cart,
        user=request.user
    )

    items = list(cart.items.select_related("product").all())

    if not items:
        return redirect("cart:cart_detail")

    total = sum(
        (item.product.price * item.quantity for item in items),
        start=0
    )

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            # Save the order and its items together.
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.total_price = total
                order.save()

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )

                cart.items.all().delete()

            return redirect(
                "cart:pay_order",
                order_id=order.id
            )
    else:
        form = CheckoutForm()

    return render(
        request,
        "cart/checkout.html",
        {
            "cart": cart,
            "items": items,
            "total": total,
            "form": form,
        }
    )


@login_required
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "cart/my_orders.html",
        {"orders": orders}
    )


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order,
        pk=pk,
        user=request.user
    )

    return render(
        request,
        "cart/order_detail.html",
        {
            "order": order,
            "items": order.items.all(),
        }
    )


@login_required

@login_required
def pay_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if order.status != "Pending":
        return redirect("cart:order_detail", pk=order.id)

    if not request.user.email:
        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "Your account needs an email address "
                    "before you can pay."
                )
            }
        )

    if not settings.PAYSTACK_SECRET_KEY:
        return render(
            request,
            "cart/payment_failed.html",
            {"message": "Paystack is not configured correctly."}
        )

    # Reuse an existing pending payment or create one.
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "reference": uuid.uuid4().hex,
            "amount": order.total_price,
            "status": "Pending",
        }
    )

    # Don't create a new transaction for a completed payment.
    if payment.status == "Success":
        return redirect("cart:order_detail", pk=order.id)

    # Check that the payment amount still matches the order.
    if payment.amount != order.total_price:
        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "The payment amount doesn't match the order. "
                    "Please contact support before retrying."
                )
            }
        )

    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": request.user.email,
        "amount": int(payment.amount * 100),
        "currency": "NGN",
        "reference": payment.reference,
        "callback_url": request.build_absolute_uri(
            "/cart/payment/callback/"
        ),
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()

    except (requests.RequestException, ValueError):
        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "We couldn't connect to Paystack. "
                    "Your order is still recorded. "
                    "Check your orders before retrying."
                )
            }
        )

    if (
        result.get("status") is True
        and result.get("data", {}).get("authorization_url")
    ):
        return redirect(result["data"]["authorization_url"])

    return render(
        request,
        "cart/payment_failed.html",
        {
            "message": result.get(
                "message",
                "Paystack could not initialize this payment."
            )
        }
    )


@login_required
def payment_callback(request):
    reference = request.GET.get("reference") or request.GET.get("trxref")

    if not reference:
        return render(
            request,
            "cart/payment_failed.html",
            {"message": "No payment reference was provided."}
        )

    payment = get_object_or_404(
        Payment,
        reference=reference,
        order__user=request.user
    )

    if payment.status == "Success":
        return render(
            request,
            "cart/payment_success.html",
            {"order": payment.order}
        )

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "We couldn't verify your payment. "
                    "Your payment status has not been changed."
                )
            }
        )

    transaction_data = result.get("data", {})

    # Confirm the response belongs to this payment.
    details_match = (
        result.get("status") is True
        and transaction_data.get("reference") == payment.reference
        and transaction_data.get("amount") == int(payment.amount * 100)
        and transaction_data.get("currency") == "NGN"
    )

    if not details_match:
        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "We couldn't confirm the payment details. "
                    "Your order remains unpaid."
                )
            }
        )

    transaction_status = transaction_data.get("status")

    if transaction_status == "success":
        with transaction.atomic():
            payment.status = "Success"
            payment.save(update_fields=["status"])

            order = payment.order
            order.status = "Processing"
            order.save(update_fields=["status"])

        return render(
            request,
            "cart/payment_success.html",
            {"order": payment.order}
        )

    if transaction_status in ("failed", "abandoned"):
        payment.status = "Failed"
        payment.save(update_fields=["status"])

        return render(
            request,
            "cart/payment_failed.html",
            {
                "message": (
                    "Paystack reports that this payment was not completed. "
                    "Your order remains pending."
                )
            }
        )

    return render(
        request,
        "cart/payment_failed.html",
        {
            "message": (
                "Your payment is still pending or being processed. "
                "Please check again later."
            )
        }
    )