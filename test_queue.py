
import tkinter as tk
from tkinter import scrolledtext
import threading
import queue
import time

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("400x300")
        
        self.text_log = scrolledtext.ScrolledText(root, height=10)
        self.text_log.pack(fill="both", expand=True)
        
        self.msg_queue = queue.Queue()
        self.root.after(100, self.process_queue)
        
        self.btn = tk.Button(root, text="Start Thread", command=self.start_thread)
        self.btn.pack()
        
    def log(self, msg):
        self.msg_queue.put(("log", msg))
        
    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if msg[0] == "log":
                    self.text_log.insert(tk.END, msg[1] + "\n")
                    self.text_log.see(tk.END)
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
            
    def start_thread(self):
        self.log("Main Thread Log")
        threading.Thread(target=self.run_process, daemon=True).start()
        
    def run_process(self):
        self.log("Thread Started")
        time.sleep(1)
        self.log("Thread Working...")
        time.sleep(1)
        self.log("Thread Done")

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    # create a file to signal we are running 
    with open("test_queue_running.txt", "w") as f: f.write("running")
    # Auto-click start after 1s then close after 3s to automate test
    root.after(1000, lambda: app.btn.invoke())
    root.after(4000, root.destroy)
    root.mainloop()
