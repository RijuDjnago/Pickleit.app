from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/notify/(?P<room_name>\w+)/$", consumers.NotificationConsumer.as_asgi()),
    # re_path(r"ws/admin_chat/(?P<room_name>\w+)/(?P<sender_id>\w+)/$", consumers.ChatConsumerAdmin.as_asgi()),
]