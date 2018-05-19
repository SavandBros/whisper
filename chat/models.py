from django.db import models
from django.utils.translation import ugettext_lazy as _


class Room(models.Model):
    """A room for people to chat in."""
    title = models.CharField(verbose_name=_('title'), max_length=255)
    # If only "staff" users are allowed (is_staff on django's User)
    staff_only = models.BooleanField(verbose_name=_('staff only'), default=False)

    class Meta:
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')

    def __str__(self) -> str:
        return self.title

    @property
    def group_name(self) -> str:
        """
        Returns the Channels Group name that sockets should subscribe to to get sent messages as they are generated.
        """
        return f'room-{self.id}'
