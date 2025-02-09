from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Post, comment
from .Form import EmailPostForms, commentForm, Searchforms
from django.core.mail import send_mail
from django.views.generic import ListView
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, TrigramSimilarity


class PostListViev(ListView):
    queryset = Post.objects.filter(status=Post.Status.PUBLISHED)
    template_name = 'blog/list.html'
    paginate_by = 2

def post_list(request, tag_slug=None):
    posts = Post.objects.filter(status=Post.Status.PUBLISHED)
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts= posts.filter(tags__in=[tag])
    paginator = Paginator(posts,2)
    page_number = request.GET.get('page',1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request,
                  'blog/list.html',
                  {'object_list': posts, 'tag':tag}
                  )
    

def post_detail(request, year, month, day, slug):
     post = get_object_or_404(Post,
                            slug = slug,
                            publish__year=year,
                            publish__month=month,
                            publish__day=day,)
     comments = post.comments.filter(active=True)
     form = commentForm()

     post_tags_ids = post.tags.values_list('id', flat=True)
     similar_posts= Post.objects.filter(tags__in=post_tags_ids).exclude(id=post.id)
     similar_posts= similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]


     return render(request,
               'blog/detail.html',
              {'post': post,
               'comments': comments, 
               'form': form, 
               'similar_posts':similar_posts})
def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id,)
    sent=False
    if request.method == 'POST':
        forms =EmailPostForms(request.POST)
        if forms.is_valid():
            cd= forms.cleaned_data
            post_url=request.build_absolute_uri(post.get_absolute_url())
            subject =f"{cd['name']} recommends you read {post.title}"
            message =f'read {post.title} at {post_url}\n\n'\
                     f"{cd['name']}\s comments: {cd['comments']}"
            send_mail(subject,message,'your_account@gmail.com', [cd['to']])
            sent=True
    else:
        forms =EmailPostForms()
    return render(request,'share.html', {'post':post, 'form':forms, 'sent':sent})          

@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED)

    comment = None
    form = commentForm(data=request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()
    return render(request,
                  'comment.html',
                  {'post': post, 'form': form, 'comment': comment})         
    
def post_searh(request):
    form = Searchforms()
    query = None
    results= []

    if 'query'in request.GET:
        form = Searchforms(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            search_vector = SearchVector('title', weight='A') + \
                            SearchVector('body',weight='B')
            search_query = SearchQuery(query,config='spanish')
            results = Post.objects.annotate(
                search=search_vector,
                similarity=TrigramSimilarity('title', query),
            ).filter(similarity__gt=0.1).order_by('-similarity')

                

    return render(request, 
                  'blog/search.html', 
                  {'query':query, 
                   'form':form, 
                   'results':results})

