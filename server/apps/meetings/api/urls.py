from dmr.routing import Router

app_name = 'meetings'

router: Router = Router('', [])

urlpatterns = router.urls
