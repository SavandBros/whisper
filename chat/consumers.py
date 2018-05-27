from typing import Set

import bleach
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from chat.exceptions import ClientError
from chat.models import Room
from chat.utils import get_room_or_error, cache_or_update_room_presence, get_presence_users, remove_user_from_presence
from users.models import User


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    This chat consumer handles websocket connections for chat clients.

    It uses AsyncJsonWebsocketConsumer, which means all the handling functions
    must be async functions, and any sync work (like ORM access) has to be
    behind database_sync_to_async or sync_to_async. For more, read
    http://channels.readthedocs.io/en/latest/topics/consumers.html
    """
    # WebSocket event handlers

    async def connect(self):
        """Called when the websocket is handshaking as part of initial connection."""
        # Are they logged in?
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            # Accept the connection
            await self.accept()
        # Store which rooms the user has joined on this connection
        self.rooms: Set[int] = set()

    async def receive_json(self, content, **kwargs):
        """
        Called when we get a text frame. Channels will JSON-decode the payload
        for us and pass it as the first argument.
        """
        # Messages will have a "command" key we can switch on
        command = content.get("command", None)
        try:
            if command == "join":
                # Make them join the room
                await self.join_room(content["room"])
            elif command == "leave":
                # Leave the room
                await self.leave_room(content["room"])
            elif command == "send":
                await self.send_room(content["room"], content["message"])
            elif command == "room_users":
                await self.room_users(content['room'])
        except ClientError as e:
            # Catch any errors and send it back
            await self.send_json({"error": e.code})

    async def disconnect(self, code):
        """Called when the WebSocket closes for any reason."""
        # Leave all the rooms we are still in
        for room_id in list(self.rooms):
            try:
                await self.leave_room(room_id)
            except ClientError:
                pass

    # Command helper methods called by receive_json
    async def join_room(self, room_id: int):
        """Called by receive_json when someone sent a join command."""
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        user: User = self.scope['user']
        room: Room = await get_room_or_error(room_id, user)
        # Send a join message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.join",
                    "room_id": room_id,
                    "username": user.username,
                }
            )
        # Store that we're in the room
        self.rooms.add(room_id)
        await cache_or_update_room_presence(room_id, user)
        # Add them to the group so they get room messages
        await self.channel_layer.group_add(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish opening the room
        await self.send_json({
            "join": str(room.id),
            "title": room.title,
        })

    async def leave_room(self, room_id: int):
        """Called by receive_json when someone sent a leave command."""
        # The logged-in user is in our scope thanks to the authentication ASGI middleware
        user: User = self.scope['user']
        room: Room = await get_room_or_error(room_id, user)
        # Send a leave message if it's turned on
        if settings.NOTIFY_USERS_ON_ENTER_OR_LEAVE_ROOMS:
            await self.channel_layer.group_send(
                room.group_name,
                {
                    "type": "chat.leave",
                    "room_id": room_id,
                    "username": user.username,
                }
            )
        # Remove that we're in the room
        self.rooms.discard(room_id)
        await remove_user_from_presence(room_id, user.id)

        # Remove them from the group so they no longer get room messages
        await self.channel_layer.group_discard(
            room.group_name,
            self.channel_name,
        )
        # Instruct their client to finish closing the room
        await self.send_json({
            "leave": str(room.id),
        })

    async def send_room(self, room_id: int, message: str):
        """Called by receive_json when someone sends a message to a room."""
        # Check they are in this room
        if room_id not in self.rooms:
            raise ClientError("ROOM_ACCESS_DENIED")
        # Get the room and send to the group about it
        room: Room = await get_room_or_error(room_id, self.scope["user"])
        user: User = self.scope['user']
        await self.channel_layer.group_send(
            room.group_name,
            {
                "type": "chat.message",
                "room_id": room_id,
                "username": user.username,
                "message": message,
            }
        )
        await cache_or_update_room_presence(room_id, user)

    async def room_users(self, room_id: int) -> None:
        """Called when asking for list of the online users in the room."""
        await self.send_json({
            'type': settings.MSG_TYPE_INTERNAL,
            'room': room_id,
            'data': {'users': await get_presence_users(room_id)}
        })

    # Handlers for messages sent over the channel layer

    # These helper methods are named by the types we send - so chat.join becomes chat_join
    async def chat_join(self, event: dict):
        """Called when someone has joined our chat."""
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_ENTER,
                "room": event["room_id"],
                "username": event["username"],
            },
        )

    async def chat_leave(self, event: dict):
        """Called when someone has left our chat."""
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_LEAVE,
                "room": event["room_id"],
                "username": event["username"],
            },
        )

    async def chat_message(self, event: dict):
        """Called when someone has messaged our chat."""
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_MESSAGE,
                "room": event["room_id"],
                "username": event["username"],
                "message": bleach.linkify(event["message"]),
            },
        )
