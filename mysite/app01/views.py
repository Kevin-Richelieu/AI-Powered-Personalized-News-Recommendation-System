
from .decorators import login_required_custom
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection
import json

# ===== 认证相关视图 =====
def user_login(request):
    """用户登录 - 使用原始SQL验证"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # 使用原始SQL查询验证用户
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT UserID, UserName, PassWord, Major FROM User WHERE UserName = %s", 
                [username]
            )
            row = cursor.fetchone()
            
            if row:
                user_id, db_username, db_password, major = row
                # 直接比较密码（因为您的数据库中是明文存储）
                if password == db_password:
                    # 登录成功，将用户信息存入session
                    request.session['user_id'] = user_id
                    request.session['username'] = db_username
                    request.session['user_major'] = major
                    request.session['is_authenticated'] = True
                    
                    messages.success(request, f'欢迎回来，{db_username}！')
                    return redirect('dashboard')
                else:
                    messages.error(request, '密码错误')
            else:
                messages.error(request, '用户不存在')
    
    return render(request, 'app01/login.html')

def user_logout(request):
    """用户登出"""
    # 清除session
    request.session.flush()
    messages.success(request, '您已成功退出登录')
    return redirect('home')

def user_register(request):
    """用户注册"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        major = request.POST.get('major', '')
        
        if password != confirm_password:
            messages.error(request, '两次输入的密码不一致')
            return render(request, 'app01/register.html')
        
        # 检查用户名是否已存在
        with connection.cursor() as cursor:
            cursor.execute("SELECT UserID FROM User WHERE UserName = %s", [username])
            if cursor.fetchone():
                messages.error(request, '用户名已存在')
                return render(request, 'app01/register.html')
            
            # 插入新用户
            cursor.execute(
                "INSERT INTO User (UserName, PassWord, Major) VALUES (%s, %s, %s)",
                [username, password, major]
            )
            connection.commit()
            
            messages.success(request, '注册成功，请登录')
            return redirect('login')
    
    return render(request, 'app01/register.html')

def home(request):
    """首页"""
    return render(request, 'app01/home.html')

# ===== 主要功能视图 =====
@login_required_custom
def dashboard(request):
    """用户仪表板"""
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    
    # 获取个性化新闻
    personalized_news = get_personalized_news(user_id)
    
    # 获取用户兴趣标签
    user_tags = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.TagName, SUM(ut.VisitTimes) as VisitCount
            FROM User_Tag ut
            LEFT JOIN Tag t ON ut.TagID = t.TagID
            WHERE ut.UserID = %s
            GROUP BY ut.TagID, t.TagName
            ORDER BY VisitCount DESC
        """, [user_id])
        user_tags = cursor.fetchall()  # 结果为(TagName, VisitCount)的元组列表
    
    context = {
        'username': username,
        'personalized_news': personalized_news,
        'user_tags': user_tags  # 传递用户标签到模板
    }
    return render(request, 'app01/dashboard.html', context)

@login_required_custom
def timeline(request):
    """时序推送页面"""
    user_id = request.session.get('user_id')  # 获取当前用户ID
    username = request.session.get('username')
    
    # 获取用户兴趣标签（与dashboard使用相同逻辑）
    user_tags = []
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT t.TagName, SUM(ut.VisitTimes) as VisitCount
            FROM User_Tag ut
            LEFT JOIN Tag t ON ut.TagID = t.TagID
            WHERE ut.UserID = %s
            GROUP BY ut.TagID, t.TagName
            ORDER BY VisitCount DESC
        """, [user_id])
        user_tags = cursor.fetchall()  # 结果为(TagName, VisitCount)的元组列表
    
    context = {
        'username': username,
        'user_tags': user_tags  # 传递标签数据到模板
    }
    return render(request, 'app01/timeline.html', context)

@login_required_custom
def search(request):
    """搜索页面"""
    username = request.session.get('username')
    query = request.GET.get('q', '')
    
    context = {
        'username': username,
        'query': query,
        'results': search_news(query) if query else [],
    }
    return render(request, 'app01/search.html', context)

# ===== API接口视图 =====
@login_required_custom
def personalized_news_api(request):
    """个性化新闻推荐API"""
    try:
        # 从session获取用户ID
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({
                'status': 'error',
                'message': '用户未登录',
                'news': []
            }, status=401)
        
        print(f"为用户 {user_id} 获取个性化推荐")  # 调试信息
        
        # 调用个性化推荐函数
        personalized_news = get_personalized_news(user_id)
        
        return JsonResponse({
            'news': personalized_news,
            'status': 'success',
            'count': len(personalized_news)
        })
        
    except Exception as e:
        print(f"Error in personalized_news_api: {e}")
        return JsonResponse({
            'status': 'error',
            'message': '服务器内部错误',
            'news': []
        }, status=500)

@login_required_custom
def timeline_news_api(request):
    """时序新闻API - 按时间顺序返回新闻"""
    try:
        # 获取查询参数
        range_filter = request.GET.get('range', 'all')  # all, today, week, month
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 构建基础查询
        base_query = """
        SELECT 
            n.NewsID,
            n.PublishDate,
            n.URL,
            n.Summary,
            GROUP_CONCAT(DISTINCT t.TagName ORDER BY t.TagName SEPARATOR ', ') AS TagNames,
            COUNT(DISTINCT t.TagID) AS TagCount
        FROM News n
        LEFT JOIN News_Tag nt ON n.NewsID = nt.NewsID
        LEFT JOIN Tag t ON nt.TagID = t.TagID
        """
        
        # 添加时间范围筛选
        where_conditions = []
        params = []
        
        if range_filter == 'today':
            where_conditions.append("n.PublishDate = CURDATE()")
        elif range_filter == 'week':
            where_conditions.append("n.PublishDate >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
        elif range_filter == 'month':
            where_conditions.append("n.PublishDate >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)")
        # 'all' 不添加时间条件
        
        # 构建完整的WHERE子句
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # 完整的查询
        query = f"""
        {base_query}
        {where_clause}
        GROUP BY n.NewsID, n.PublishDate, n.URL, n.Summary
        ORDER BY n.PublishDate DESC, n.NewsID DESC
        LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        
        # 执行查询
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        # 获取总数（用于分页）
        count_query = f"""
        SELECT COUNT(DISTINCT n.NewsID)
        FROM News n
        {where_clause}
        """
        
        with connection.cursor() as cursor:
            if where_conditions:
                cursor.execute(count_query, params[:-2])  # 去掉LIMIT和OFFSET参数
            else:
                cursor.execute(count_query)
            total_count = cursor.fetchone()[0]
        
        # 格式化日期（如果需要）
        for news in results:
            if news['PublishDate']:
                # 将日期转换为更友好的格式
                news['FormattedDate'] = news['PublishDate'].strftime('%Y年%m月%d日')
        
        return JsonResponse({
            'news': results,
            'status': 'success',
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': page * limit < total_count,
                'has_prev': page > 1
            },
            'range': range_filter
        })
        
    except Exception as e:
        import traceback
        print(f"Error in timeline_news_api: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            'status': 'error',
            'message': '服务器内部错误',
            'news': []
        }, status=500)

@login_required
def search_news_api(request):
    """搜索新闻API"""
    query = request.GET.get('q', '')
    # 这里您需要实现搜索逻辑
    data = {
        'results': [],
        'query': query,
        'status': 'success'
    }
    return JsonResponse(data)

@login_required_custom 
def update_tag_visits(request):#点击记数
    """更新用户对新闻标签的访问次数"""
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            news_id = request.POST.get('news_id')  # 获取被点击的新闻ID
            
            if not user_id or not news_id:
                return JsonResponse({
                    'status': 'error',
                    'message': '参数不完整'
                }, status=400)
            
            # 1. 获取该新闻对应的所有标签ID
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT TagID FROM News_Tag WHERE NewsID = %s
                """, [news_id])
                tag_ids = [row[0] for row in cursor.fetchall()]
                
                if not tag_ids:
                    return JsonResponse({
                        'status': 'success',
                        'message': '该新闻无标签，无需更新'
                    })
            
            # 2. 批量更新User_Tag表（存在则+1，不存在则创建）
            with connection.cursor() as cursor:
                for tag_id in tag_ids:
                    # 使用INSERT ... ON DUPLICATE KEY UPDATE语法
                    # 需确保User_Tag表有(UserID, TagID)的唯一索引
                    cursor.execute("""
                        INSERT INTO User_Tag (UserID, TagID, VisitTimes)
                        VALUES (%s, %s, 1)
                        ON DUPLICATE KEY UPDATE VisitTimes = VisitTimes + 1
                    """, [user_id, tag_id])
                connection.commit()
            
            return JsonResponse({
                'status': 'success',
                'message': '标签访问次数已更新'
            })
            
        except Exception as e:
            connection.rollback()
            print(f"更新标签访问次数错误: {e}")
            return JsonResponse({
                'status': 'error',
                'message': '服务器内部错误'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': '不支持的请求方法'
    }, status=405)

# ===== 辅助函数 =====
def get_personalized_news(user_id):
    """获取个性化新闻 - 基于用户标签访问频率"""
    # 1. 获取用户访问频率最高的前5个标签
    with connection.cursor() as cursor:
        # 查询用户访问的标签及次数，按访问次数降序排列
        cursor.execute("""
            SELECT ut.TagID, t.TagName, SUM(ut.VisitTimes) as TotalVisits
            FROM User_Tag ut
            LEFT JOIN Tag t ON ut.TagID = t.TagID
            WHERE ut.UserID = %s
            GROUP BY ut.TagID, t.TagName
            ORDER BY TotalVisits DESC
            LIMIT 5
        """, [user_id])
        
        # 获取标签信息
        user_tags = cursor.fetchall()
        if not user_tags:
            print(f"用户 {user_id} 没有标签数据，无法推荐新闻")  # 调试信息
            return []  # 如果没有用户标签，返回空列表
        
        # 提取标签ID列表
        tag_ids = [str(tag[0]) for tag in user_tags]
        tag_id_params = ', '.join(['%s'] * len(tag_ids))

        print(f"用户 {user_id} 的标签IDs: {tag_ids}")  # 调试信息
        
        # 2. 根据标签查询相关新闻，按匹配标签数和发布时间排序
        query = f"""
            SELECT 
                n.NewsID,
                n.PublishDate,
                n.URL,
                n.Summary,
                GROUP_CONCAT(DISTINCT t.TagName ORDER BY t.TagName SEPARATOR ', ') AS TagNames,
                COUNT(DISTINCT t.TagID) AS MatchedTags,
                COUNT(DISTINCT t.TagID) / {len(tag_ids)} AS RelevanceScore
            FROM News n
            LEFT JOIN News_Tag nt ON n.NewsID = nt.NewsID
            LEFT JOIN Tag t ON nt.TagID = t.TagID
            WHERE nt.TagID IN ({tag_id_params})
            GROUP BY n.NewsID, n.PublishDate, n.URL, n.Summary
            ORDER BY MatchedTags DESC, n.PublishDate DESC
            LIMIT 20
        """
        
        cursor.execute(query, tag_ids)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        print(f"为用户 {user_id} 推荐了 {len(results)} 条新闻")  # 调试信息
        
        # 格式化日期
        for news in results:
            if news['PublishDate']:
                news['FormattedDate'] = news['PublishDate'].strftime('%Y年%m月%d日')
        
        #print(f"推荐结果: {results}")  # 调试信息

        return results

def search_news(query):
    """搜索新闻（您来实现具体逻辑）"""
    # 实现搜索功能
    return []