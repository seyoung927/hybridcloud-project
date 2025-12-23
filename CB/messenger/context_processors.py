from .models import Message

def unread_count(request):
    if request.user.is_authenticated:
        # 내가 받은 것 중, 읽은 시간(read_at)이 비어있는(None) 것의 개수
        count = Message.objects.filter(receiver=request.user, read_at__isnull=True).count()
        return {'unread_msg_count': count}
    return {'unread_msg_count': 0}