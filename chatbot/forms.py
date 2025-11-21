from .models import ChatRoom
from django.forms import ModelForm

class ChatRoomForm(ModelForm):
    class Meta:
        model = ChatRoom
        fields = ("title", )