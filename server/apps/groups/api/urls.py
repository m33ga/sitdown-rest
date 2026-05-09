from dmr.routing import Router, path

from server.apps.groups.api import views

app_name = 'groups'

router: Router = Router(
    '',
    [
        path('groups/', views.GroupsCollection.as_view(), name='groups_collection'),
        path(
            'groups/<uuid:id>/',
            views.GroupsDetail.as_view(),
            name='groups_detail',
        ),
        path(
            'groups/<uuid:id>/pin/',
            views.GroupsPin.as_view(),
            name='groups_pin',
        ),
        path(
            'groups/<uuid:id>/members/',
            views.GroupsMembersCollection.as_view(),
            name='groups_members_collection',
        ),
        path(
            'groups/<uuid:id>/members/<uuid:user_id>/',
            views.GroupsMembersDetail.as_view(),
            name='groups_members_detail',
        ),
    ],
)

urlpatterns = router.urls
