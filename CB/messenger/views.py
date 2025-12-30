from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Message
from .forms import MessageForm
from community.models import Notification # 🔔 알림은 community에서 빌려오기

# ==========================================
# 1. 받은 쪽지함 (Inbox)
# ==========================================
@login_required
def inbox(request):
    # 모델의 related_name='received_messages_messenger'를 사용합니다.
    messages_list = request.user.received_messages_messenger.all()
    return render(request, 'messenger/inbox.html', {'messages_list': messages_list})

# ==========================================
# 2. 보낸 쪽지함 (Sent Box)
# ==========================================
@login_required
def sent_box(request):
    # 모델의 related_name='sent_messages_messenger'를 사용합니다.
    messages_list = request.user.sent_messages_messenger.all()
    return render(request, 'messenger/sent_box.html', {'messages_list': messages_list})

# ==========================================
# 3. 쪽지 보내기 (Send Message)
# ==========================================
@login_required
def send_message(request):
    # '답장' 버튼 등을 통해 받는 사람 ID가 넘어왔을 때 처리 (?to=3)
    recipient_id = request.GET.get('to')
    initial_data = {}
    if recipient_id:
        initial_data['recipient'] = recipient_id

    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user # 보낸 사람은 현재 로그인한 사람
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
    
    # [보안] 본인 확인 (보낸 사람이나 받는 사람이 아니면 볼 수 없음)
    if request.user != msg.sender and request.user != msg.recipient:
        messages.error(request, "이 쪽지를 볼 권한이 없습니다.")
        return redirect('inbox')

    # [핵심] 내가 받는 사람이고, 아직 안 읽었다면 -> '읽음' 처리
    if request.user == msg.recipient and not msg.is_read:
        msg.is_read = True
        msg.save()
        
    return render(request, 'messenger/view_message.html', {'msg': msg})

from django.http import JsonResponse

def check_new_messages(request):
    # 안 읽은 쪽지(is_read=False) 개수 세기
    if request.user.is_authenticated:
        count = Message.objects.filter(receiver=request.user, is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})