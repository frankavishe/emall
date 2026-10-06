import os
import uuid

from django.utils.deconstruct import deconstructible


@deconstructible
class UniqueUploadTo:
    """`upload_to` that stores each file under a random name in `prefix`. Media storage
    overwrites same-named files, so keeping the uploaded name would let two uploads of
    "photo.jpg" clobber each other — and deleting one would delete the other's file."""

    def __init__(self, prefix):
        self.prefix = prefix

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f"{self.prefix}/{uuid.uuid4().hex}{ext}"
