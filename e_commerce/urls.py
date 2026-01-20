from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API_URL = 'https://semisuccessfully-unmauled-genoveva.ngrok-free.dev'

if 'ef542fe9bec5.ngrok-free.app' in settings.ALLOWED_HOSTS:
    # Production configuration
    API_URL = 'https://ef542fe9bec5.ngrok-free.app'
    API_SCHEMES = ['https']
else:
    # Development configuration
    API_URL = 'http://127.0.0.1:8000'
    API_SCHEMES = ['http']

schema_view = get_schema_view(
    openapi.Info(
        title="e_commerce API",
        default_version="v1",
        description="API documentation for e_commerce",
        terms_of_service="https://www.e_commerce.com/terms/",
        contact=openapi.Contact(email="contact@e_commerce.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),# noqa
    url=API_URL,
    # schemes=API_SCHEMES,
)


urlpatterns = [
    path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    # path("", include("honey.urls")),
    path("alid/", admin.site.urls),
    path("", include("home.urls")),
    path("", include("vendors.urls")),
    path("", include("stock.urls")),
    path("", include("payment.urls")),

    # Swagger URLs
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),  # noqa
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),  # noqa
    path(
        "redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),  # noqa
]

# handler404 = "admin_panel.views.custom_404_handler"
# handler500 = "admin_panel.views.custom_500_handler"

# Add Debug Toolbar URLs
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # noqa
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )  # noqa
