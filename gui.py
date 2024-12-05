import tkinter as tk
from tkinter import ttk
import time
import threading
import os

class SmartDispenserGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Smart Dispenser")
        self.root.geometry("800x480")

        # Canvas와 Scrollbar를 사용한 스크롤 가능한 영역 생성
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # 스크롤 가능한 프레임 바인딩
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Scrollable Frame 포장
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 출력 라벨
        self.output_label = tk.Label(
            self.scrollable_frame,
            text="대기 중...",
            font=("Arial", 18),
            wraplength=750,
            justify="left"
        )
        self.output_label.pack(expand=True, fill="both")

    def update_display(self, message):
        """디스플레이 업데이트 함수"""
        self.output_label.config(text=message)
        self.root.update()

    def check_for_updates(self):
        """Flask 서버에서 메시지 업데이트 확인"""
        message_file = "/tmp/gui_message.txt"
        last_message = ""
        
        while True:
            if os.path.exists(message_file):
                with open(message_file, "r") as f:
                    message = f.read().strip()
                if message != last_message:
                    self.update_display(message)
                    last_message = message
            time.sleep(1)

    def start(self):
        """GUI 메인 루프 시작"""
        threading.Thread(target=self.check_for_updates, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    gui = SmartDispenserGUI()
    gui.start()
