from dmr.routing import Router

app_name = 'main'

router: Router = Router('', [])

urlpatterns = router.urls
