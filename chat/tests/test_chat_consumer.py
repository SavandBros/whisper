import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test.utils import freeze_time

from chat.consumers import ChatConsumer
from chat.models import Room
from users.models import User


@database_sync_to_async
def create_room() -> Room:
    return Room.objects.create(title='Savand Bros', staff_only=True)


@database_sync_to_async
def create_user(email: str, username: str, name: str) -> User:
    return User.objects.create_user(email=email, username=username, name=name, password='somepassword', is_staff=True)


@database_sync_to_async
def tear_down() -> None:
    User.objects.filter().delete()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_chat_consumer() -> None:
    user: User = await create_user(email='ali@email.com', username='alireza', name='Alireza Savand')
    user_2: User = await create_user(email='amir@email.com', username='amir', name='Amir Savand')

    room = await create_room()
    communicator = WebsocketCommunicator(ChatConsumer, "/testws/")
    communicator.scope['user'] = user
    connected, _ = await communicator.connect()
    assert connected

    assert communicator.instance.rooms == set()

    # Joining a room that doesn't exists
    await communicator.send_json_to({"command": "join", "room": '5451'})
    response = await communicator.receive_json_from()
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

    # Getting list of users in the room
    await communicator.send_json_to({'command': 'room_users', 'room': room.id})
    response = await communicator.receive_json_from()
    last_update: float = response['data']['users']['1']['last_update']
    assert isinstance(last_update, float)
    assert response == {
        'data': {
            'users': {
                '1': {
                    'name': 'Alireza Savand',
                    'username': 'alireza',
                    'left': False,
                    'last_update': last_update
                }
            }
        },
        'type': settings.MSG_TYPE_INTERNAL, 'room': room.id
    }

    communicator_2 = WebsocketCommunicator(ChatConsumer, "/testws/")
    communicator_2.scope['user'] = user_2
    connected, _ = await communicator_2.connect()
    assert connected

    await communicator_2.send_json_to({"command": "join", "room": room.id})
    response = await communicator_2.receive_json_from()
    assert response == {'join': str(room.id), 'title': 'Savand Bros'}

    response = await communicator.receive_json_from()
    assert response == {'msg_type': settings.MSG_TYPE_ENTER, 'room': room.id, 'username': user_2.username}

    assert communicator_2.instance.rooms == set(list([room.id, ]))

    await communicator_2.send_json_to({'command': 'room_users', 'room': room.id})
    response = await communicator_2.receive_json_from()

    last_update_1: float = response['data']['users']['1']['last_update']
    last_update_2: float = response['data']['users']['2']['last_update']

    assert isinstance(last_update_1, float)
    assert isinstance(last_update_2, float)
    assert response == {
        'data': {
            'users': {
                '1': {'username': user.username, 'name': user.name, 'left': False, 'last_update': last_update_1},
                '2': {'username': user_2.username, 'name': user_2.name, 'left': False, 'last_update': last_update_2}
            }
        },
        'type': settings.MSG_TYPE_INTERNAL, 'room': room.id
    }

    # User:Alireza gonna leave the room and Amir should be notified.
    await communicator.send_json_to({"command": "leave", "room": room.id})
    response = await communicator.receive_json_from()
    assert response == {'leave': str(room.id)}
    assert communicator.instance.rooms == set()

    # Here User: Amir has been notified about Alireza leaving.
    response = await communicator_2.receive_json_from()
    assert response == {'msg_type': settings.MSG_TYPE_LEAVE, 'room': room.id, 'username': user.username}

    # Let's get the users online the room now since Alireza has left us alone
    await communicator_2.send_json_to({'command': 'room_users', 'room': room.id})
    response = await communicator_2.receive_json_from()
    last_update_1: float = response['data']['users']['1']['last_update']
    last_update_2: float = response['data']['users']['2']['last_update']
    assert response == {
        'data': {
            'users': {
                '1': {'username': user.username, 'name': user.name, 'left': True, 'last_update': last_update_1},
                '2': {'username': user_2.username, 'name': user_2.name, 'left': False, 'last_update': last_update_2}
            }
        },
        'type': settings.MSG_TYPE_INTERNAL, 'room': room.id
    }

    # User: Amir is leaving the room
    await communicator_2.send_json_to({"command": "leave", "room": room.id})
    response = await communicator_2.receive_json_from()
    assert response == {'leave': str(room.id)}
    assert communicator_2.instance.rooms == set()

    # Finally disconnecting
    await communicator.disconnect()
    await communicator_2.disconnect()

    # Teardown
    await tear_down()
