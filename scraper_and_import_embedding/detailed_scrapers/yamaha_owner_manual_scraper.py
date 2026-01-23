import os
import json
import time
import requests
import pdfplumber
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def start_scraper():
    # 1. ตั้งค่าโฟลเดอร์เก็บไฟล์
    base_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(base_dir, "yamaha_manuals_pdf")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"สร้างโฟลเดอร์เก็บไฟล์ที่: {download_dir}")

    # 2. ตั้งค่า Browser
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # ปิดไว้ก่อนเพื่อให้คุณเห็นการทำงาน
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    all_data = []

    try:
        print("กำลังเข้าสู่หน้าเว็บหลัก...")
        driver.get("https://www.yamaha-motor.co.th/dealer-services/owners-manual")
        
        # 3. หาลิงก์ "ดูทั้งหมด" ของทุกหมวด
        view_all_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.contentt-1.txt20")))
        category_urls = [el.get_attribute('href') for el in view_all_elements if el.get_attribute('href')]
        print(f"พบหมวดหมู่ทั้งหมด {len(category_urls)} หมวด")

        for cat_url in category_urls:
            print(f"\n--- กำลังเข้าหมวดหมู่: {cat_url} ---")
            driver.get(cat_url)
            time.sleep(3) # รอหน้าเว็บโหลดข้อมูลรุ่นรถ

            # 4. หาปุ่มภาษาไทยในหมวดนั้นๆ (ต้องนิยามภายใน loop นี้)
            thai_buttons = driver.find_elements(By.CSS_SELECTOR, "a.mainbtnshort.red")
            print(f"พบปุ่มภาษาไทย {len(thai_buttons)} ปุ่ม")

            for btn in thai_buttons:
                try:
                    pdf_url = btn.get_attribute('href')
                    # หาชื่อรุ่นจาก Element รอบข้าง (ปรับตามโครงสร้างหน้าเว็บ)
                    # สมมติว่าชื่อรุ่นอยู่ใน tag h4 หรือ div ที่อยู่เหนือปุ่ม
                    model_name = btn.find_element(By.XPATH, "./ancestor::div[contains(@class,'thumbnail-sticker')]//h4").text
                except Exception:
                    model_name = f"model_{int(time.time())}"

                if pdf_url and ".pdf" in pdf_url:
                    clean_name = "".join(x for x in model_name if x.isalnum() or x in "._- ").strip()
                    file_name = f"{clean_name}_TH.pdf"
                    file_path = os.path.join(download_dir, file_name)

                    print(f"กำลังจัดการรุ่น: {model_name}")
                    
                    # ดาวน์โหลดไฟล์
                    res = requests.get(pdf_url)
                    with open(file_path, "wb") as f:
                        f.write(res.content)

                    # สกัดข้อความจาก PDF
                    text_content = ""
                    try:
                        with pdfplumber.open(file_path) as pdf:
                            for page in pdf.pages:
                                text_content += (page.extract_text() or "") + "\n"
                    except Exception as e:
                        text_content = f"Error extracting text: {e}"

                    all_data.append({
                        "model": model_name,
                        "pdf_url": pdf_url,
                        "local_file": file_path,
                        "content": text_content.strip()
                    })

        # 5. บันทึกข้อมูลทั้งหมดเป็น JSON
        json_output = os.path.join(base_dir, "yamaha_all_manuals_data.json")
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        
        print(f"\n[สำเร็จ] สกัดข้อมูลเสร็จสิ้นทั้งหมด {len(all_data)} รายการ")
        print(f"ไฟล์ JSON อยู่ที่: {json_output}")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการทำงาน: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    start_scraper()