from django.forms import ModelForm

from .models import ChatRoom


class ChatRoomForm(ModelForm):
    class Meta:
        model = ChatRoom
        fields = ("title",)
