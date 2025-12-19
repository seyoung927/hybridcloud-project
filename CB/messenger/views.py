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
    if request.method == 'POST':
        form = MessageForm(request.POST, user=request.user)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            messages.success(request, "쪽지를 성공적으로 보냈습니다.")
            return redirect('inbox')
    else:
        form = MessageForm(user=request.user)
    
    return render(request, 'messenger/send_message.html', {'form': form})

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