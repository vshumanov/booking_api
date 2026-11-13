from rest_framework.routers import DefaultRouter

from .views import BlockViewSet, BookingViewSet, PropertyViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("bookings", BookingViewSet, basename="booking")
router.register("blocks", BlockViewSet, basename="block")

urlpatterns = router.urls
