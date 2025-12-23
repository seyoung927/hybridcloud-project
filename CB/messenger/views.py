from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Message
from .forms import MessageForm

# 1. 받은 쪽지함 (Inbox)
@login_required
def inbox(request):
    # [수정] received_messages -> messenger_received
    messages_list = request.user.messenger_received.all() 
    return render(request, 'messenger/inbox.html', {'messages_list': messages_list})

# 2. 쪽지 보내기
@login_required
def send_message(request):
    # GET 파라미터로 받는 사람 지정된 경우 (?to=3) 처리
    recipient_id = request.GET.get('to')
    initial_data = {}
    if recipient_id:
        initial_data['recipient'] = recipient_id

    if request.method == 'POST':
        # ★ [핵심] 여기도 폼 사용 & FILES 포함
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user # 보낸 사람은 나
            msg.save()
            
            # 🔔 알림 생성 (Notification)
            Notification.objects.create(
                recipient=msg.recipient, # 폼에서 선택한 받는 사람
                sender=request.user,
                message=f"📩 {request.user.nickname}님이 쪽지를 보냈습니다: {msg.title}",
                link="/community/inbox/"
            )
            
            messages.success(request, "쪽지를 전송했습니다.")
            return redirect('community:inbox')
    else:
        # 받는 사람이 지정되어 있다면 미리 선택된 상태로 폼 생성
        form = MessageForm(initial=initial_data)

# 3. 쪽지 읽기 (클릭 시 읽음 처리)
@login_required
def view_message(request, message_id):
    msg = get_object_or_404(Message, id=message_id)
    
    # 본인 확인 (내가 받은 쪽지거나, 내가 보낸 쪽지여야 함)
    if request.user != msg.sender and request.user != msg.receiver:
        messages.error(request, "권한이 없습니다.")
        return redirect('inbox')

    # 내가 받은 쪽지라면 읽음 처리(read_at 채우기)
    if request.user == msg.receiver and msg.read_at is None:
        msg.read_at = timezone.now()
        msg.save()
        
    return render(request, 'messenger/view_message.html', {'msg': msg})

@login_required
def sent_box(request):
    # 내가 보낸 메시지들 (최신순 정렬은 모델 Meta에 되어있음)
    messages_list = request.user.messenger_sent.all()
    return render(request, 'messenger/sent_box.html', {'messages_list': messages_list})