from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from .models import Message, Notification

User = get_user_model()

# 1. 받은 쪽지함 (Inbox)
@login_required
def inbox(request):
    # 나에게 온 쪽지를 최신순으로 가져옴
    messages = request.user.received_messages.all()
    return render(request, 'community/inbox.html', {'messages': messages})

# 2. 쪽지 보내기 (Send)
@login_required
def send_message(request):
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient') # 받는 사람 ID
        content = request.POST.get('content')
        
        try:
            recipient = User.objects.get(id=recipient_id)
            
            # 쪽지 저장
            Message.objects.create(
                sender=request.user,
                recipient=recipient,
                content=content
            )
            
            # (선택) 쪽지 받았다고 알림(Notification)도 하나 꽂아줄까요?
            Notification.objects.create(
                recipient=recipient,
                sender=request.user,
                message=f"📩 {request.user.nickname}님이 쪽지를 보냈습니다.",
                link="/community/inbox/"
            )
            
            return redirect('inbox') # 보낸 후 내 쪽지함으로 이동
            
        except User.DoesNotExist:
            return HttpResponseForbidden("존재하지 않는 사용자입니다.")
            
    # GET 요청이면: 쪽지 쓰는 화면(유저 목록 포함) 보여주기
    users = User.objects.exclude(id=request.user.id) # 나 빼고 전체 유저 목록
    return render(request, 'community/send_message.html', {'users': users})

# 3. 쪽지 상세 보기 (읽음 처리)
@login_required
def view_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)
    
    # 보안 검사: 내 쪽지도 아닌데 남이 보려고 하면 차단
    if message.recipient != request.user and message.sender != request.user:
        return HttpResponseForbidden("권한이 없습니다.")
    
    # 받은 사람이 읽었을 때만 '읽음 처리'
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
        
    return render(request, 'community/view_message.html', {'message': message})

from django.contrib import messages
from .models import Board, Post

# 4. 게시판 목록 (Board List)
def board_list(request):
    boards = Board.objects.all()
    return render(request, 'community/board_list.html', {'boards': boards})

# 5. 글 목록 (Post List)
@login_required
def post_list(request, board_slug):
    board = get_object_or_404(Board, slug=board_slug)
    
    # ★ 읽기 권한 체크 (Rank Power 이용)
    # 유저 등급(user.rank_power)이 게시판 제한(read_min_rank)보다 낮으면?
    if request.user.rank_power < board.read_min_rank:
        messages.error(request, "이 게시판을 볼 권한이 없습니다.")
        return redirect('board_list') # 쫓아냄

    posts = board.posts.all()
    return render(request, 'community/post_list.html', {'board': board, 'posts': posts})

# 6. 글 쓰기 (Post Create) - ★ 권한 제어의 핵심
@login_required
def post_create(request, board_slug):
    board = get_object_or_404(Board, slug=board_slug)
    
    # ★ 쓰기 권한 체크 (핵심 로직!)
    # 사원(10)이 공지사항(40)에 쓰려고 하면 여기서 막힘
    if request.user.rank_power < board.write_min_rank:
        messages.error(request, "이 게시판에 글을 쓸 권한이 없습니다 (직급 부족).")
        return redirect('post_list', board_slug=board.slug)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        file = request.FILES.get('file') # 파일 업로드 처리
        
        Post.objects.create(
            board=board,
            author=request.user,
            title=title,
            content=content,
            file=file
        )
        return redirect('post_list', board_slug=board.slug)

    return render(request, 'community/post_create.html', {'board': board})
    
# 7. 글 상세 보기
@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    # 조회수 증가 (쿠키 등을 써서 중복 방지하면 좋지만 일단 단순하게)
    post.view_count += 1
    post.save()
    
    return render(request, 'community/post_detail.html', {'post': post})