from django.contrib import admin
from .models import Board, Post, Comment, Notification

# 간단하게 등록
admin.site.register(Board)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Notification)