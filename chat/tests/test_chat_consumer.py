import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings

from chat.consumers import ChatConsumer
from chat.models import Room
from users.models import User


@database_sync_to_async
def create_room() -> Room:
    return Room.objects.create(title='Savand Bros', staff_only=True)


@database_sync_to_async
def create_user() -> User:
    return User.objects.create_user(email='ali@email.com', username='alireza', password='somepassword', is_staff=True)


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer() -> None:
    user = await create_user()
    room = await create_room()
    communicator = WebsocketCommunicator(ChatConsumer, "/testws/")
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected

    assert communicator.instance.rooms == set()

    # Joining a room that doesn't exists
    await communicator.send_json_to({"command": "join", "room": '5451'})
    response = await communicator.receive_json_from()
    print(response)
    assert response == {'error': 'ROOM_INVALID'}

    # Test joining
    await communicator.send_json_to({"command": "join", "room": room.id})
    response = await communicator.receive_json_from()
    assert response == {'join': str(room.id), 'title': 'Savand Bros'}

    assert communicator.instance.rooms == set(list([room.id, ]))

    # Testing Sending Message
    message: str = 'Hello Alireza'
    await communicator.send_json_to({"command": "send", "room": room.id, 'message': message})
    response = await communicator.receive_json_from()
    assert response == {'msg_type': settings.MSG_TYPE_MESSAGE,
                        'room': room.id,
                        'username': user.username,
                        'message': message}

    # Testing Leaving the room
    await communicator.send_json_to({"command": "leave", "room": room.id})
    response = await communicator.receive_json_from()
    assert response == {'leave': str(room.id)}
    assert communicator.instance.rooms == set()

