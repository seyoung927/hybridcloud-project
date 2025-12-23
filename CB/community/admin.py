from django.contrib import admin
from .models import Board, Post, Comment, Notification, Message

# 간단하게 등록
admin.site.register(Board)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Notification)
admin.site.register(Message)