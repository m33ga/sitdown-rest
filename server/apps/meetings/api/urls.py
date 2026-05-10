from dmr.routing import Router, path

from server.apps.meetings.api import views

app_name = 'meetings'

router: Router = Router(
    '',
    [
        path(
            'groups/<uuid:group_id>/meetings/',
            views.MeetingsCollection.as_view(),
            name='meetings_collection',
        ),
        path(
            'meetings/<uuid:id>/',
            views.MeetingsDetail.as_view(),
            name='meetings_detail',
        ),
        path(
            'meetings/<uuid:id>/entries/',
            views.EntriesCollection.as_view(),
            name='entries_collection',
        ),
        path(
            'meetings/<uuid:id>/entries/<uuid:user_id>/',
            views.EntriesDetail.as_view(),
            name='entries_detail',
        ),
    ],
)

urlpatterns = router.urls
