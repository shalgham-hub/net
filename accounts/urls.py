from django.urls import path

from .views import (
    ConfigResetCredentials,
    HomeView,
    LoginView,
    LogoutView,
    MetricsView,
    PasswordResetView,
    VerifyPasswordResetView,
)

urlpatterns = [
    path('web/reset-password/', PasswordResetView.as_view(), name='password-reset'),
    path(
        'web/reset-password/<str:token>/',
        VerifyPasswordResetView.as_view(),
        name='verify-password-reset-token',
    ),
    path('web/login/', LoginView.as_view(), name='login'),
    path('web/logout/', LogoutView.as_view(), name='logout'),
    path('', HomeView.as_view(), name='home'),
    path('web/rest-credentials/', ConfigResetCredentials.as_view(), name='config-reset-credentials'),
    path('web/metrics/', MetricsView.as_view(), name='metrics'),
]
