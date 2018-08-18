import django.views.static
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from homebytwo.landingpage import views as landingpage_views

urlpatterns = [

    # Landing Page URL patterns
    # home
    path('', landingpage_views.home, name="home"),

    # email-signup/
    path('email-signup/',
         landingpage_views.email_signup,
         name="email_signup"),

    # register
    path('register/',
         landingpage_views.register,
         name="register"),

    # URL patterns to other apps
    # django social auth
    path('', include('social_django.urls', namespace='social')),

    # routes/
    path('routes/', include('homebytwo.routes.urls')),

    # import/
    path('import/', include('homebytwo.importers.urls')),

    # admin/
    path('admin/', admin.site.urls),
    path('', include('django.contrib.auth.urls')),
]

# Serve Media URL in development. This is only needed when using runserver.
if settings.DEBUG:
    urlpatterns = [
        path('media/<path>.*', django.views.static.serve,
             {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    ] + staticfiles_urlpatterns() + urlpatterns

    # serve Django Debug Toolbar in DEBUG mode
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns