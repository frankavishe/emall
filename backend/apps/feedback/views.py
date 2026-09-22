from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.core.permissions import IsCustomer
from apps.feedback.models import Review
from apps.feedback.permissions import has_delivered_purchase
from apps.feedback.serializers import ReviewWriteSerializer


class CustomerReviewView(APIView):
    """Create-or-update (`POST`) and delete (`DELETE`) the requesting Customer's own review on a
    product, gated on a DELIVERED purchase (FR-001, FR-002, FR-003, FR-004; research.md §2-3)."""

    permission_classes = [IsCustomer]

    def post(self, request, product_id):
        product = get_object_or_404(Product.objects.all(), pk=product_id)
        if not has_delivered_purchase(request.user, product):
            raise PermissionDenied("You can only review products you have received.")

        serializer = ReviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review, created = Review.objects.update_or_create(
            customer=request.user,
            product=product,
            defaults={
                "rating": serializer.validated_data["rating"],
                "comment": serializer.validated_data.get("comment", ""),
            },
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ReviewWriteSerializer(review).data, status=response_status
        )

    def delete(self, request, product_id):
        review = get_object_or_404(Review, customer=request.user, product_id=product_id)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
