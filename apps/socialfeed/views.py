from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
import random
from math import radians, sin, cos, sqrt, atan2
from apps.socialfeed.models import *
from apps.socialfeed.serializers import *
from apps.user.models import User
###social feed

class SocialFeedPagination(PageNumberPagination):
    page_size = 5  # Default items per page
    page_size_query_param = 'per_page'  # Allow clients to set page size via query param
    max_page_size = 100  # Maximum items per page

@api_view(['GET'])
def my_social_feed(request):
    res = {
        "count": 0,
        "next": None,
        "previous": None,
        "results":[]
        }
    data = request.GET
    user_uuid = data.get("user_uuid")
    check_user = User.objects.filter(uuid=user_uuid)
    if check_user.exists():
        get_user = check_user.first()
        feeds = socialFeed.objects.filter(user=get_user).order_by('-created_at')
        
        # Shuffle the data
        serializer = MysocialFeedSerializer(feeds, many=True)
        data = serializer.data
        random.shuffle(data)

        # Apply pagination
        paginator = SocialFeedPagination()
        paginated_data = paginator.paginate_queryset(data, request)

        return paginator.get_paginated_response(paginated_data)
    else:
        return Response(res, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def social_feed_list(request):
    user_uuid = request.GET.get("user_uuid", None)
    feeds = socialFeed.objects.filter(block=False).order_by('-created_at')
    serializer = SocialFeedSerializer(feeds, many=True, context={'user_uuid': user_uuid})
    data = serializer.data
    random.shuffle(data)
    paginator = SocialFeedPagination()
    paginated_data = paginator.paginate_queryset(data, request)
    return paginator.get_paginated_response(paginated_data)

@api_view(['GET'])
def social_feed_detail(request, pk):
    feed = get_object_or_404(socialFeed, pk=pk)
    serializer = socialFeedDetailsSerializer(feed)
    return Response(serializer.data)

@api_view(['POST'])
def post_social_feed(request):
    try:
        data = request.POST
        user_uuid = data.get("user_uuid")
        user = User.objects.filter(uuid=user_uuid)
        if not user.exists():
            return Response(
                {
                "msg":"Unauthorized access", 
                "status": status.HTTP_400_BAD_REQUEST
                }
                )
        
        get_user = user.first()
        text = data.get("text")
        post_files = request.FILES.getlist("post_files")

        feed = socialFeed(text=text, user=get_user)
        feed.save()

        for post_file in post_files:
            save_file = FeedFile(post=feed, file=post_file)
            save_file.save()

        return Response(
                        {
                        "msg":"Successfully posted your feed!", 
                        "status": status.HTTP_201_CREATED
                        }
                        )
    except Exception as e:
        return Response(
                        {
                        "msg":str(e), 
                        "status": status.HTTP_400_BAD_REQUEST
                        })

@api_view(['POST'])
def post_comment(request):
    user_uuid = request.data.get("user_uuid")
    post_id = request.data.get("post_id")
    text = request.data.get("text")
    parent_comment_id = request.data.get("parent_comment_id", None)

    # Fetch user by UUID
    user = User.objects.filter(uuid=user_uuid).first()
    if not user:
        return Response({"msg": "Unauthorized access", "status": status.HTTP_400_BAD_REQUEST})

    # Fetch post by ID
    post = socialFeed.objects.filter(id=post_id).first()
    if not post:
        return Response({"msg": "This is not a valid post", "status": status.HTTP_400_BAD_REQUEST})

    # Create a new comment
    save_comment = CommentFeed(user=user, post=post, comment_text=text)

    # If there is a parent comment ID, set it
    if parent_comment_id not in [None, "None"]:
        try:
            parent_comment = CommentFeed.objects.get(id=parent_comment_id)
            save_comment.parent_comment = parent_comment
        except CommentFeed.DoesNotExist:
            return Response({"msg": "Parent comment not found", "status": status.HTTP_400_BAD_REQUEST})

    save_comment.save()

    return Response({"msg": "Post your comment", "status": status.HTTP_200_OK})

@api_view(['POST'])
def post_like(request):
    try:
        user_uuid = request.data.get("user_uuid")
        post_id = request.data.get("post_id")

        # Validate user
        user = User.objects.filter(uuid=user_uuid).first()
        if not user:
            return Response({"msg": "Unauthorized access", "status": status.HTTP_400_BAD_REQUEST})

        # Validate post
        post = socialFeed.objects.filter(id=post_id).first()
        if not post:
            return Response({"msg": "This is not a valid post", "status": status.HTTP_400_BAD_REQUEST})

        # Check if the user has already liked the post
        existing_like = LikeFeed.objects.filter(post=post, user=user).first()
        if existing_like:
            # If like exists, remove it (dislike)
            existing_like.delete()
            total_likes = LikeFeed.objects.filter(post=post).count()
            return Response({"msg": "Unlike", "total_like": total_likes, "status": status.HTTP_200_OK})
        else:
            # If like does not exist, create it
            LikeFeed.objects.create(post=post, user=user)
            total_likes = LikeFeed.objects.filter(post=post).count()
            return Response({"msg": "Like", "total_like": total_likes, "status": status.HTTP_200_OK})
    except Exception as e:
        return Response({"msg": str(e), "status": status.HTTP_400_BAD_REQUEST})


@api_view(['GET'])
def like_user_list(request, pk):
    post = get_object_or_404(socialFeed, pk=pk)
    likes = LikeFeed.objects.filter(post=post)
    serializer = LikeFeedSerializer(likes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def comment_list(request, pk):
    post = get_object_or_404(socialFeed, pk=pk)
    comments = CommentFeed.objects.filter(post=post)
    serializer = CommentFeedSerializer(comments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def report_post(request):
    try:
        user_uuid = request.data.get("user_uuid")
        post_id = request.data.get("post_id")

        user = User.objects.filter(uuid=user_uuid).first()
        if not user:
            return Response({"msg": "Unauthorized access", "status": status.HTTP_400_BAD_REQUEST})

        post = socialFeed.objects.filter(id=post_id).first()
        if not post:
            return Response({"msg": "This is not a valid post", "status": status.HTTP_400_BAD_REQUEST})

        existing_report = FeedReport.objects.filter(feed=post, user=user).first()
        if existing_report:
            return Response({"msg": "Already reported", "status": status.HTTP_200_OK})
        else:
            FeedReport.objects.create(feed=post, user=user)  # Fixed missing object creation
            return Response({"msg": "Successfully reported the post to admin", "status": status.HTTP_200_OK})
    except Exception as e:
        return Response({"msg": str(e), "status": status.HTTP_400_BAD_REQUEST})