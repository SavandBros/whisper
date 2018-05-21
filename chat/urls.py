from typing import List

from django.urls import path

from chat import views

app_name = 'chat'

urlpatterns: List[path] = [
    path(r'', view=views.index, name='index'),
]
