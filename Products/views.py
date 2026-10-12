from django.shortcuts import render
from .models import Product

# create your views here.

def product_list(request):
    products = Product.objects.all()

    context = {
        "products": products
    }

    return render(request, "Products/product_list.html", context)

def product_detail(request, pk):
    product = Product.objects.get(pk=pk)

    context = {
        "product": product
    }

    return render(request, "Products/product_detail.html", context)