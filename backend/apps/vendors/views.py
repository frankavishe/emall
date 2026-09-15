from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from apps.core.permissions import IsVendor
from apps.vendors.models import Shop
from apps.vendors.serializers import ShopSerializer


class VendorShopListCreateView(ListCreateAPIView):
    permission_classes = [IsVendor]
    serializer_class = ShopSerializer
    pagination_class = None

    def get_queryset(self):
        return Shop.objects.filter(owner=self.request.user).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()
        return Response(self.get_serializer(shop).data, status=status.HTTP_201_CREATED)
