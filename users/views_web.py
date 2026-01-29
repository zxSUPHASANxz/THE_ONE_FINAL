"""
Web Views for User Management
Handles traditional template-based views (not API)
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required

from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
from mechanics.models import MechanicProfile


def direct_password_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not email or not new_password or not confirm_password:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return render(request, 'users/password_reset/direct_reset.html')
            
        if new_password != confirm_password:
            messages.error(request, 'รหัสผ่านไม่ตรงกัน')
            return render(request, 'users/password_reset/direct_reset.html')
            
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            messages.success(request, 'เปลี่ยนรหัสผ่านสำเร็จ! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่')
            return redirect('users:login')
        except User.DoesNotExist:
            messages.error(request, 'ไม่พบผู้ใช้ที่มีอีเมลนี้ในระบบ')
            return render(request, 'users/password_reset/direct_reset.html')
            
    return render(request, 'users/password_reset/direct_reset.html')


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
            return render(request, 'users/register.html', {'form_data': request.POST})
        
        if not username or len(username) < 3:
            messages.error(request, 'ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร')
            return render(request, 'users/register.html', {'form_data': request.POST})
        
        if not email:
            messages.error(request, 'กรุณากรอกอีเมล')
            return render(request, 'users/register.html', {'form_data': request.POST})
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
            return render(request, 'users/register.html', {'form_data': request.POST})
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'อีเมลนี้ถูกใช้งานแล้ว')
            return render(request, 'users/register.html', {'form_data': request.POST})
        
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

            # If registering as mechanic, create a MechanicProfile with optional fields
            if user_type == 'mechanic':
                shop_address = request.POST.get('shop_address', '')
                qualification = request.POST.get('qualification', '')
                specialization = request.POST.get('specialization', 'all')
                try:
                    years_of_experience = int(request.POST.get('years_of_experience', 0))
                except Exception:
                    years_of_experience = 0

                profile = MechanicProfile.objects.create(
                    user=user,
                    specialization=specialization,
                    years_of_experience=years_of_experience,
                    qualification=qualification,
                    shop_address=shop_address
                )

                # Handle uploaded files (optional)
                if 'shop_photo' in request.FILES:
                    profile.shop_photo = request.FILES['shop_photo']
                if 'qualification_file' in request.FILES:
                    profile.qualification_file = request.FILES['qualification_file']
                if 'license_file' in request.FILES:
                    profile.license_file = request.FILES['license_file']

                profile.save()

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
            return render(request, 'users/register.html', {'form_data': request.POST})
    
    return render(request, 'users/register.html')


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
