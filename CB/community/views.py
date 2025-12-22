from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from .models import Message, Notification
import re 
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from .models import Post

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
    
    # (선택사항) 템플릿에서 권한 체크를 쉽게 하기 위해
    # 여기서 미리 필터링해서 보낼 수도 있지만, 
    # 지금은 일단 다 보여주고 클릭 시 튕기게(이미 구현함) 하는 게 구현이 빠릅니다.
    
    context = {
        'boards': boards,
    }
    return render(request, 'community/board_list.html', context)

# 5. 글 목록 (Post List)
@login_required
def post_list(request, board_slug):
    board = get_object_or_404(Board, slug=board_slug)
    
    if not board.can_read(request.user):
        messages.error(request, "🚫 접근 권한이 없는 게시판입니다.")
        return redirect('board_list')

    posts = board.posts.all().order_by('-created_at')
    
    # ▼ [중요] 이 줄이 없으면 HTML이 권한을 몰라서 버튼을 숨겨버립니다!
    can_write_access = board.can_write(request.user)

    return render(request, 'community/post_list.html', {
        'board': board, 
        'posts': posts,
        # ▼ 이 변수도 꼭 넘겨줘야 합니다!
        'can_write_access': can_write_access 
    })

@login_required
def post_create(request, board_slug):
    board = get_object_or_404(Board, slug=board_slug)
    
    # ★ 바뀐 쓰기 권한 체크 로직
    if not board.can_write(request.user):
        messages.error(request, "🚫 이 게시판에 글을 쓸 권한이 없습니다.")
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

# 10. 게시글 삭제 (Soft Delete 버전)
@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, "삭제 권한이 없습니다.")
        return redirect('post_detail', post_id=post.id)
        
    # ★ DB에서 지우지 않고 '숨김' 처리만 함
    post.is_active = False 
    post.save()
    
    return redirect('post_list', board_slug=post.board.slug)

from .models import Post, Comment # Comment 모델 임포트 확인!



import re # 정규표현식 모듈
from django.contrib.auth import get_user_model

# 기존 comment_create 함수를 업그레이드
@login_required
def comment_create(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if not post.board.can_read(request.user):
        messages.error(request, "권한이 없습니다.")
        return redirect('board_list')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            # 1. 댓글 저장
            comment = Comment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            
            # 2. 멘션 감지 로직 (@닉네임 패턴 찾기)
            # 예: "안녕하세요 @김부장 님" -> ['김부장'] 추출
            mentioned_nicknames = re.findall(r'@(\w+)', content)
            
            # 3. 멘션된 유저들에게 알림 발송
            User = get_user_model()
            for nickname in set(mentioned_nicknames): # 중복 제거 (set)
                try:
                    target_user = User.objects.get(nickname=nickname)
                    
                    # 본인이 본인을 멘션한 건 알림 제외
                    if target_user != request.user:
                        Notification.objects.create(
                            recipient=target_user,
                            sender=request.user,
                            message=f"💬 {request.user.nickname}님이 댓글에서 언급했습니다: {content[:20]}...",
                            link=f"/community/post/{post.id}/"
                        )
                except User.DoesNotExist:
                    continue # 없는 닉네임이면 무시
                    
    return redirect('post_detail', post_id=post.id)

# 9. 댓글 삭제 (Comment Delete)
@login_required
def comment_delete(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    
    # 보안: 작성자 본인(또는 관리자)만 삭제 가능
    if request.user != comment.author and not request.user.is_superuser:
        messages.error(request, "삭제 권한이 없습니다.")
        return redirect('post_detail', post_id=comment.post.id)
        
    post_id = comment.post.id # 삭제하고 돌아갈 곳 저장
    comment.delete()
    return redirect('post_detail', post_id=post_id)


@login_required
def all_posts(request):
    """
    모든 게시판의 글을 최신순으로 모아보기 (전체 글 보기)
    """
    # 1. 모든 글 가져오기 (작성일 역순)
    posts = Post.objects.all().order_by('-created_at')
    
    # 2. 검색어 처리 (제목 or 내용)
    q = request.GET.get('q', '')
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(content__icontains=q))

    # 3. 페이징 처리 (15개씩)
    paginator = Paginator(posts, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'community/all_posts.html', {
        'page_obj': page_obj,
        'query': q,
    })

@login_required
def manage_boards(request):
    # 관리자만 접근 가능하게 하려면 아래 줄 주석 해제
    # if not request.user.is_staff: return redirect('home')

    if request.method == 'POST':
        form = BoardCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('community:manage_boards')  # 생성 후 목록으로 새로고침
    else:
        form = BoardCreationForm()

    # 이미 만들어진 게시판 목록도 같이 보여주기
    boards = Board.objects.all().order_by('-created_at')

    return render(request, 'community/manage_boards.html', {
        'form': form,
        'boards': boards
    })