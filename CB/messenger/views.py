from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse # 상단으로 이동
from .models import Message
from .forms import MessageForm
from community.models import Notification # 🔔 알림은 community에서 빌려오기

# ==========================================
# 1. 받은 쪽지함 (Inbox)
# ==========================================
@login_required
def inbox(request):
    # 최신순 정렬 추가 (.order_by('-created_at'))
    messages_list = request.user.received_messages_messenger.all().order_by('-created_at')
    return render(request, 'messenger/inbox.html', {'messages_list': messages_list})

# ==========================================
# 2. 보낸 쪽지함 (Sent Box)
# ==========================================
@login_required
def sent_box(request):
    # 최신순 정렬 추가
    messages_list = request.user.sent_messages_messenger.all().order_by('-created_at')
    return render(request, 'messenger/sent_box.html', {'messages_list': messages_list})
# ==========================================
# 3. 쪽지 보내기 (Send Message)
# ==========================================
@login_required
def send_message(request):
    recipient_id = request.GET.get('to')
    initial_data = {}
    if recipient_id:
        initial_data['recipient'] = recipient_id

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()

            # 🔔 알림 생성 (Notification)
            # 받는 사람(msg.recipient)에게 알림을 보냅니다.
            Notification.objects.create(
                recipient=msg.recipient,
                sender=request.user,
                message=f"📩 {request.user.nickname}님이 쪽지를 보냈습니다: {msg.title}",
                link="/messenger/inbox/" # 쪽지함 URL (urls.py 설정에 따라 다를 수 있음)
            )
            
            messages.success(request, "쪽지를 성공적으로 보냈습니다.")
            return redirect('inbox') # urls.py의 name='inbox'로 이동
    else:
        form = MessageForm(initial=initial_data)

    return render(request, 'messenger/send_message.html', {'form': form})

# ==========================================
# 4. 쪽지 상세 보기 & 읽음 처리 (View Message)
# ==========================================
@login_required
def view_message(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    
    # [보안] 본인 확인
    if request.user != msg.sender and request.user != msg.recipient:
        messages.error(request, "이 쪽지를 볼 권한이 없습니다.")
        return redirect('inbox')

    # [핵심] 받는 사람이 나고, 안 읽었으면 -> 읽음 처리
    # ⚠️ 중요: 여기서 msg.save()가 되어야 AJAX 알람이 꺼집니다!
    if request.user == msg.recipient and not msg.is_read:
        msg.is_read = True
        msg.save()
        
    return render(request, 'messenger/view_message.html', {'msg': msg})

# ==========================================
# 5. [API] 실시간 알람 확인용 (AJAX 연동)
# ==========================================
def check_new_messages(request):
    if request.user.is_authenticated:
        # ⚠️ 수정됨: receiver -> recipient (모델 필드명 통일)
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})