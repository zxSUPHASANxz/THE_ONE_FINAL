import os
import logging
import csv
import io
import json
from urllib.parse import urlencode

import google.generativeai as genai
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from dotenv import load_dotenv

from .models import Knowbase, KnowbaseEmbedQueue

load_dotenv()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Gemini Embedding Helper
# ══════════════════════════════════════════════════════════════════════════════
_GEMINI_CONFIGURED = False
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_CHUNK_SIZE = 1800
DEFAULT_CHUNK_OVERLAP = 200
MAX_EMBED_CHUNKS = 8


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    สกัดข้อความจากไฟล์ที่อัปโหลดเพื่อใช้เป็น content สำหรับ embedding
    รองรับ: txt, md, csv, json, pdf (ถ้าติดตั้ง pypdf)
    """
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"ไฟล์ใหญ่เกินกำหนด ({max_mb} MB)")

    file_name = (uploaded_file.name or "").lower()
    extension = os.path.splitext(file_name)[1]
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)

    if extension in (".txt", ".md", ".log"):
        return raw_bytes.decode("utf-8", errors="ignore").strip()

    if extension == ".csv":
        text = raw_bytes.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        lines = [" | ".join(row) for row in reader]
        return "\n".join(lines).strip()

    if extension == ".json":
        text = raw_bytes.decode("utf-8", errors="ignore")
        try:
            obj = json.loads(text)
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            return text.strip()

    if extension == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            extracted = []
            for page in reader.pages:
                extracted.append(page.extract_text() or "")
            return "\n".join(extracted).strip()
        except Exception as exc:
            raise ValidationError(
                f"อ่านไฟล์ PDF ไม่สำเร็จ: {exc}. กรุณาติดตั้ง pypdf หรือใช้ไฟล์ .txt/.md/.csv/.json"
            )

    raise ValidationError("รองรับเฉพาะไฟล์ .txt, .md, .csv, .json, .pdf")


def _configure_genai(api_key_override: str | None = None):
    """ตั้งค่า Gemini API Key (รองรับ key จากฟอร์มแบบ override)"""
    global _GEMINI_CONFIGURED
    if api_key_override:
        genai.configure(api_key=api_key_override)
        return

    if not _GEMINI_CONFIGURED:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY ไม่พบใน .env — กรุณาตรวจสอบไฟล์ .env")
        genai.configure(api_key=api_key)
        _GEMINI_CONFIGURED = True


def generate_embedding(text: str, api_key: str | None = None) -> list | None:
    """
    ส่งข้อความไปยัง Google Gemini และรับตัวเลขเวกเตอร์ 3072 มิติกลับมา
    คืนค่า list[float] เมื่อสำเร็จ หรือ None เมื่อเกิดข้อผิดพลาด
    """
    try:
        _configure_genai(api_key_override=api_key)
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
        )
        return result["embedding"]
    except Exception as exc:
        logger.error("Gemini embedding error: %s", exc)
        return None


def split_text_into_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    """ตัดข้อความยาวเป็นหลาย chunk พร้อม overlap เล็กน้อย"""
    clean_text = (text or "").strip()
    if not clean_text:
        return []

    if len(clean_text) <= chunk_size:
        return [clean_text]

    chunks = []
    step = max(1, chunk_size - overlap)
    start = 0
    while start < len(clean_text):
        end = start + chunk_size
        chunks.append(clean_text[start:end])
        if end >= len(clean_text):
            break
        start += step
    return chunks


def average_vectors(vectors: list[list[float]]) -> list[float] | None:
    """เฉลี่ยเวกเตอร์หลายก้อนให้เหลือเวกเตอร์เดียว"""
    if not vectors:
        return None

    dimensions = len(vectors[0])
    sums = [0.0] * dimensions
    valid_count = 0

    for vector in vectors:
        if len(vector) != dimensions:
            continue
        for index, value in enumerate(vector):
            sums[index] += float(value)
        valid_count += 1

    if valid_count == 0:
        return None

    return [value / valid_count for value in sums]


def generate_embedding_with_chunking(text: str, api_key: str | None = None) -> list[float] | None:
    """
    ข้อความสั้น: embedding ปกติ
    ข้อความยาว: แบ่ง chunk แล้ว average เวกเตอร์
    """
    chunks = split_text_into_chunks(text)
    if not chunks:
        return None

    if len(chunks) == 1:
        return generate_embedding(chunks[0], api_key=api_key)

    selected_chunks = chunks[:MAX_EMBED_CHUNKS]
    vectors = []
    for chunk in selected_chunks:
        vector = generate_embedding(chunk, api_key=api_key)
        if vector:
            vectors.append(vector)

    if len(chunks) > MAX_EMBED_CHUNKS:
        logger.warning(
            "Long content truncated by chunk limit: total_chunks=%s used_chunks=%s",
            len(chunks),
            MAX_EMBED_CHUNKS,
        )

    return average_vectors(vectors)


# ══════════════════════════════════════════════════════════════════════════════
# Shared Custom Action (ใช้ร่วมกันทั้ง KnowbaseAdmin และ KnowbaseEmbedQueueAdmin)
# ══════════════════════════════════════════════════════════════════════════════
@admin.action(description="สร้าง Embedding สำหรับรายการที่เลือก (เฉพาะที่ยังไม่มี)")
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
        text = f"{obj.title}\n{obj.content}"
        vec = generate_embedding_with_chunking(text)
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
# Knowbase Admin (หน้าหลักจัดการฐานความรู้ทั้งหมด)
# ══════════════════════════════════════════════════════════════════════════════
class KnowbaseAdminForm(forms.ModelForm):
    api_key = forms.CharField(
        label="API Key (Gemini)",
        required=False,
        widget=forms.PasswordInput(render_value=True, attrs={
            "autocomplete": "off",
            "placeholder": "ใส่ API key เฉพาะครั้งนี้ (ถ้าไม่ใส่จะใช้ .env)",
        }),
        help_text="ใช้เฉพาะรอบที่กดบันทึกครั้งนี้เท่านั้น",
    )
    upload_file = forms.FileField(
        label="Upload File",
        required=False,
        help_text="อัปโหลดไฟล์เพื่อดึงข้อความเข้า content อัตโนมัติ (รองรับ .txt/.md/.csv/.json/.pdf)",
    )
    extracted_preview = forms.CharField(
        label="Extracted Preview",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "readonly": "readonly"}),
        help_text="ตัวอย่างข้อความที่ดึงได้จากไฟล์ (ตรวจสอบก่อนกดบันทึก)",
    )

    class Meta:
        model = Knowbase
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "content" in self.fields:
            self.fields["content"].required = False
        if "extracted_preview" in self.fields and self.instance and getattr(self.instance, "content", None):
            self.fields["extracted_preview"].initial = self.instance.content[:1000]

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get("content") or "").strip()
        uploaded_file = cleaned_data.get("upload_file")

        if not content and not uploaded_file:
            raise ValidationError("กรุณากรอก Content หรืออัปโหลดไฟล์อย่างน้อย 1 อย่าง")

        if uploaded_file:
            extracted_text = extract_text_from_uploaded_file(uploaded_file)
            if not extracted_text:
                raise ValidationError("ไฟล์ที่อัปโหลดไม่มีข้อความที่อ่านได้")
            if content:
                cleaned_data["content"] = f"{content}\n\n{extracted_text}".strip()
            else:
                cleaned_data["content"] = extracted_text
            cleaned_data["extracted_preview"] = extracted_text[:1000]
        elif content:
            cleaned_data["extracted_preview"] = content[:1000]

        return cleaned_data


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
    form = KnowbaseAdminForm
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

        uploaded_file = form.cleaned_data.get("upload_file")
        if uploaded_file:
            existing_raw_data = obj.raw_data if isinstance(obj.raw_data, dict) else {}
            existing_raw_data.update({
                "upload_file_name": uploaded_file.name,
                "upload_file_size": uploaded_file.size,
                "upload_source": "admin_form",
            })
            obj.raw_data = existing_raw_data

        if should_embed and obj.content:
            text = f"{obj.title}\n{obj.content}"
            api_key_input = (form.cleaned_data.get("api_key") or "").strip()
            vec = generate_embedding_with_chunking(text, api_key=api_key_input or None)
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
    change_list_template = "admin/chatbot/knowbaseembedqueue/change_list.html"

    def has_add_permission(self, request):
        """เปิดปุ่ม + เพิ่ม ใน sidebar เพื่อพาไปหน้า Add Embedding"""
        return True

    def add_view(self, request, form_url="", extra_context=None):
        """เมื่อกด + เพิ่ม ของเมนู Embedding ให้ redirect ไปหน้า Add Embedding"""
        return HttpResponseRedirect(reverse("admin:chatbot_knowbaseembedqueue_add_embedding"))

    def get_urls(self):
        custom_urls = [
            path(
                "add-embedding/",
                self.admin_site.admin_view(self.add_embedding_view),
                name="chatbot_knowbaseembedqueue_add_embedding",
            ),
        ]
        return custom_urls + super().get_urls()

    def add_embedding_view(self, request):
        """
        หน้า Add Embedding:
        - แสดงข้อมูลที่ยังไม่มี embedding ทั้งหมด
        - ให้ผู้ใช้เลือกและกดปุ่ม Embedding
        - จำกัดการเลือกสูงสุด 10 รายการต่อครั้ง
        - สำเร็จ: บันทึก embedding แล้วจะไม่แสดงในหน้านี้อีก
        - ล้มเหลว: ไม่บันทึกและยังแสดงในหน้านี้เหมือนเดิม
        """
        pending_qs = Knowbase.objects.filter(embedding__isnull=True)

        query = request.GET.get("q", "").strip()
        sort = request.GET.get("sort", "created_desc").strip()

        def build_url(search_text: str, sort_value: str):
            params = {}
            if search_text:
                params["q"] = search_text
            if sort_value:
                params["sort"] = sort_value
            if not params:
                return "."
            return f"?{urlencode(params)}"

        def redirect_with_filters(search_text: str, sort_value: str):
            query_string = urlencode({"q": search_text, "sort": sort_value}) if search_text else urlencode({"sort": sort_value})
            if query_string:
                return HttpResponseRedirect(f"{request.path}?{query_string}")
            return HttpResponseRedirect(request.path)

        if query:
            pending_qs = pending_qs.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(brand__icontains=query)
                | Q(model__icontains=query)
                | Q(source__icontains=query)
                | Q(category__icontains=query)
            )

        if sort == "created_desc":
            pending_qs = pending_qs.order_by("-created_at")
        elif sort == "title_asc":
            pending_qs = pending_qs.order_by("title")
        elif sort == "title_desc":
            pending_qs = pending_qs.order_by("-title")
        else:
            sort = "created_desc"
            pending_qs = pending_qs.order_by("-created_at")

        if request.method == "POST":
            selected_ids = request.POST.getlist("selected_ids")
            api_key_input = request.POST.get("api_key", "").strip()
            query = request.POST.get("q", "").strip()
            sort = request.POST.get("sort", "created_desc").strip()

            if not api_key_input and not os.getenv("GEMINI_API_KEY"):
                self.message_user(
                    request,
                    "ไม่พบ API key: กรุณากรอก API key ในฟอร์ม หรือกำหนด GEMINI_API_KEY ใน .env",
                    messages.ERROR,
                )
                return redirect_with_filters(query, sort)

            if not selected_ids:
                self.message_user(
                    request,
                    "กรุณาเลือกรายการที่ต้องการทำ Embedding อย่างน้อย 1 รายการ",
                    messages.WARNING,
                )
                return redirect_with_filters(query, sort)

            if len(selected_ids) > 10:
                self.message_user(
                    request,
                    "อนุญาตให้ทำ Embedding ได้สูงสุด 10 รายการต่อครั้ง",
                    messages.ERROR,
                )
                return redirect_with_filters(query, sort)

            targets = pending_qs.filter(id__in=selected_ids)

            ok = 0
            fail = 0
            for obj in targets:
                text = f"{obj.title}\n{obj.content}"
                vec = generate_embedding_with_chunking(text, api_key=api_key_input or None)
                if vec:
                    obj.embedding = vec
                    obj.save(update_fields=["embedding"])
                    ok += 1
                else:
                    fail += 1

            if ok:
                self.message_user(
                    request,
                    f"✅ สร้าง Embedding สำเร็จ {ok} รายการ",
                    messages.SUCCESS,
                )
            if fail:
                self.message_user(
                    request,
                    f"❌ สร้างไม่สำเร็จ {fail} รายการ รายการที่ล้มเหลวยังคงอยู่ในหน้า Embedding",
                    messages.ERROR,
                )

            return redirect_with_filters(query, sort)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "เพิ่ม Embedding",
            "pending_items": pending_qs,
            "pending_total": pending_qs.count(),
            "search_query": query,
            "sort_key": sort,
            "clear_search_url": build_url("", sort),
            "sort_url_created_asc": build_url(query, "created_asc"),
            "sort_url_created_desc": build_url(query, "created_desc"),
            "sort_url_title_asc": build_url(query, "title_asc"),
            "sort_url_title_desc": build_url(query, "title_desc"),
            "back_url": reverse("admin:chatbot_knowbaseembedqueue_changelist"),
        }
        return render(request, "admin/chatbot/knowbaseembedqueue/add_embedding.html", context)

    def get_queryset(self, request):
        """Filter เฉพาะ record ที่ยังไม่มี Embedding เรียงจากเก่าสุดขึ้นมา"""
        return (
            super()
            .get_queryset(request)
            .filter(embedding__isnull=True)
            .order_by("created_at")
        )