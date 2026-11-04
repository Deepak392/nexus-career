
from django.urls import path

from .views import StudentProfileView

urlpatterns = [
    path(
        "profile/",
        StudentProfileView.as_view(),
        name="student-profile",
    ),
]
