"""
Web Views for Mechanics
Handles template-based views (not API)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import MechanicProfile, WorkQueue, Review
from booking.models import Booking


@login_required
def dashboard_view(request):
    """Mechanic dashboard with work queue"""
    # Check if user is a mechanic
    if request.user.user_type != 'mechanic':
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงหน้านี้')
        return redirect('home')
    
    # Get or create mechanic profile
    profile, created = MechanicProfile.objects.get_or_create(user=request.user)
    
    # Get work queues (include cancelled bookings)
    work_queues = WorkQueue.objects.filter(
        mechanic=request.user
    ).select_related('booking', 'booking__motorcycle', 'booking__customer').order_by('-assigned_at')
    
    # Count by status
    pending_count = work_queues.filter(status='pending', booking__status='pending').count()
    accepted_count = work_queues.filter(status='accepted').count()
    confirmed_count = work_queues.filter(status='accepted', booking__status='confirmed').count()
    rejected_count = work_queues.filter(status='rejected').count()
    cancelled_by_customer_count = work_queues.filter(booking__status='cancelled').count()
    
    # Count jobs taken by other mechanics (booking confirmed but not by this mechanic)
    taken_by_others_count = work_queues.filter(
        status='pending',
        booking__status='confirmed'
    ).exclude(booking__mechanic=request.user).count()
    
    # Get bookings in progress
    in_progress_bookings = Booking.objects.filter(
        mechanic=request.user,
        status='in_progress'
    ).select_related('motorcycle', 'customer')
    
    # Get completed bookings count
    completed_count = Booking.objects.filter(
        mechanic=request.user,
        status='completed'
    ).count()
    
    context = {
        'profile': profile,
        'work_queues': work_queues,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'cancelled_by_customer_count': cancelled_by_customer_count,
        'taken_by_others_count': taken_by_others_count,
        'in_progress_count': in_progress_bookings.count(),
        'completed_count': completed_count,
        'in_progress_bookings': in_progress_bookings,
        'today': timezone.now()
    }
    
    return render(request, 'mechanics/dashboard.html', context)


@login_required
def accept_work_view(request, pk):
    """Accept a work queue"""
    if request.user.user_type != 'mechanic':
        messages.error(request, 'คุณไม่มีสิทธิ์ทำรายการนี้')
        return redirect('home')
    
    work_queue = get_object_or_404(WorkQueue, pk=pk, mechanic=request.user)
    
    if work_queue.status == 'pending':
        # Check if booking is still available (not taken by another mechanic)
        booking = work_queue.booking
        if booking.status != 'pending':
            messages.warning(request, f'งานนี้มีช่างคนอื่นรับไปแล้ว')
            return redirect('mechanics:dashboard')
        
        work_queue.status = 'accepted'
        work_queue.responded_at = timezone.now()
        work_queue.save()
        
        # Update booking
        booking.mechanic = request.user
        booking.status = 'confirmed'
        booking.save()
        
        # Update mechanic profile
        profile = request.user.mechanic_profile
        profile.total_jobs += 1
        profile.save()
        
        # Notify other mechanics that this work was taken
        from users.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get motorcycle info
        motorcycle_text = "รถจักรยานยนต์"
        try:
            if booking.motorcycle:
                motorcycle_text = f"{booking.motorcycle.brand} {booking.motorcycle.model}"
        except Exception:
            pass
        
        # Find all other mechanics who might have seen this booking
        other_mechanics = User.objects.filter(
            user_type='mechanic',
            mechanic_profile__is_available=True
        ).exclude(id=request.user.id)
        
        for mech in other_mechanics:
            Notification.objects.create(
                user=mech,
                booking=booking,
                notification_type='work_taken_by_other',
                title='❌ งานถูกรับไปแล้ว',
                message=f'การจอง #{booking.id} ({motorcycle_text}) มีช่างคนอื่นรับไปแล้ว'
            )
        
        messages.success(request, f'รับงานเรียบร้อย - การจอง #{booking.id}')
    else:
        messages.warning(request, 'งานนี้ได้รับการตอบกลับแล้ว')
    
    return redirect('mechanics:dashboard')


@login_required
def reject_work_view(request, pk):
    """Reject a work queue"""
    if request.user.user_type != 'mechanic':
        messages.error(request, 'คุณไม่มีสิทธิ์ทำรายการนี้')
        return redirect('home')
    
    work_queue = get_object_or_404(WorkQueue, pk=pk, mechanic=request.user)
    
    if work_queue.status == 'pending':
        work_queue.status = 'rejected'
        work_queue.responded_at = timezone.now()
        work_queue.save()
        
        messages.info(request, f'ปฏิเสธงาน - การจอง #{work_queue.booking.id}')
    else:
        messages.warning(request, 'งานนี้ได้รับการตอบกลับแล้ว')
    
    return redirect('mechanics:dashboard')


@login_required
def start_work_view(request, booking_id):
    """Start working on a booking"""
    if request.user.user_type != 'mechanic':
        messages.error(request, 'คุณไม่มีสิทธิ์ทำรายการนี้')
        return redirect('home')
    
    booking = get_object_or_404(
        Booking, 
        id=booking_id, 
        mechanic=request.user,
        status='confirmed'
    )
    
    booking.status = 'in_progress'
    booking.save()
    
    messages.success(request, f'เริ่มงาน - การจอง #{booking.id}')
    return redirect('mechanics:dashboard')


@login_required
def complete_work_view(request, booking_id):
    """Mark booking as completed"""
    if request.user.user_type != 'mechanic':
        messages.error(request, 'คุณไม่มีสิทธิ์ทำรายการนี้')
        return redirect('home')
    
    booking = get_object_or_404(
        Booking, 
        id=booking_id, 
        mechanic=request.user,
        status='in_progress'
    )
    
    booking.status = 'completed'
    booking.save()
    
    messages.success(request, f'ทำงานเสร็จสิ้น - การจอง #{booking.id}')
    return redirect('mechanics:dashboard')
