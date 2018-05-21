from typing import List

from django.conf.urls import url
from django.contrib import auth

from users import views

app_name = 'users'

urlpatterns: List[url] = [
    url(r'^$', view=views.UserListView.as_view(), name='list'),
    url(r'^logout/$', view=auth.views.logout_then_login, name='logout'),
    url(r'^~redirect/$', view=views.UserRedirectView.as_view(), name='redirect'),
    url(r'^(?P<username>[\w.@+-]+)/$', view=views.UserDetailView.as_view(), name='detail'),
    url(r'^~update/$', view=views.UserUpdateView.as_view(), name='update'),
]
