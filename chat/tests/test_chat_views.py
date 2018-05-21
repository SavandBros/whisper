from django.http import HttpResponseRedirect, HttpResponse
from django.test import TestCase
from django.urls import reverse

from chat.models import Room
from users.models import User


class TestChatViews(TestCase):
    """Unit testing Chat Views."""
    @staticmethod
    def create_user() -> User:
        return User.objects.create_user(email='ali@email.com', username='alireza', password='somepassword')

    def login_user(self) -> None:
        assert self.client.login(username='alireza', password='somepassword')

    def test_authorized_only(self) -> None:
        resp: HttpResponseRedirect = self.client.get(reverse('chat:index'))

        self.assertEqual(resp.status_code, HttpResponseRedirect.status_code)

        self.create_user()
        self.login_user()

        resp: HttpResponse = self.client.get(reverse('chat:index'))
        self.assertEqual(resp.status_code, 200)

    def test_rooms_jsonify(self) -> None:
        self.create_user()
        self.login_user()

        Room.objects.create(title='my room', staff_only=True)
        Room.objects.create(title='second room', staff_only=False)

        resp: HttpResponse = self.client.get(reverse('chat:index'))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['rooms'].count(), Room.objects.order_by("title").count())
        self.assertEqual(
            resp.context['rooms_js'],
            '[{"id": 1, "title": "my room", "staff_only": true, "group_name": "room-1"}, '
            '{"id": 2, "title": "second room", "staff_only": false, "group_name": "room-2"}]'
        )
