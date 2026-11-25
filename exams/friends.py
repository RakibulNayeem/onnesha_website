"""Friend rules in one place: who is a friend, and how requests move."""
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Friendship

User = get_user_model()


def between(a, b):
    """The request linking two students in either direction, if any."""
    return Friendship.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)).first()


def friends_of(user):
    ids = Friendship.objects.filter(status="accepted").filter(Q(from_user=user) | Q(to_user=user)) \
        .values_list("from_user_id", "to_user_id")
    return User.objects.filter(pk__in={i for pair in ids for i in pair} - {user.pk}).order_by("username")


def incoming(user):
    return Friendship.objects.filter(to_user=user, status="pending").select_related("from_user")


def outgoing(user):
    return Friendship.objects.filter(from_user=user, status="pending").select_related("to_user")


def send(user, other):
    """Ask `other` to be friends. If they already asked us, that accepts it. Returns a short result code."""
    if other.pk == user.pk:
        return "self"
    link = between(user, other)
    if link and link.status == "accepted":
        return "already"
    if link and link.from_user_id == other.pk:
        link.status = "accepted"
        link.save(update_fields=["status"])
        return "accepted"
    if link:
        return "waiting"
    Friendship.objects.create(from_user=user, to_user=other)
    return "sent"
