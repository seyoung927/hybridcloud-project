from .models import Message

def unread_count(request):
    if request.user.is_authenticated:
        # 수정 1: receiver -> recipient (모델 필드명 맞추기)
        # 수정 2: read_at -> is_read (읽음 여부 체크 방식 변경)
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_msg_count': count}
    return {'unread_msg_count': 0}