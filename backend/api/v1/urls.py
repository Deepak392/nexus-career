from django.urls import include, path

urlpatterns = [
    path("students/", include("apps.students.urls")),
    path("alumni/", include("apps.alumni.urls")),
]