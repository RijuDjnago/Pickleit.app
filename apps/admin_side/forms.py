# forms.py
from django import forms
from apps.chat.models import MessageBox

class MessageForm(forms.ModelForm):
    class Meta:
        model = MessageBox
        fields = ['text_message', 'send_file', 'send_image']
