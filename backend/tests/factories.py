from datetime import date, time, timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.bookings.models import Booking, OpeningHours, Service, ShopClosure
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
from apps.core.admin_permissions import AdminRole
from apps.delivery.models import RiderProfile
from apps.feedback.models import Review
from apps.orders.models import Order, OrderItem
from apps.vendors.models import Shop


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.CUSTOMER
    is_email_verified = False
    # Administrators get the full tier unless a test asks for another.
    admin_role = factory.LazyAttribute(
        lambda o: AdminRole.SUPER_ADMIN if o.role == User.Role.ADMINISTRATOR else None
    )

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "a-strong-password-1")
        if create:
            self.save()


class RiderFactory(UserFactory):
    role = User.Role.RIDER
    is_email_verified = True
    profile = factory.RelatedFactory(
        "tests.factories.RiderProfileFactory", factory_related_name="user"
    )


class RiderProfileFactory(DjangoModelFactory):
    class Meta:
        model = RiderProfile

    user = factory.SubFactory(RiderFactory, profile=None)
    phone = "+255700000001"
    vehicle_type = RiderProfile.VehicleType.MOTORCYCLE
    plate_number = "MC 123 ABC"


class ShopFactory(DjangoModelFactory):
    class Meta:
        model = Shop

    owner = factory.SubFactory(UserFactory, role=User.Role.VENDOR)
    name = factory.Sequence(lambda n: f"Shop {n}")
    status = Shop.Status.PENDING
    # Dar es Salaam city centre — the same point as tests' default delivery pin, so the default
    # delivery fee is the minimum fee.
    latitude = Decimal("-6.792400")
    longitude = Decimal("39.208300")


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


class ServicesShopFactory(ShopFactory):
    status = Shop.Status.APPROVED
    business_type = Shop.BusinessType.SERVICES


class ServiceCategoryFactory(CategoryFactory):
    name = factory.Sequence(lambda n: f"Service category {n}")
    slug = factory.Sequence(lambda n: f"service-category-{n}")
    kind = Category.Kind.SERVICE


class ServiceFactory(DjangoModelFactory):
    class Meta:
        model = Service

    shop = factory.SubFactory(ServicesShopFactory)
    category = factory.SubFactory(ServiceCategoryFactory)
    name = factory.Sequence(lambda n: f"Service {n}")
    description = "A test service."
    price = Decimal("20000.00")
    duration_minutes = 60
    is_published = True


class OpeningHoursFactory(DjangoModelFactory):
    class Meta:
        model = OpeningHours

    shop = factory.SubFactory(ServicesShopFactory)
    weekday = 0
    opens_at = time(9, 0)
    closes_at = time(17, 0)


class ShopClosureFactory(DjangoModelFactory):
    class Meta:
        model = ShopClosure

    shop = factory.SubFactory(ServicesShopFactory)
    date = date(2030, 1, 7)


class BookingFactory(DjangoModelFactory):
    class Meta:
        model = Booking

    customer = factory.SubFactory(UserFactory, role=User.Role.CUSTOMER, is_email_verified=True)
    service = factory.SubFactory(ServiceFactory)
    shop = factory.SelfAttribute("service.shop")
    starts_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    ends_at = factory.LazyAttribute(
        lambda o: o.starts_at + timedelta(minutes=o.service.duration_minutes)
    )
    respond_by = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=12))
    contact_phone = "+255712345678"
    price = factory.SelfAttribute("service.price")
    commission_rate = Decimal("10.00")
    commission_amount = factory.LazyAttribute(lambda o: o.price * Decimal("0.10"))
    vendor_earning = factory.LazyAttribute(lambda o: o.price - o.commission_amount)


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    shop = factory.SubFactory(ShopFactory, status=Shop.Status.APPROVED)
    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    description = "A test product."
    price = "9.99"
    stock_quantity = 10
    is_published = False


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart

    customer = factory.SubFactory(UserFactory, role=User.Role.CUSTOMER)


class CartItemFactory(DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory, is_published=True)
    quantity = 1


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    customer = factory.SubFactory(UserFactory, role=User.Role.CUSTOMER)
    recipient_name = factory.Faker("name")
    address_line = "12 Ring Road"
    city = "Accra"
    region = "Greater Accra"
    postal_code = "GA-184-9021"
    country = "Ghana"
    phone = "+233201234567"


class OrderItemFactory(DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory, is_published=True)
    quantity = 1
    unit_price = "9.99"
    status = OrderItem.Status.DELIVERED


class ReviewFactory(DjangoModelFactory):
    class Meta:
        model = Review

    customer = factory.SubFactory(UserFactory, role=User.Role.CUSTOMER)
    product = factory.SubFactory(ProductFactory, is_published=True)
    rating = 5
    comment = "Great product."
