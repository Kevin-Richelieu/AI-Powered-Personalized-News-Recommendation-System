# app01/decorators.py
from django.shortcuts import redirect
from functools import wraps

def login_required_custom(view_func):
    """自定义登录验证装饰器"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view