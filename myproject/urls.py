"""
URL configuration for pickleball project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from apps.user.views import account_deletion_request
from apps.user.views import event_matches_table
from django.shortcuts import render
from django.db.models import Prefetch
from apps.team import views
from apps.socialfeed.models import socialFeed, FeedFile
from django.shortcuts import render
from apps.user.models import User
from datetime import datetime
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def index(req):
    posts = socialFeed.objects.filter(block=False).order_by('-created_at').only(
        'id', 'user_id', 'text', 'created_at', 'number_comment', 'number_like'
    ).prefetch_related(
        Prefetch(
            'post_file',
            queryset=FeedFile.objects.order_by('id')[:1],  # Get only the first file per post
            to_attr='first_file'
        )
    )[:4]
    return render(req, "index/index.html", {"posts":posts})

def privacy_policy(req):
    return render(req, "index/privacy-policy.html")

def terms_conditions(req):
    return render(req, "index/terms-conditions.html")


def handler_404(request, exception):
    return render(request, '404.html', {})


urlpatterns = [
    path('', index, name="index"),
    path('privacy_policy/', privacy_policy, name="privacy_policy"),
    path('terms_conditions/', terms_conditions, name="terms_conditions"),
    path('pickleit-admin-main/', admin.site.urls),
    path('user/', include('apps.user.urls')),
    path('team/', include('apps.team.urls')),
    path('accessories/', include('apps.pickleitcollection.urls')),
    path('chat/', include('apps.chat.urls')),
    path('admin/', include('apps.admin_side.urls')),
    path('accessories/', include('apps.store.urls')),
    path('court/', include('apps.courts.urls')),
    path('socialfeed/', include('apps.socialfeed.urls')),
    path('clubs/', include('apps.clubs.urls')),
    path('user_side/', include('apps.user_side.urls')),
    path('requestdeletion1/', account_deletion_request, name="account_deletion_request"),
    path('events/matches/table/', event_matches_table, name="event_matches_table"),
]



if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)