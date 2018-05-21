import json

from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import render
from typing import List

from chat.models import Room


@login_required
def index(request: HttpRequest):
    """
    Root page view. This is essentially a single-page app, if you ignore the
    login and admin parts.
    """
    # Get a list of rooms, ordered alphabetically
    rooms: QuerySet = Room.objects.order_by("title")
    rooms_js: List[dict] = []

    for room in rooms:
        rooms_js.append({
            'id': room.id,
            'title': room.title,
            'staff_only': room.staff_only,
            'group_name': room.group_name,
        })

    return render(request, "index.html", {"rooms": rooms, 'rooms_js': json.dumps(rooms_js)})
