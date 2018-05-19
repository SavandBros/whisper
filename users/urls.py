from typing import List

from django.conf.urls import url

from users import views

app_name = 'users'

urlpatterns: List[url] = [
    url(r'^$', view=views.UserListView.as_view(), name='list'),
    url(r'^~redirect/$', view=views.UserRedirectView.as_view(), name='redirect'),
    url(r'^(?P<username>[\w.@+-]+)/$', view=views.UserDetailView.as_view(), name='detail'),
    url(r'^~update/$', view=views.UserUpdateView.as_view(), name='update'),
]
