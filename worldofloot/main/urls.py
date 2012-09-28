from django.conf.urls import patterns, url

urlpatterns = patterns('worldofloot.main.views',
    url(r'^$', 'index', name='index'),
    url(r'^about/', 'about', name='about'),
    url(r'^my/', 'my_loot', name='my_loot'),
    url(r'^recent/', 'recent', name='recent'),
    url(r'^popular/', 'popular', name='popular'),
    url(r'^user/(.*)', 'user', name='user'),
    url(r'^info/(.*)/(.*)', 'get_item_info', name='get_item_info'),
    url(r'^add/(.*)/(.*)/(.*)', 'add_item', name='add_item'),
    url(r'^remove/(.*)/(.*)', 'remove_item', name='remove_item'),
    url(r'^login_or_create/', 'login_or_create', name='login_or_create'),
    url(r'^logout/', 'logout_user', name='logout_user'),
)
