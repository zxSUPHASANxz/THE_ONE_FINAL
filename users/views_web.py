"""
Web Views for User Management
Handles traditional template-based views (not API)
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับ {user.get_full_name() or user.username}!')
            
            # Redirect based on user type
            if user.user_type == 'mechanic':
                return redirect('mechanics:dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    
    return render(request, 'users/login.html')


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number', '')
        user_type = request.POST.get('user_type', 'customer')
        
        # Validation
        if password != password2:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
            return render(request, 'auth/register.html', {'form_data': request.POST})
        
        if not username or len(username) < 3:
            messages.error(request, 'ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร')
            return render(request, 'auth/register.html', {'form_data': request.POST})
        
        if not email:
            messages.error(request, 'กรุณากรอกอีเมล')
            return render(request, 'auth/register.html', {'form_data': request.POST})
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
            return render(request, 'auth/register.html', {'form_data': request.POST})
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'อีเมลนี้ถูกใช้งานแล้ว')
            return render(request, 'auth/register.html', {'form_data': request.POST})
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                user_type=user_type
            )
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับ {username}! สมัครสมาชิกและเข้าสู่ระบบสำเร็จ')
            
            # Redirect based on user type
            if user_type == 'mechanic':
                return redirect('mechanics:dashboard')
            else:
                return redirect('home')
            
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            return render(request, 'auth/register.html', {'form_data': request.POST})
    
    return render(request, 'auth/register.html')


@login_required
def profile_view(request):
    """Display and edit user profile"""
    if request.method == 'POST':
        user = request.user
        
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.address = request.POST.get('address', user.address)
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            user.profile_image = request.FILES['profile_image']
        
        try:
            user.save()
            messages.success(request, 'อัปเดตโปรไฟล์สำเร็จ!')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
        
        return redirect('users:profile_web')
    
    # Query user's motorcycles for profile display
    from booking.models import Motorcycle
    motorcycles = Motorcycle.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'users/profile.html', {
        'user': request.user,
        'motorcycles': motorcycles
    })


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'ออกจากระบบเรียบร้อย')
    return redirect('home')
