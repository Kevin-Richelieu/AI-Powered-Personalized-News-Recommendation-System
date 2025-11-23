from django.urls import path
from . import views

urlpatterns = [
    # 认证相关
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    
    # 主要功能页面
    path('dashboard/', views.dashboard, name='dashboard'),  # 个性化推荐主页
    path('timeline/', views.timeline, name='timeline'),     # 时序推送页面
    path('search/', views.search, name='search'),           # 搜索页面
    
    # API接口
    path('api/personalized-news/', views.personalized_news_api, name='personalized_news_api'),
    path('api/timeline-news/', views.timeline_news_api, name='timeline_news_api'),
    path('api/search-news/', views.search_news_api, name='search_news_api'),
    path('api/update-tag-visits/', views.update_tag_visits, name='update_tag_visits'),
]