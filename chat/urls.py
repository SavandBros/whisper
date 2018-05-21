from typing import List

from django.conf.urls import url

from chat import views

app_name = 'chat'

urlpatterns: List[url] = [
    url(r'', view=views.index, name='index'),
]
