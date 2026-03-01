import os
import logging

import google.generativeai as genai
from django.contrib import admin, messages
from django.utils.html import format_html
from dotenv import load_dotenv

from .models import ChatMessage, ChatSession, Knowbase, KnowbaseEmbedQueue

load_dotenv()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Gemini Embedding Helper
# ══════════════════════════════════════════════════════════════════════════════
_GEMINI_CONFIGURED = False


def _configure_genai():
    """ตั้งค่า Gemini API Key ครั้งเดียวต่อ process (lazy init)"""
    global _GEMINI_CONFIGURED
    if not _GEMINI_CONFIGURED:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY ไม่พบใน .env — กรุณาตรวจสอบไฟล์ .env")
        genai.configure(api_key=api_key)
        _GEMINI_CONFIGURED = True


def generate_embedding(text: str) -> list | None:
    """
    ส่งข้อความไปยัง Google Gemini และรับตัวเลขเวกเตอร์ 3072 มิติกลับมา
    คืนค่า list[float] เมื่อสำเร็จ หรือ None เมื่อเกิดข้อผิดพลาด
    """
    try:
        _configure_genai()
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
        )
        return result["embedding"]
    except Exception as exc:
        logger.error("Gemini embedding error: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Shared Custom Action (ใช้ร่วมกันทั้ง KnowbaseAdmin และ KnowbaseEmbedQueueAdmin)
# ══════════════════════════════════════════════════════════════════════════════
@admin.action(description="🧮 สร้าง Embedding สำหรับรายการที่เลือก (เฉพาะที่ยังไม่มี)")
def action_generate_embeddings(modeladmin, request, queryset):
    """
    Custom Action:
    - กรองเฉพาะ record ที่ embedding=NULL ก่อนเสมอ (ไม่ยิง API ซ้ำ)
    - เมื่อสำเร็จ: บันทึก embedding → record หายออกจาก Queue อัตโนมัติ
    - เมื่อล้มเหลว: ไม่บันทึกอะไร → record ยังอยู่ใน Queue ให้ retry
    """
    targets = queryset.filter(embedding__isnull=True)
    if not targets.exists():
        modeladmin.message_user(
            request,
            "รายการที่เลือกมี Embedding ครบแล้ว ✅ ไม่จำเป็นต้องทำซ้ำ",
            messages.WARNING,
        )
        return

    ok = 0
    fail = 0
    for obj in targets:
        text = f"{obj.title}\n{obj.content[:2000]}"
        vec = generate_embedding(text)
        if vec:
            obj.embedding = vec
            obj.save(update_fields=["embedding"])
            ok += 1
        else:
            fail += 1

    if ok:
        modeladmin.message_user(
            request,
            f"✅ สร้าง Embedding สำเร็จ {ok} รายการ",
            messages.SUCCESS,
        )
    if fail:
        modeladmin.message_user(
            request,
            f"❌ สร้างไม่สำเร็จ {fail} รายการ — ตรวจสอบ GEMINI_API_KEY หรือโควตา API",
            messages.ERROR,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Chat Session Admin
# ══════════════════════════════════════════════════════════════════════════════
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("session_id", "user", "is_active", "started_at", "ended_at")
    list_filter = ("is_active", "started_at")
    search_fields = ("session_id", "user__username")
    readonly_fields = ("started_at",)


# ══════════════════════════════════════════════════════════════════════════════
# Chat Message Admin
# ══════════════════════════════════════════════════════════════════════════════
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "sender", "message_preview", "created_at")
    list_filter = ("sender", "created_at")
    search_fields = ("message", "session__session_id")
    readonly_fields = ("created_at",)

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = "ข้อความ"


# ══════════════════════════════════════════════════════════════════════════════
# Knowbase Admin (หน้าหลักจัดการฐานความรู้ทั้งหมด)
# ══════════════════════════════════════════════════════════════════════════════
@admin.register(Knowbase)
class KnowbaseAdmin(admin.ModelAdmin):
    """
    หน้าหลักสำหรับดูและแก้ไขฐานความรู้ทั้งหมด

    วิธีที่ 1 — Auto-embed เมื่อกด Save:
      - เพิ่มข้อมูลใหม่ → สร้าง Embedding ให้อัตโนมัติทันที
      - แก้ไข title/content ของรายการเดิม → สร้าง Embedding ใหม่อัตโนมัติ
      - แก้ไขฟิลด์อื่น (เช่น brand, category) → ไม่ยิง API (ประหยัดโควตา)

    วิธีที่ 2 — Action สร้าง Embedding ทีละหลายรายการ:
      - เลือกรายการที่ยังไม่มี Embedding แล้วกด Action ได้เลย
    """
    list_display = (
        "title", "brand", "model", "source", "category",
        "embedding_status", "is_active", "created_at",
    )
    list_filter = ("source", "category", "brand", "is_active")
    search_fields = ("title", "content", "brand", "model")
    # embedding_status แสดงในหน้า readonly — ไม่ให้คนพิมพ์ตัวเลข 3072 มิติด้วยมือ
    readonly_fields = ("embedding_status", "created_at", "updated_at")
    exclude = ("embedding",)   # ซ่อน field เวกเตอร์ดิบออกจากฟอร์ม
    list_per_page = 25
    actions = [action_generate_embeddings]

    # ── คอลัมน์แสดงสถานะ Embedding ─────────────────────────────────────────
    @admin.display(description="Embedding", ordering="embedding")
    def embedding_status(self, obj):
        if obj.embedding is not None:
            return format_html(
                '<span style="color:#2e7d32;font-weight:bold">✅ มีแล้ว</span>'
            )
        return format_html(
            '<span style="color:#c62828;font-weight:bold">❌ ยังไม่มี</span>'
        )

    # ── Auto-embed เมื่อกด Save (วิธีที่ 1) ─────────────────────────────────
    def save_model(self, request, obj, form, change):
        """
        Logic การตัดสินใจยิง API:
          - record ใหม่ (change=False)         → สร้าง Embedding เสมอ
          - record เดิม + แก้ไข title/content  → สร้าง Embedding ใหม่
          - record เดิม + แก้ไขฟิลด์อื่นๆ     → ข้ามการยิง API (ประหยัดโควตา)
        """
        should_embed = (
            not change  # record ใหม่
            or (change and ("content" in form.changed_data or "title" in form.changed_data))
        )

        if should_embed and obj.content:
            text = f"{obj.title}\n{obj.content[:2000]}"
            vec = generate_embedding(text)
            if vec:
                obj.embedding = vec
                self.message_user(
                    request,
                    "✅ สร้าง Embedding อัตโนมัติสำเร็จ — ข้อมูลพร้อมใช้งานกับ n8n แล้ว",
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    "⚠️ บันทึกข้อมูลสำเร็จ แต่สร้าง Embedding ไม่ได้ "
                    "(ตรวจสอบ GEMINI_API_KEY หรือโควตา) — "
                    "สามารถสร้างทีหลังได้ที่เมนู 'จัดการ Embedding'",
                    messages.WARNING,
                )

        super().save_model(request, obj, form, change)


# ══════════════════════════════════════════════════════════════════════════════
# Embedding Queue Admin (หน้าคิวรอสร้าง Embedding)
# ══════════════════════════════════════════════════════════════════════════════
@admin.register(KnowbaseEmbedQueue)
class KnowbaseEmbedQueueAdmin(admin.ModelAdmin):
    """
    หน้าเฉพาะสำหรับจัดการ record ที่ยังไม่มี Embedding

    การทำงาน:
      - แสดงเฉพาะ record ที่ embedding=NULL
      - จำกัด 10 รายการต่อหน้า
      - เลือก record แล้วกด Action 'สร้าง Embedding' ได้เลย
      - เมื่อสำเร็จ: record หายออกจากหน้านี้อัตโนมัติ
      - เมื่อล้มเหลว: record ยังอยู่ให้ retry ใหม่
    """
    list_display = ("title", "brand", "model", "source", "category", "created_at")
    list_filter = ("source", "category", "brand")
    search_fields = ("title", "content", "brand", "model")
    exclude = ("embedding",)
    list_per_page = 10   # จำกัด 10 ต่อหน้า ป้องกันโควตา Gemini หมดต่อครั้ง
    actions = [action_generate_embeddings]

    def has_add_permission(self, request):
        """ปิดการเพิ่มข้อมูลจากหน้านี้ — ให้เพิ่มผ่านหน้า Knowbase หลักเท่านั้น"""
        return False

    def get_queryset(self, request):
        """Filter เฉพาะ record ที่ยังไม่มี Embedding เรียงจากเก่าสุดขึ้นมา"""
        return (
            super()
            .get_queryset(request)
            .filter(embedding__isnull=True)
            .order_by("created_at")
        )

