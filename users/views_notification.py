from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from users.models import Notification
from users.serializers_notification import NotificationSerializer
import json


@login_required
@require_http_methods(["GET"])
def get_notifications(request):
    """Get all notifications for current user (Both customers and mechanics)"""
    notifications = Notification.objects.filter(user=request.user)[:20]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    serializer = NotificationSerializer(notifications, many=True)
    
    return JsonResponse({
        'notifications': serializer.data,
        'unread_count': unread_count
    })


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True, 'message': 'อ่านแล้ว'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'ไม่พบการแจ้งเตือน'}, status=404)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True, 'message': 'อ่านทั้งหมดแล้ว'})


@login_required
@require_http_methods(["DELETE"])
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return JsonResponse({'success': True, 'message': 'ลบการแจ้งเตือนแล้ว'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'ไม่พบการแจ้งเตือน'}, status=404)
