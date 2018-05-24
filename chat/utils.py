# This decorator turns this function from a synchronous function into an async one
# we can call from our async consumers, that handles Django DBs correctly.
# For more, see http://channels.readthedocs.io/en/latest/topics/databases.html
from typing import Dict

from channels.db import database_sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from chat.exceptions import ClientError
from chat.models import Room
from users.models import User


@database_sync_to_async
def get_room_or_error(room_id: int, user: User):
    """
    Tries to fetch a room for the user, checking permissions along the way.
    """
    # Check if the user is logged in
    if not user.is_authenticated:
        raise ClientError("USER_HAS_TO_LOGIN")
    # Find the room they requested (by ID)
    try:
        room = Room.objects.get(pk=room_id)
    except Room.DoesNotExist:
        raise ClientError("ROOM_INVALID")
    # Check permissions
    if room.staff_only and not user.is_staff:
        raise ClientError("ROOM_ACCESS_DENIED")
    return room


@database_sync_to_async
def cache_or_update_room_presence(room_id: int, user: User) -> None:
    """Cache or update user presence in the room."""
    cache_key = get_room_presence_cache_key(room_id)
    room_cached = cache.get(cache_key)
    users_data: Dict[int, Dict[str, str]] = {
        user.id: {
            'username': user.username,
            'name': user.name,
            'left': False,
            'last_update': timezone.now().timestamp()
        }
    }

    if not room_cached:
        cache.set(cache_key, users_data, timeout=settings.ROOM_PRESENCE_TIMEOUT)
    else:
        room_cached.update(users_data)
        cache.set(cache_key, room_cached, timeout=settings.ROOM_PRESENCE_TIMEOUT)


@database_sync_to_async
def get_presence_users(room_id: int) -> Dict[int, Dict[str, str]]:
    """Return all the presence users in the room."""
    return cache.get(get_room_presence_cache_key(room_id))


@database_sync_to_async
def remove_user_from_presence(room_id: int, user_id: int) -> None:
    """Remove user from the room presence."""
    cache_key = get_room_presence_cache_key(room_id)
    room_cached = cache.get(cache_key)
    # Purge users that have left 2 hours ago!

    if room_cached:
        user_data: dict = room_cached[user_id]
        user_data.update({'left': True})

    cache.set(cache_key, room_cached, timeout=settings.ROOM_PRESENCE_TIMEOUT)


def get_room_presence_cache_key(room_id: int) -> str:
    """Return Room Presence Cache Key."""
    return f'room-presence-{room_id}'
