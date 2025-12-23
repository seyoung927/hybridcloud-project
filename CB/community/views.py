from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from .models import Message, Notification
import re 
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from .models import Post
from .forms import PostForm  # 👈 forms.py에서 만든 폼 가져오기

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

    return render(request, 'community/send_message.html', {'form': form})
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
from django.db.models import Count, Q
from .models import Board, Post

# 4. 게시판 목록 (Board List)
def board_list(request):
    # [수정 전] boards = Board.objects.all()
    # 이렇게 하면 그냥 게시판만 가져오고, 글 개수는 HTML에서 샜었죠.

    # [수정 후] 여기서 '살아있는 글' 개수를 미리 계산해서 'post_count'라는 이름표를 붙여줍니다.
    boards = Board.objects.annotate(
        post_count=Count('posts', filter=Q(posts__is_active=True))
    )
    
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

    posts = board.posts.filter(is_active=True).order_by('-created_at')
    
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
    
    # 권한 체크
    if not board.can_write(request.user):
        messages.error(request, "🚫 이 게시판에 글을 쓸 권한이 없습니다.")
        return redirect('community:post_list', board_slug=board.slug)

    if request.method == 'POST':
        # ★ [핵심] request.FILES를 꼭 넣어야 사진/파일이 올라갑니다.
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.board = board       # 어느 게시판인지 연결
            post.author = request.user # 작성자 연결
            post.save()
            return redirect('community:post_list', board_slug=board.slug)
    else:
        form = PostForm()

    return render(request, 'community/post_create.html', {
        'board': board,
        'form': form # 템플릿으로 폼 넘겨주기
    })    
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

from .forms import BoardCreationForm

@login_required
def manage_boards(request):
    # 관리자만 접근 가능하게 하려면 아래 줄 주석 해제
    # if not request.user.is_staff: return redirect('home')

    if request.method == 'POST':
        form = BoardCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_boards')  # 생성 후 목록으로 새로고침
    else:
        form = BoardCreationForm()

    # 이미 만들어진 게시판 목록도 같이 보여주기
    boards = Board.objects.all().order_by('-created_at')

    return render(request, 'community/manage_boards.html', {
        'form': form,
        'boards': boards
    })

@login_required
def edit_board(request, board_id):
    # 수정할 게시판 객체를 가져옵니다 (없으면 404 에러)
    board = get_object_or_404(Board, id=board_id)

    if request.method == 'POST':
        # 1. 삭제 버튼을 눌렀을 경우
        if 'delete' in request.POST:
            board.delete()
            return redirect('manage_boards') # 삭제 후 목록으로 이동

        # 2. 수정 버튼을 눌렀을 경우
        # instance=board 를 넣어줘야 "새 글"이 아니라 "기존 글 수정"이 됩니다.
        form = BoardCreationForm(request.POST, instance=board)
        if form.is_valid():
            form.save()
            return redirect('manage_boards') # 수정 후 목록으로 이동
    else:
        # 처음 페이지 들어왔을 때 기존 내용을 채워서 보여줌
        form = BoardCreationForm(instance=board)

    return render(request, 'community/edit_board.html', {
        'form': form,
        'board': board
    })