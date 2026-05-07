from django.db import models


class UserRole(models.TextChoices):
    BUYER = "buyer", "Buyer"
    SELLER = "seller", "Seller"
    ADMIN = "admin", "Admin"
