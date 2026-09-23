import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
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

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "a-strong-password-1")
        if create:
            self.save()


class ShopFactory(DjangoModelFactory):
    class Meta:
        model = Shop

    owner = factory.SubFactory(UserFactory, role=User.Role.VENDOR)
    name = factory.Sequence(lambda n: f"Shop {n}")
    status = Shop.Status.PENDING


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")


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
