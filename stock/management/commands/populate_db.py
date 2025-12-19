import random
from decimal import Decimal
from django.utils.text import slugify
import uuid
from django.core.management.base import BaseCommand
from django.utils import lorem_ipsum
from stock.models import User, Product, Order, OrderItem, Shelf, ShelfItem
from vendors.models import VendorProfile

class Command(BaseCommand):
    help = 'Creates application data'

    def handle(self, *args, **kwargs):
        # get or create superuser
        user = User.objects.filter(username='admin').first()
        if not user:
            user = User.objects.create_superuser(username='admin', password='test')

        
        vendor_profile, created = VendorProfile.objects.get_or_create(
        user=user,
        defaults={
                'store_name': 'System Vendor',
                'store_handle': 'system-vendor',
                'description': 'System vendor for existing Product',
                'is_approved': True,
                'contact_email': 'system@vendor.com',
                'contact_phone': '0000000000',
                'address': 'System address'
            }
        )

        # create Product - name, desc, price, stock, image
        product = [
            Product(name="Winter cloth", descriptions=lorem_ipsum.paragraph(), price=Decimal('12.99'), stock=4, vendor=vendor_profile, handle=f"{slugify('Winter cloth')}-{uuid.uuid4().hex[:6]}"),
            Product(name="Summer cloth", descriptions=lorem_ipsum.paragraph(), price=Decimal('70.99'), stock=6, vendor=vendor_profile, handle=f"{slugify('Summer cloth')}-{uuid.uuid4().hex[:6]}"),
            Product(name="Velvet Underground & Nico", descriptions=lorem_ipsum.paragraph(), price=Decimal('15.99'), stock=11, vendor=vendor_profile, handle=f"{slugify('Velvet Underground & Nico')}-{uuid.uuid4().hex[:6]}"),
            Product(name="jersey", descriptions=lorem_ipsum.paragraph(), price=Decimal('17.99'), stock=2, vendor=vendor_profile, handle=f"{slugify('jersey')}-{uuid.uuid4().hex[:6]}"),
            Product(name="polo", descriptions=lorem_ipsum.paragraph(), price=Decimal('350.99'), stock=4, vendor=vendor_profile, handle=f"{slugify('polo')}-{uuid.uuid4().hex[:6]}"),
            Product(name="shoes", descriptions=lorem_ipsum.paragraph(), price=Decimal('500.05'), stock=0, vendor=vendor_profile, handle=f"{slugify('shoes')}-{uuid.uuid4().hex[:6]}"),
        ]

        # create Product & re-fetch from DB
        Product.objects.bulk_create(product)
        Product = Product.objects.all()


        # create some dummy orders tied to the superuser
        for _ in range(3):
            # create an Order with 2 order items
            order = Order.objects.create(user=user)
            shelf = Shelf.objects.create(user=user, vendor=vendor_profile, name=f"Shelf {_+1}")
            for product in random.sample(list(Product), 2):
                OrderItem.objects.create(
                    order=order, Product=product, quantity=random.randint(1,3)
                )
                ShelfItem.objects.create(
                    shelf=shelf, Product=product, quantity=random.randint(1,3)
                )
        self.stdout.write(self.style.SUCCESS('Database populated successfully.'))