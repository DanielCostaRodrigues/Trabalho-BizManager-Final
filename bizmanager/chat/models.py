from django.db import models
from django.db import models
from django.utils import timezone
from autenticacao.models import User

class ChatRoom(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    file_url = models.CharField(max_length=255, blank=True, null=True)  
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.content[:50]}"