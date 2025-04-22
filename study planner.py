import subprocess
import requests
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from PIL import Image
from fpdf import FPDF
import json

OLLAMA_MODEL = "mistral"
OLLAMA_PORT = 11434

class StudyPlannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Study Planner")
        self.geometry("1000x800")

        self.model_started = False
        self.ollama_process = None

        image = Image.open("PM.png")
        image = image.resize((100, 300))
        self.header_image = ctk.CTkImage(light_image=image, dark_image=image, size=(300, 100))
        self.image_label = ctk.CTkLabel(self, image=self.header_image, text="")
        self.image_label.pack(pady=10)

        self.label = ctk.CTkLabel(self, text="📚 Enter the topic you want to study:", font=ctk.CTkFont(size=18))
        self.label.pack(pady=10)

        self.topic_entry = ctk.CTkEntry(self, width=800, height=40, font=ctk.CTkFont(size=16), placeholder_text="e.g. Organic Chemistry, Python Basics")
        self.topic_entry.pack(pady=10)

        self.duration_label = ctk.CTkLabel(self, text="⏱️ Desired Study Duration:", font=ctk.CTkFont(size=16))
        self.duration_label.pack(pady=(10, 2))

        self.duration_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.duration_frame.pack(pady=5)

        self.duration_entry = ctk.CTkEntry(self.duration_frame, width=100, height=35, font=ctk.CTkFont(size=14), placeholder_text="e.g. 3")
        self.duration_entry.pack(side="left", padx=5)

        self.duration_type_var = tk.StringVar(value="months")
        self.duration_dropdown = ctk.CTkOptionMenu(
            self.duration_frame,
            values=["years", "months", "days", "hours"],
            variable=self.duration_type_var,
            width=120,
            height=35,
            font=ctk.CTkFont(size=14)
        )
        self.duration_dropdown.pack(side="left", padx=5)

        self.generate_button = ctk.CTkButton(self, text="🧠 Generate Study Plan", command=self.generate_plan, height=40, font=ctk.CTkFont(size=16))
        self.generate_button.pack(pady=10)

        self.save_button = ctk.CTkButton(self, text="📄 Save as PDF", command=self.save_to_pdf, height=40, font=ctk.CTkFont(size=16))
        self.save_button.pack(pady=10)

        self.output_box = tk.Text(self, font=("Helvetica", 20), height=30, wrap="word")
        self.output_box.pack(padx=20, pady=20, fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_ollama(self):
        if not self.model_started:
            try:
                self.ollama_process = subprocess.Popen(["ollama", "run", OLLAMA_MODEL])
                self.model_started = True
            except Exception as e:
                self.output_box.insert("end", f"\n❌ Failed to start Ollama: {e}\n")

    def stop_ollama(self):
        try:
            subprocess.run(["ollama", "stop", OLLAMA_MODEL], check=True)
            if self.ollama_process:
                self.ollama_process.terminate()
        except Exception as e:
            self.output_box.insert("end", f"\n❌ Error shutting down Ollama: {e}\n")

    def generate_plan(self):
        topic = self.topic_entry.get().strip()
        if not topic:
            self.output_box.insert("end", "\n⚠️ Please enter a topic.\n")
            return

        duration_value = self.duration_entry.get().strip()
        duration_unit = self.duration_type_var.get()

        if duration_value.isdigit():
            prompt = (f"Create a detailed study plan for the topic: {topic}. "
                      f"The user wants to study this topic within {duration_value} {duration_unit}. "
                      f"Adjust the depth and schedule accordingly, and lessen time if the topic is simple.")
        else:
            prompt = f"Create a detailed study plan for the topic: {topic}, lessen the time if topic is less complex."

        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", "⏳ Generating your AI-powered study plan...\n")

        threading.Thread(target=self.query_ollama_stream, args=(prompt,), daemon=True).start()

    def query_ollama_stream(self, prompt):
        self.start_ollama()

        url = f"http://localhost:{OLLAMA_PORT}/api/generate"
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": True}

        try:
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()
                self.output_box.delete("1.0", "end")
                self.output_box.insert("end", "✅ Here’s your study plan:\n\n")
                self.output_box.see("end")

                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            chunk = data.get("response", "")
                            self.output_box.insert("end", chunk)
                            self.output_box.see("end")
                            self.update_idletasks()
                        except Exception as e:
                            self.output_box.insert("end", f"\n[Error parsing response: {e}]\n")
                            break
        except Exception as e:
            self.output_box.delete("1.0", "end")
            self.output_box.insert("end", f"\n❌ Error communicating with Ollama: {e}\n")

    def save_to_pdf(self):
        content = self.output_box.get("1.0", "end").strip()

        if not content:
            self.output_box.insert("end", "\n⚠️ Nothing to save!\n")
            return

        content = content.replace('’', "'")
        content = content.replace('✅', '[DONE]').replace('❌', '[ERROR]').replace('⏳', '[LOADING]')
        content = content.replace("[DONE] Here's your study plan:", '')

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                 filetypes=[("PDF files", "*.pdf")],
                                                 title="Save Study Plan As PDF")
        if file_path:
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_font("Helvetica", size=20)

                for line in content.split("\n"):
                    pdf.multi_cell(0, 12, txt=line)

                pdf.output(file_path)
                self.output_box.insert("end", f"\n✅ Saved to PDF: {file_path}\n")
            except Exception as e:
                self.output_box.insert("end", f"\n❌ Failed to save PDF: {e}\n")

    def on_closing(self):
        self.stop_ollama()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    app = StudyPlannerApp()
    app.mainloop()
