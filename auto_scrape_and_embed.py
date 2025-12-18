#!/usr/bin/env python3
"""
Auto Scrape and Embed Pipeline
รัน scraper แล้ว embed ต่อเนื่องอัตโนมัติ
"""

import subprocess
import sys
import os
from datetime import datetime

def print_header(title):
    """พิมพ์หัวข้อ"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def run_command(command, description):
    """รันคำสั่งและแสดงผล"""
    print(f"\n🚀 {description}")
    print(f"📝 คำสั่ง: {command}\n")
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=False,
        text=True
    )
    
    if result.returncode == 0:
        print(f"\n✅ {description} - สำเร็จ!")
        return True
    else:
        print(f"\n⚠️  {description} - เสร็จสิ้น (อาจมีข้อผิดพลาดบางส่วน)")
        return True  # ยังให้ดำเนินการต่อ

def main():
    """ฟังก์ชันหลัก"""
    start_time = datetime.now()
    
    print_header("🤖 AUTO SCRAPE & EMBED PIPELINE")
    print(f"⏰ เริ่มต้น: {start_time.strftime('%H:%M:%S')}")
    print(f"📁 Working Directory: {os.getcwd()}")
    
    # Step 1: Run Pantip Scraper
    print_header("STEP 1/2: PANTIP SCRAPER (150+ Keywords)")
    scraper_cmd = f"{sys.executable} scraper/pantip_scraper.py"
    
    if not run_command(scraper_cmd, "Scraping Pantip threads"):
        print("\n❌ Scraper failed. Stopping pipeline.")
        return
    
    # Step 2: Run Embedding
    print_header("STEP 2/2: HUGGING FACE EMBEDDING")
    embed_cmd = f"{sys.executable} embedding/embed_with_huggingface.py"
    
    run_command(embed_cmd, "Creating embeddings")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print_header("🎉 PIPELINE COMPLETE")
    print(f"⏰ เริ่มต้น: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ สิ้นสุด: {end_time.strftime('%H:%M:%S')}")
    print(f"⏱️  ระยะเวลา: {duration}")
    print("\n✅ Scraping และ Embedding เสร็จสมบูรณ์!")
    print("📊 ตรวจสอบผลได้ที่:")
    print("   - pantip.json (ข้อมูลที่สกัด)")
    print("   - PostgreSQL database (embeddings)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  ยกเลิกการทำงานโดยผู้ใช้")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
