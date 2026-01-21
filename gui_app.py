# --- CONFIG: Persistent Browser Path for EXE ---
import sys
import os

# Set browser path BEFORE imports to prevent loading default temp paths
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    browser_dir = os.path.join(base_dir, "browsers")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir
    # Also Start Proactive Install Check immediately
    if not os.path.exists(browser_dir) or not os.listdir(browser_dir):
        # We handle the actual install inside scraper.py for logging, 
        # but setting the ENV var here is critical.
        pass

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import tkinter.ttk as ttk  # Import ttk for Progressbar
import tkinter.ttk as ttk  # Import ttk for Progressbar
import threading
import queue # For thread-safe GUI updates
# import pandas as pd # Lazy loaded
# from scraper import scrape_coupang # Lazy loaded
# from processor import calculate_shopee_price, generate_english_description # Lazy loaded

# --- UI CONSTANTS ---
BG_COLOR = None 
CARD_COLOR = None
ACCENT_COLOR = "#007bff"
TEXT_COLOR = "black"
FONT_MAIN = ("Malgun Gothic", 9)
FONT_BOLD = ("Malgun Gothic", 9, "bold")
FONT_TITLE = ("Malgun Gothic", 14, "bold")

class StdoutRedirector:
    def __init__(self, queue, tag=""):
        self.queue = queue
        self.tag = tag

    def write(self, message):
        if message.strip(): 
            msg_clean = message.strip()
            # LOG CLEANING
            if "DEBUG:" in msg_clean or "[GUI_LOG]" in msg_clean:
                return 
            
            # QUOTA ERROR MASKING
            if "quota_metric" in msg_clean or "ResourceExhausted" in msg_clean:
                self.queue.put(("log", f"{self.tag}⚠️ AI 사용량 초과 (잠시 대기 중...)"))
                return
                
            self.queue.put(("log", f"{self.tag}{message}"))
            
    def flush(self):
        pass

class CoupangShopeeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("쿠팡 -> 쇼피 자동 소싱 프로그램 (Seoul Attic Edition)")
        self.root.geometry("950x980") # Detailed View needs more height 
        # self.root.configure(bg=BG_COLOR) # Removed
        
        # Thread-safe Queue
        self.msg_queue = queue.Queue()
        self.root.after(100, self.process_queue)
        
        # Redirect Console to GUI
        sys.stdout = StdoutRedirector(self.msg_queue)
        sys.stderr = StdoutRedirector(self.msg_queue, "[ERROR] ")
        
        # Result Cache
        self.results_cache = {}  # {filename: full_text}
        
        self.api_key = self.load_api_key() or "AIzaSyA6i8VOO3H-cDaii1He6aWOpyYLl5GzsXk"
        
        # Main Layout (PanedWindow)
        self.main_pane = tk.PanedWindow(root, orient="horizontal")
        self.main_pane.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- LEFT PANEL (Controls) ---
        self.left_frame = tk.Frame(self.main_pane)
        self.main_pane.add(self.left_frame, width=500)
        
        # 1. Title
        self.lbl_title = tk.Label(self.left_frame, text="상품 소싱 및 설정", font=FONT_TITLE)
        self.lbl_title.pack(pady=10, anchor="w")

        # API Key Input
        frame_api = tk.LabelFrame(self.left_frame, text="Google Gemini API Key", font=FONT_BOLD)
        frame_api.pack(fill="x", padx=5, pady=5)
        
        frame_api_inner = tk.Frame(frame_api)
        frame_api_inner.pack(fill="x", padx=5, pady=5)

        self.entry_api_key = tk.Entry(frame_api_inner, font=FONT_MAIN, show="*") # Masked by default
        self.entry_api_key.pack(side="left", fill="x", expand=True)
        self.entry_api_key.insert(0, self.api_key) # Pre-fill existing key
        
        btn_save_key = tk.Button(frame_api_inner, text="💾 저장", command=self.save_api_key, bg="#e1e1e1")
        btn_save_key.pack(side="right", padx=5)
        
        # URL/File Input
        frame_url = tk.LabelFrame(self.left_frame, text="파일 목록 (Files)", font=FONT_BOLD)
        frame_url.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Listbox with Scrollbar
        list_frame = tk.Frame(frame_url)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. Create Listbox (Do not pack yet)
        self.list_files = tk.Listbox(list_frame, selectmode="extended", height=5, font=FONT_MAIN)
        
        # 2. Horizontal Scrollbar (Pack First to stick to bottom)
        scrollbar_x = tk.Scrollbar(list_frame, orient="horizontal", command=self.list_files.xview)
        scrollbar_x.pack(side="bottom", fill="x")

        # 3. Pack Listbox & Vertical Scrollbar
        self.list_files.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.list_files.yview)
        scrollbar.pack(side="right", fill="y")
        self.list_files.config(yscrollcommand=scrollbar.set, xscrollcommand=scrollbar_x.set)
        
        btn_browse = tk.Button(frame_url, text="파일 추가 (+)", command=self.browse_files, bg="#e1e1e1")
        btn_browse.pack(side="right", padx=5)
        
        btn_clear = tk.Button(frame_url, text="비우기 (Clear)", command=self.clear_files, bg="#e1e1e1")
        btn_clear.pack(side="right", padx=5)

        btn_remove = tk.Button(frame_url, text="선택 삭제 (-)", command=self.remove_files, bg="#e1e1e1")
        btn_remove.pack(side="right", padx=5)

        # Category Input
        frame_cat = tk.Frame(self.left_frame)
        frame_cat.pack(fill="x", padx=5, pady=5)
        
        lbl_cat = tk.Label(frame_cat, text="쇼피 카테고리 ID:", font=FONT_MAIN)
        lbl_cat.pack(side="left")
        
        self.entry_category = tk.Entry(frame_cat, font=FONT_MAIN)
        self.entry_category.pack(side="left", fill="x", expand=True, padx=5)
        
        # --- Custom AI Prompt Input ---
        lbl_prompt = tk.Label(self.left_frame, text="AI 지시사항 (Custom Prompt)", font=FONT_BOLD)
        lbl_prompt.pack(fill="x", padx=5, pady=(15, 5))
        
        self.text_prompt = scrolledtext.ScrolledText(self.left_frame, height=8, font=FONT_MAIN) 
        self.text_prompt.pack(fill="x", padx=5, pady=0)
        
        # Load saved prompt
        self.load_prompt_config()
        
        # Start Button
        self.btn_start = tk.Button(self.left_frame, text="▶ 일괄 변환 시작 (Start)", command=self.start_process, 
                                   bg=ACCENT_COLOR, fg="white", font=("Malgun Gothic", 12, "bold"), height=2)
        self.btn_start.pack(fill="x", padx=5, pady=20)
        
        # Step Indicators
        frame_steps = tk.Frame(self.left_frame)
        frame_steps.pack(fill="x", padx=5, pady=(0, 10))
        
        self.lbl_step1 = tk.Label(frame_steps, text="1.데이터수집", font=FONT_MAIN, fg="#888")
        self.lbl_step1.pack(side="left", expand=True)
        
        tk.Label(frame_steps, text="→", fg="#ccc").pack(side="left")
        
        self.lbl_step2 = tk.Label(frame_steps, text="2.AI분석/생성", font=FONT_MAIN, fg="#888")
        self.lbl_step2.pack(side="left", expand=True)
        
        tk.Label(frame_steps, text="→", fg="#ccc").pack(side="left")
        
        self.lbl_step3 = tk.Label(frame_steps, text="3.결과저장", font=FONT_MAIN, fg="#888")
        self.lbl_step3.pack(side="left", expand=True)
        
        # Progress Bar Removed as per request
        # self.progress = ttk.Progressbar(...) 
        
        # Log Area
        lbl_log = tk.Label(self.left_frame, text="시스템 로그 (System Log)", font=FONT_BOLD, anchor="w")
        lbl_log.pack(fill="x", padx=5, pady=(10, 5))
        
        self.text_log = scrolledtext.ScrolledText(self.left_frame, height=15, font=("Consolas", 9), state="normal") 
        self.text_log.pack(fill="x", padx=5, pady=0)
        
        # Open Folder
        self.btn_open_folder = tk.Button(self.left_frame, text="📂 결과 폴더 열기", command=self.open_output_folder, state="disabled", bg="#e1e1e1")
        self.btn_open_folder.pack(pady=10)
        
        # --- RIGHT PANEL (Result Split View) ---
        self.right_frame = tk.Frame(self.main_pane)
        self.main_pane.add(self.right_frame)
        
        # Split into Top (List) and Bottom (Detail)
        self.paned_result = tk.PanedWindow(self.right_frame, orient="vertical")
        self.paned_result.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 1. Result List (Top)
        frame_res_list = tk.LabelFrame(self.paned_result, text="완료된 항목 (Items)", font=FONT_BOLD)
        self.paned_result.add(frame_res_list, height=150)
        
        # 1. Create Listbox (Do not pack yet)
        self.list_results = tk.Listbox(frame_res_list, font=FONT_MAIN)
        
        # 2. Horizontal Scrollbar (Pack First)
        scrollbar_res_x = tk.Scrollbar(frame_res_list, orient="horizontal", command=self.list_results.xview)
        scrollbar_res_x.pack(side="bottom", fill="x")

        # 3. Pack Listbox & Vertical Scrollbar
        self.list_results.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.list_results.bind("<<ListboxSelect>>", self.on_result_select)
        
        scrollbar_res = tk.Scrollbar(frame_res_list, orient="vertical", command=self.list_results.yview)
        scrollbar_res.pack(side="right", fill="y")
        self.list_results.config(yscrollcommand=scrollbar_res.set, xscrollcommand=scrollbar_res_x.set)
        
        # 2. Result Detail (Bottom)
        frame_res_detail = tk.LabelFrame(self.paned_result, text="상세 내용 (Detail Preview)", font=("Malgun Gothic", 9, "bold"))
        self.paned_result.add(frame_res_detail)
        
        self.text_result = scrolledtext.ScrolledText(frame_res_detail, font=("Malgun Gothic", 10), padx=5, pady=5)
        self.text_result.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Status Label (Bottom)
        # Status Label (Bottom)
        self.lbl_status = tk.Label(root, text="준비됨", fg="gray", font=("Malgun Gothic", 9))
        self.lbl_status.pack(side="bottom", fill="x")
        
    def load_prompt_config(self):
        """Load custom prompt from file if exists"""
        try:
            if os.path.exists("prompt_config.txt"):
                with open("prompt_config.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                    self.text_prompt.delete("1.0", tk.END)
                    self.text_prompt.insert(tk.END, content)
        except Exception as e:
            print(f"Failed to load prompt config: {e}")

    def save_prompt_config(self):
        """Save current prompt to file"""
        try:
            content = self.text_prompt.get("1.0", tk.END).strip()
            with open("prompt_config.txt", "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to save prompt config: {e}")

    def browse_files(self):
        filenames = filedialog.askopenfilenames(filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")])
        if filenames:
            for f in filenames:
                self.list_files.insert(tk.END, f)
                
    def clear_files(self):
        self.list_files.delete(0, tk.END)

    def remove_files(self):
        selection = self.list_files.curselection()
        if not selection: return
        for index in reversed(selection):
            self.list_files.delete(index)

    def log(self, message):
        """Thread-safe logging with Console Mirror"""
        # print(f"[GUI_LOG] {message}") # No longer needed as we redirect stdout
        self.msg_queue.put(("log", message))

        
    def update_step(self, step_num):
        """Thread-safe step indicator update (1, 2, 3, or 0 for reset)"""
        self.msg_queue.put(("step", step_num))
        
    def append_result(self, key, label, text):
        """Thread-safe result appending: key=unique_id, label=display_name"""
        self.msg_queue.put(("result", key, label, text))
        
    def on_result_select(self, event):
        selection = self.list_results.curselection()
        if selection:
            label = self.list_results.get(selection[0])
            # Retrieve by label (Product Name)
            content = self.results_cache.get(label, "")
            self.text_result.delete("1.0", tk.END)
            self.text_result.insert(tk.END, content)

    def process_queue(self):
        """Check queue for updates"""
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "log":
                    self.text_log.insert(tk.END, msg[1] + "\n")
                    self.text_log.see(tk.END)
                elif msg_type == "result":
                    key = msg[1]
                    label = msg[2] # Product Name
                    text = msg[3]
                    
                    # Store in Cache (Key by Label for easy retrieval from Listbox)
                    self.results_cache[label] = text
                    
                    # Add to Listbox if new
                    items = self.list_results.get(0, tk.END)
                    if label not in items:
                        self.list_results.insert(tk.END, label)
                        
                    # Auto-select if first item
                    if self.list_results.size() == 1:
                        self.list_results.selection_clear(0, tk.END)
                        self.list_results.selection_set(0)
                        self.on_result_select(None)
                elif msg_type == "step":
                    step = msg[1]
                    # Reset all
                    def set_style(lbl, active=False, done=False):
                        if done: lbl.config(fg="#28a745", font=("Malgun Gothic", 9, "bold")) # Green
                        elif active: lbl.config(fg="#007bff", font=("Malgun Gothic", 9, "bold")) # Blue
                        else: lbl.config(fg="#999", font=("Malgun Gothic", 9)) # Gray
                    
                    if step == 0: # Reset
                        set_style(self.lbl_step1)
                        set_style(self.lbl_step2)
                        set_style(self.lbl_step3)
                    elif step == 1:
                        set_style(self.lbl_step1, active=True)
                    elif step == 2:
                        set_style(self.lbl_step1, done=True)
                        set_style(self.lbl_step2, active=True)
                    elif step == 3:
                        set_style(self.lbl_step1, done=True)
                        set_style(self.lbl_step2, done=True)
                        set_style(self.lbl_step3, active=True)
                    elif step == 4: # All Done
                        set_style(self.lbl_step1, done=True)
                        set_style(self.lbl_step2, done=True)
                        set_style(self.lbl_step3, done=True)
                    
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Queue Error: {e}")
        finally:
            self.root.after(100, self.process_queue)

    def start_process(self):
        print("DEBUG: start_process called")
        sys.stdout.flush()
        files = self.list_files.get(0, tk.END)
        category_id = self.entry_category.get().strip()
        
        if not files:
            messagebox.showwarning("Warning", "파일을 하나 이상 추가해주세요.")
            return
            
        self.btn_start.config(state="disabled", text="진행 중...")
        self.text_log.delete(1.0, tk.END)
        self.btn_open_folder.config(state="disabled")
        self.lbl_status.config(text="처리 중...")
        self.log(f"총 {len(files)}개 파일 작업 시작.")
        
        self.update_step(0) # Reset steps
        
        self.list_results.delete(0, tk.END) # Clear result list
        self.results_cache = {} # Clear cache
        self.text_result.delete(1.0, tk.END) # Clear detail view
        
        self.save_prompt_config()  # Save prompt on start
        user_prompt = self.text_prompt.get("1.0", tk.END).strip()
        current_api_key = self.entry_api_key.get().strip() # Get Key from GUI

        if not current_api_key:
             messagebox.showwarning("API Key", "API Key를 입력해주세요.")
             self.btn_start.config(state="normal", text="▶ 일괄 변환 시작 (Start)") # Re-enable button
             return
        
        # Run in thread
        print(f"DEBUG: Spawning thread with args: {len(files)} files, cat={category_id}, prompt_len={len(user_prompt)}")
        sys.stdout.flush()
        threading.Thread(target=self.run_process, args=(files, category_id, user_prompt, current_api_key), daemon=True).start()

    def run_process(self, files, category_id, user_prompt, api_key):
        print("DEBUG: Thread started running")
        sys.stdout.flush()
        
        # Lazy Import to speed up GUI launch
        try:
            from scraper import scrape_coupang
            from processor import calculate_shopee_price, generate_english_description
        except ImportError as e:
            self.log(f"Critical Import Error: {e}")
            return

        try:
            # 1. Generate Output Filename ONCE
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = os.path.abspath(f"output/shopee_upload_{timestamp}.xlsx")
            
            # Loop
            for idx, url in enumerate(files):
                current_num = idx + 1
                total = len(files)
                self.log(f"\n--- [{current_num}/{total}] 처리 중: {os.path.basename(url)} ---")
                
                try:
                    # 1. Scrape
                    self.update_step(1) # Visual Step 1
                    self.log("데이터 추출 중...")
                    product_data = scrape_coupang(url)
                    
                    if not product_data or not product_data['title']:
                        self.log(">> 오류: 데이터 추출 실패. 건너뜁니다.")
                        self.update_progress(idx + 1)
                        continue # Skip to next

                    self.log(f"추출 성공: {product_data['title'][:15]}...")
                    # Progress step 1 removed


                    # 3. AI Processing
                    self.update_step(2) # Visual Step 2
                    self.log(f"AI 설명 생성 중... (Images found: {len(product_data.get('images', []))})")
                    eng_data = generate_english_description(
                        product_data['title'], 
                        product_data['images'],
                        use_ai=True, 
                        api_key=api_key,
                        user_prompt=user_prompt  # Pass custom prompt
                    )
                    # Progress step 2 removed
                    
                    product_data.update({
                        'eng_title': eng_data['title'],
                        'eng_description': eng_data['description'],
                        'weight_val': eng_data.get('weight_kg')
                    })
                    
                    # 2-B. Category (MOVED: Analyze using ENGLISH TITLE)
                    final_category_id = category_id
                    if not final_category_id:
                        self.log(f"카테고리 자동 분석 중... (Based on: {eng_data['title'][:20]}...)")
                        try:
                            import xlwings as xw
                            template_path = os.path.abspath("program/Shopee_template.xlsx")
                            if not os.path.exists(template_path): template_path = os.path.abspath("Shopee_template.xlsx")
                            
                            cat_list = []
                            if os.path.exists(template_path):
                                app = xw.App(visible=False)
                                wb = app.books.open(template_path)
                                try:
                                    s = wb.sheets['HiddenCatProps']
                                    vals = s.range('A1:A500').value
                                    cat_list = [v for v in vals if v]
                                except: pass
                                finally: wb.close(); app.quit()
                                
                                if cat_list:
                                    from processor import select_best_category
                                    # USE ENGLISH TITLE HERE
                                    best_cat = select_best_category(eng_data['title'], cat_list, api_key)
                                    if best_cat: 
                                        self.log(f"  -> AI 카테고리: {best_cat}")
                                        final_category_id = best_cat.split('-')[0]
                        except Exception as e:
                            self.log(f"카테고리 분석 실패: {e}")
                    
                    # --- SHOW RESULT IN GUI ---
                    display_text = f"""
[TITLE]
{eng_data['title']}

[DESCRIPTION]
{eng_data['description']}
"""
                    # Use URL basename as key, Product Title as Label
                    self.append_result(os.path.basename(url), product_data['title'], display_text)

                    # 4. Price & Export
                    self.update_step(3) # Visual Step 3
                    image_count = len(product_data.get('image_urls', []))
                    self.log(f"판매가 계산 및 엑셀 저장... (Remote URL 개수: {image_count})")
                    
                    final_price = calculate_shopee_price(product_data['price'], product_data.get('weight_str'))
                    
                    # Call Export with FIXED output filename
                    self.export_to_excel(product_data, final_price, final_category_id, output_filename)
                    self.log(">> 저장 완료.")
                    
                    # Progress step 3 removed
                    
                    # Delay to prevent Excel locking issues
                    import time
                    time.sleep(2)
                    
                except Exception as item_e:
                    self.log(f">> [오류] 이 상품 처리 중 실패: {item_e}")
                    import traceback
                    traceback.print_exc()
            
            # End of Loop
            self.update_step(4) # Check all green
            self.log("\n모든 작업이 완료되었습니다!")
            messagebox.showinfo("Success", f"총 {len(files)}개 작업 완료.\n파일: {output_filename}")
            os.startfile(os.path.abspath("output"))
            self.btn_open_folder.config(state="normal")
            
        except Exception as e:
            self.log(f"치명적 오류 발생: {e}")
            messagebox.showerror("오류", f"실행 중 문제 발생: {e}")
        finally:
            self.reset_ui()
    

    def export_to_excel(self, product_data, shopee_price, category_id, output_file):
        os.makedirs("output", exist_ok=True)
        template_path = os.path.abspath("program/Shopee_template.xlsx")
        if not os.path.exists(template_path):
            template_path = os.path.abspath("Shopee_template.xlsx")
        if not os.path.exists(template_path):
             # Try _internal for PyInstaller 6 single-folder bundle
             base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
             template_path = os.path.join(base_dir, "_internal", "Shopee_template.xlsx")
            
        if not os.path.exists(template_path):
             messagebox.showerror("Error", f"Shopee_template.xlsx 파일을 찾을 수 없습니다.\nPath: {template_path}")
             return

        try:
            import xlwings as xw
            
            # Check if output file already exists (from previous item in batch)
            is_new_file = not os.path.exists(output_file)
            
            # app = xw.App(visible=False) # Keep invisible
            # Use existing app if possible or create new? Safer to create new for isolation
            app = xw.App(visible=False) 
            
            if is_new_file:
                # Open template and Save As output
                wb = app.books.open(template_path)
                wb.save(output_file)
            else:
                # Open existing output
                wb = app.books.open(output_file)
            
            try:
                # Find Sheet
                ws = None
                for sheet in wb.sheets:
                    if "Template" in sheet.name:
                        ws = sheet; break
                if not ws: ws = wb.sheets[0]
                
                # Header mapping logic
                header_row_idx = None
                col_map = {}
                used_range = ws.used_range
                raw_data = used_range.options(ndim=2).value
                
                for r_idx, row_vals in enumerate(raw_data[:20]): 
                    row_vals_str = [str(x) if x else "" for x in row_vals]
                    if any("Product Name" in s for s in row_vals_str):
                        header_row_idx = r_idx + 1
                        col_map = {}
                        for c_idx, val in enumerate(row_vals_str):
                            if val:
                                key = val.strip()
                                if key not in col_map: col_map[key] = []
                                col_map[key].append(c_idx + 1)
                        break
                
                if not header_row_idx:
                     raise Exception("엑셀에서 'Product Name' 헤더를 찾지 못했습니다.")

                # Prepare Data
                import time
                # SKU needs to be unique per item. existing int(time.time()) might duplicate if fast.
                # Add random suffix
                import random
                sku = f"KR-{int(time.time())}-{random.randint(100,999)}"
                image_source = product_data.get('image_urls', [])
                
                # Ensure Category is not empty (Fix Shopee 'Category can not be empty' error)
                final_cat = str(category_id).strip()
                if not final_cat or final_cat == "None":
                    final_cat = "100874" # Default fallback (Hair Care > Others)
                    print("Warning: Category ID empty. Defaulting to 100874.")

                weight_val = product_data.get('weight_val') or 0.5

                data_map = {
                    'Category': final_cat, 
                    'Product Name': product_data['eng_title'],
                    'Product Description': product_data['eng_description'],
                    'Parent SKU': sku,
                    'Global SKU Price': shopee_price,
                    'Stock': 999,
                    'SKU': sku,
                    'Weight': weight_val,
                    'Days to ship': 1,
                    'Brand': 0, 
                    'Cover image': image_source[0] if image_source else "",
                }
                
                # Determine Target Row (First empty row in Product Name col)
                target_r = header_row_idx + 1
                prod_name_col = col_map.get('Product Name', [2])[0]
                
                while True:
                    val = ws.range((target_r, prod_name_col)).value
                    if not val:
                        break
                    target_r += 1
                
                # Write Data
                for col_name, val in data_map.items():
                    if col_name in col_map:
                        col_idx = col_map[col_name][0]
                        ws.range((target_r, col_idx)).value = val
                
                # Write Weight to FIRST occurrence only (Shipping Weight)
                if 'Weight' in col_map:
                    weight_cols = col_map['Weight']
                    ws.range((target_r, weight_cols[0])).value = float(weight_val)
                    for w_col in weight_cols[1:]:
                        ws.range((target_r, w_col)).value = "" # Clear attribute weight
                    
                # Map Images 1-8
                for i in range(1, 9):
                    key = f"Item Image {i}" 
                    if key in col_map:
                         val = image_source[i] if i < len(image_source) else ""
                         ws.range((target_r, col_map[key][0])).value = val
                
                wb.save() # Just save, file path already set
                
            finally:
                wb.close()
                app.quit()
                
        except Exception as e:
            self.log(f"Excel Error: {e}")
            raise e

    def reset_ui(self):
        self.btn_start.config(state="normal", text="일괄 분석 및 변환 시작")
        self.lbl_status.config(text="대기 중")
        
    def open_output_folder(self):
        os.startfile(os.path.abspath("output"))

    def load_api_key(self):
        """Loads API Key from local file 'config_api.txt'."""
        try:
            config_path = os.path.abspath("config_api.txt")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                if key and len(key) > 20: # Basic validation
                    return key
        except Exception as e:
            print(f"Error loading API Key: {e}")
        return None

    def save_api_key(self):
        """Saves current API Key to 'config_api.txt'."""
        key = self.entry_api_key.get().strip()
        if not key:
            messagebox.showwarning("오류", "저장할 API Key를 입력해주세요.")
            return
            
        try:
            config_path = os.path.abspath("config_api.txt")
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(key)
            messagebox.showinfo("저장 완료", "API Key가 안전하게 저장되었습니다.\n다음 실행 시 자동 적용됩니다.")
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {e}")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except: pass

    root = tk.Tk()
    app = CoupangShopeeApp(root)
    root.mainloop()
