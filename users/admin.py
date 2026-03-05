from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'user_type', 'phone_number', 'is_staff', 'created_at')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ข้อมูลเพิ่มเติม', {'fields': ('user_type', 'phone_number', 'address', 'profile_image')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('ข้อมูลเพิ่มเติม', {'fields': ('user_type', 'phone_number')}),
    )


class NotificationAdminForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False
        self.fields['user'].empty_label = 'ผู้ใช้ทั้งหมด'
        self.fields['user'].help_text = 'เลือกผู้ใช้รายบุคคล หรือเลือก "ผู้ใช้ทั้งหมด"'

    def clean(self):
        cleaned_data = super().clean()
        if self.instance and self.instance.pk and not cleaned_data.get('user'):
            raise forms.ValidationError('การแก้ไขรายการเดิมต้องระบุผู้ใช้')
        return cleaned_data


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    form = NotificationAdminForm
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        selected_user = form.cleaned_data.get('user')

        if not change and selected_user is None:
            target_users = User.objects.filter(is_active=True).only('id')
            notifications = [
                Notification(
                    user=target_user,
                    notification_type=form.cleaned_data['notification_type'],
                    title=form.cleaned_data['title'],
                    message=form.cleaned_data['message'],
                    booking=form.cleaned_data.get('booking'),
                    is_read=form.cleaned_data.get('is_read', False),
                )
                for target_user in target_users
            ]
            Notification.objects.bulk_create(notifications, batch_size=500)
            self.message_user(request, f'ส่งแจ้งเตือนไปยังผู้ใช้ทั้งหมดแล้ว {len(notifications)} ราย')
            return

        super().save_model(request, obj, form, change)
