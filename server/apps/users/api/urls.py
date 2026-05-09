from dmr.routing import Router, path

from server.apps.users.api import views

app_name = 'users'

router: Router = Router(
    '',
    [
        path('token/', views.TokenCreate.as_view(), name='token_create'),
        path(
            'token/refresh/',
            views.TokenRefresh.as_view(),
            name='token_refresh',
        ),
        path('users/', views.UsersList.as_view(), name='users_list'),
    ],
)

urlpatterns = router.urls
