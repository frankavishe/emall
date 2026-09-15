import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User


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
