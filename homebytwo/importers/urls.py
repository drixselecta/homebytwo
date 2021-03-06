from django.urls import path

from . import views

urlpatterns = [
    # importers: /import/
    path("", views.index, name="importers_index"),
    path("gpx/", views.upload_gpx, name="upload_gpx"),
    # /import/strava/
    path("<str:data_source>/", views.import_routes, name="import_routes"),
    # /import/strava/1234567/
    path("<str:data_source>/<int:source_id>/", views.import_route, name="import_route"),
    # /import/switzerland_mobility/login/
    path(
        "switzerland-mobility/login/",
        views.switzerland_mobility_login,
        name="switzerland_mobility_login",
    ),
]
