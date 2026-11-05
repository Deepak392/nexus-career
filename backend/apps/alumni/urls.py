from django.urls import path

from .views import AlumniProfileView, AlumniSearchView

urlpatterns = [
    path("profile/", AlumniProfileView.as_view(), name="alumni-profile"),
    path("search/", AlumniSearchView.as_view(), name="alumni-search"),
]