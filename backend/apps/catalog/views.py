from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, Product
from apps.catalog.permissions import IsApprovedShopOwnerForProduct, IsProductOwner
from apps.catalog.serializers import (
    CatalogProductDetailSerializer,
    CatalogProductListSerializer,
    CatalogShopSerializer,
    AdminCategorySerializer,
    AdminCategoryWriteSerializer,
    CategoryConflict,
    CategoryTreeSerializer,
    VendorProductListSerializer,
    VendorProductWriteSerializer,
)
from apps.core.pagination import LimitedPageNumberPagination
from apps.core.permissions import IsAdministrator, IsVendor
from apps.vendors.models import Shop


class CategoryListView(ListAPIView):
    """Public, read-only category tree: top-level categories with their subcategories. Serves
    both the catalog filter and the vendor product form's category picker. Administrators manage
    categories through AdminCategoryListCreateView."""

    permission_classes = [AllowAny]
    pagination_class = None
    serializer_class = CategoryTreeSerializer
    queryset = (
        Category.objects.filter(parent__isnull=True)
        .prefetch_related(
            models.Prefetch("children", queryset=Category.objects.order_by("name"))
        )
        .order_by("name")
    )


def _admin_categories():
    return Category.objects.annotate(
        product_count=models.Count(
            "products", filter=models.Q(products__is_deleted=False), distinct=True
        ),
        all_product_count=models.Count("products", distinct=True),
        child_count=models.Count("children", distinct=True),
    )


def _admin_category_tree_response():
    categories = list(_admin_categories().order_by("name"))
    children = {}
    for category in categories:
        if category.parent_id is not None:
            children.setdefault(category.parent_id, []).append(category)
    top_level = [c for c in categories if c.parent_id is None]
    return Response(
        AdminCategorySerializer(top_level, many=True, context={"children": children}).data
    )


def _admin_category_response(category_id, response_status=status.HTTP_200_OK):
    category = _admin_categories().get(pk=category_id)
    return Response(AdminCategorySerializer(category).data, status=response_status)


class AdminCategoryListCreateView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        return _admin_category_tree_response()

    def post(self, request):
        serializer = AdminCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return _admin_category_response(category.pk, status.HTTP_201_CREATED)


class AdminCategoryDetailView(APIView):
    permission_classes = [IsAdministrator]

    def patch(self, request, category_id):
        category = get_object_or_404(Category, pk=category_id)
        serializer = AdminCategoryWriteSerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _admin_category_response(category.pk)

    def delete(self, request, category_id):
        category = get_object_or_404(Category, pk=category_id)
        if category.children.exists():
            raise CategoryConflict(
                f"{category.name} still has subcategories. Delete or move them first."
            )
        # Soft-deleted products still reference the category, so count them too.
        if Product.all_objects.filter(category=category).exists():
            raise CategoryConflict(
                f"Products are listed under {category.name}. Move them to another category "
                "first."
            )
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CatalogProductListView(ListAPIView):
    """Public browse/search/filter (FR-007, FR-008, FR-009, FR-011). Restricted server-side to
    published, non-deleted products from APPROVED shops regardless of any client-supplied
    filter (contracts/catalog-api.md)."""

    permission_classes = [AllowAny]
    serializer_class = CatalogProductListSerializer
    pagination_class = LimitedPageNumberPagination

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_published=True, shop__status=Shop.Status.APPROVED)
            .select_related("shop", "category")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        params = self.request.query_params
        q = params.get("q")
        if q:
            queryset = queryset.filter(
                models.Q(name__icontains=q) | models.Q(description__icontains=q)
            )
        shop = params.get("shop")
        if shop:
            if not shop.isdigit():
                return queryset.none()
            queryset = queryset.filter(shop_id=shop)
        category = params.get("category")
        if category:
            # A top-level category also matches products in its subcategories.
            queryset = queryset.filter(
                models.Q(category__slug=category) | models.Q(category__parent__slug=category)
            )
        min_price = params.get("min_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        max_price = params.get("max_price")
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        return queryset


class CatalogProductDetailView(APIView):
    """Uniform `404` for nonexistent, unpublished, soft-deleted, or non-APPROVED-shop products
    (FR-010, FR-011) — an anonymous caller can't distinguish "never existed" from "exists but
    hidden" (contracts/catalog-api.md)."""

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(
            Product.objects.filter(
                is_published=True, shop__status=Shop.Status.APPROVED
            ).select_related("shop", "category").prefetch_related("images"),
            pk=product_id,
        )
        return Response(
            CatalogProductDetailSerializer(product, context={"request": request}).data
        )


class CatalogShopDetailView(APIView):
    """Public shop profile (name, logo, theme colors). Same uniform `404` as product detail for
    a shop that isn't APPROVED."""

    permission_classes = [AllowAny]

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, pk=shop_id, status=Shop.Status.APPROVED)
        return Response(CatalogShopSerializer(shop, context={"request": request}).data)


class VendorProductListCreateView(ListCreateAPIView):
    permission_classes = [IsVendor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return VendorProductWriteSerializer
        return VendorProductListSerializer

    def get_queryset(self):
        queryset = (
            Product.objects.filter(shop__owner=self.request.user)
            .select_related("shop", "category")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        shop_id = self.request.query_params.get("shop_id")
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            VendorProductListSerializer(product, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class VendorProductDetailView(APIView):
    """PATCH/DELETE only require ownership (FR-003, FR-014) — not shop approval, unlike create
    and publish — see apps/catalog/permissions.py::IsProductOwner."""

    permission_classes = [IsVendor, IsProductOwner]

    def get_object(self, product_id):
        product = get_object_or_404(
            Product.objects.select_related("shop", "category"), pk=product_id
        )
        self.check_object_permissions(self.request, product)
        return product

    def patch(self, request, product_id):
        product = self.get_object(product_id)
        serializer = VendorProductWriteSerializer(
            product, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(VendorProductListSerializer(product, context={"request": request}).data)

    def delete(self, request, product_id):
        product = self.get_object(product_id)
        product.is_deleted = True
        product.deleted_at = timezone.now()
        product.save(update_fields=["is_deleted", "deleted_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class VendorProductPublishView(APIView):
    """Re-checks shop approval at publish time, not just at creation time — a shop's status
    could theoretically change between the two (contracts/catalog-api.md)."""

    permission_classes = [IsVendor, IsApprovedShopOwnerForProduct]

    def post(self, request, product_id):
        product = get_object_or_404(Product.objects.select_related("shop"), pk=product_id)
        self.check_object_permissions(request, product)
        missing = product.missing_fields_for_publish()
        if missing:
            return Response({"missing_fields": missing}, status=status.HTTP_400_BAD_REQUEST)
        product.is_published = True
        product.save(update_fields=["is_published"])
        return Response({"id": product.id, "is_published": product.is_published})


class VendorProductUnpublishView(APIView):
    permission_classes = [IsVendor, IsProductOwner]

    def post(self, request, product_id):
        product = get_object_or_404(Product.objects.select_related("shop"), pk=product_id)
        self.check_object_permissions(request, product)
        product.is_published = False
        product.save(update_fields=["is_published"])
        return Response({"id": product.id, "is_published": product.is_published})
