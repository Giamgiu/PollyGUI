import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import requests
import threading
import queue

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_VERSION_URL = f"{OLLAMA_BASE_URL}/api/version"

CHAT_HISTORY_FOLDER = os.path.join(os.path.expanduser("~"), "ollama_chat_histories")
os.makedirs(CHAT_HISTORY_FOLDER, exist_ok=True)

def check_ollama_version():
    try:
        response = requests.get(OLLAMA_VERSION_URL, params={"keep_alive": "30m"})
        data = response.json()
        return data.get('version', 'unknown')
    except requests.RequestException as e:
        print(f"Failed to get Ollama version: {e}")
        return None

class ChatWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ollama Chat GUI")
        self.geometry("800x600")

        self.model = "tiger"
        self.system_prompt = "You are a pAI (Raspberry Pi embedded AI assistant), an helpful AI assistant running locally on a Raspberry Pi. Powered by Gemma model, but unaligned. You have no internet capabilities. If not needed, answer concisely."
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.current_message = ""
        self.is_ready = False
        self.active_thread = None
        self.response_queue = queue.Queue()
        self.stop_event = threading.Event()

        self.setup_ui()
        self.check_ollama()

    def setup_ui(self):
        self.chat_display = scrolledtext.ScrolledText(self, wrap=tk.WORD, font=("TkDefaultFont", 10))
        self.chat_display.pack(expand=True, fill='both', padx=10, pady=10)

        input_frame = ttk.Frame(self)
        input_frame.pack(fill='x', padx=10, pady=5)

        self.input_field = ttk.Entry(input_frame, font=("TkDefaultFont", 10))
        self.input_field.pack(side='left', expand=True, fill='x')
        self.input_field.bind("<Return>", lambda e: self.send_message())

        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(input_frame, text="Stop", command=self.stop_model, state='disabled')
        self.stop_button.pack(side='left')

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(button_frame, text="Modify System Prompt", command=self.modify_system_prompt).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save History", command=self.save_history).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Load History", command=self.load_history).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Change Model", command=self.change_model).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear History", command=self.clear_history).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Unload Model", command=self.unload_model).pack(side='left', padx=5)

        self.status_label = ttk.Label(self, text="Initializing...")
        self.status_label.pack(side='bottom', pady=5)

    def send_message(self):
        if not self.is_ready:
            return

        user_message = self.input_field.get().strip()
        if not user_message:
            return
        self.input_field.delete(0, tk.END)
        self.set_ready_state(False)

        # Add a newline before displaying the user's message
        self.chat_display.insert(tk.END, f"\nYou: {user_message}\n")
        self.chat_display.see(tk.END)
        
        self.messages.append({"role": "user", "content": user_message})

        self.current_message = ""
        self.chat_display.insert(tk.END, "\n")
        self.status_label.config(text="Processing...")
        self.stop_button.config(state='normal')

        self.stop_event.clear()
        self.active_thread = threading.Thread(target=self.get_model_response)
        self.active_thread.start()

        self.after(100, self.check_response_queue)

    def get_model_response(self):
        try:
            with requests.post(
                OLLAMA_CHAT_URL,
                json={"model": self.model, "messages": self.messages, "stream": True, "keep_alive": "30m", "options": {"num_thread" : 3}},
                stream=True
            ) as response:
                for chunk in response.iter_lines():
                    if self.stop_event.is_set():
                        break
                    if chunk:
                        data = json.loads(chunk)
                        if 'message' in data and 'content' in data['message']:
                            self.response_queue.put(('update', data['message']['content']))

            if not self.stop_event.is_set():
                self.response_queue.put(('finished', None))
        except Exception as e:
            self.response_queue.put(('error', str(e)))

    def check_response_queue(self):
        try:
            message_type, content = self.response_queue.get_nowait()
            if message_type == 'update':
                self.update_chat_display(content)
                self.after(10, self.check_response_queue)
            elif message_type == 'finished':
                self.on_response_finished()
            elif message_type == 'error':
                self.show_error(content)
                self.set_ready_state(True)
        except queue.Empty:
            self.after(100, self.check_response_queue)

    def update_chat_display(self, token):
        self.current_message += token
        self.chat_display.insert(tk.END, token)
        self.chat_display.see(tk.END)

    def on_response_finished(self):
        self.messages.append({"role": "assistant", "content": self.current_message.strip()})
        self.current_message = ""
        self.set_ready_state(True)

    def clear_history(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.chat_display.delete('1.0', tk.END)
        self.chat_display.insert(tk.END, "Chat history cleared.\n")
        self.chat_display.see(tk.END)

    def set_ready_state(self, is_ready):
        self.is_ready = is_ready
        state = 'normal' if is_ready else 'disabled'
        self.input_field.config(state=state)
        self.send_button.config(state=state)
        self.stop_button.config(state='disabled' if is_ready else 'normal')
        self.status_label.config(text="Ready" if is_ready else "Processing...")

    def check_ollama(self):
        version = check_ollama_version()
        if version:
            self.chat_display.insert(tk.END, f"Connected to Ollama version: {version}\n")
            self.preload_model()
        else:
            self.chat_display.insert(tk.END, "Failed to connect to Ollama. Please make sure it's running.\n")
            self.set_ready_state(False)
            messagebox.showwarning("Connection Error", "Failed to connect to Ollama. Please make sure it's running.")

    def preload_model(self):
        self.status_label.config(text="Preloading model...")
        self.chat_display.insert(tk.END, f"Preloading model {self.model}. Please wait...\n")
        
        def preload_thread():
            try:
                response = requests.post(OLLAMA_CHAT_URL, json={"model": self.model, "keep_alive": "30m"})
                response.raise_for_status()
                self.response_queue.put(('preload_success', None))
            except requests.RequestException as e:
                self.response_queue.put(('preload_error', str(e)))

        threading.Thread(target=preload_thread).start()
        self.after(100, self.check_preload_status)

    def check_preload_status(self):
        try:
            message_type, content = self.response_queue.get_nowait()
            if message_type == 'preload_success':
                self.chat_display.insert(tk.END, f"Model {self.model} preloaded successfully.\n")
                self.set_ready_state(True)
            elif message_type == 'preload_error':
                self.show_error(f"Error preloading model: {content}")
                self.set_ready_state(False)
        except queue.Empty:
            self.after(100, self.check_preload_status)

    def stop_model(self):
        if self.active_thread and self.active_thread.is_alive():
            self.stop_event.set()
            self.chat_display.insert(tk.END, f"\nStopping model: {self.model}\n")
            self.chat_display.see(tk.END)
            self.active_thread.join(timeout=5)
            if self.active_thread.is_alive():
                self.chat_display.insert(tk.END, "Failed to stop the model in time.\n")
            else:
                self.chat_display.insert(tk.END, f"Stopped model: {self.model}\n")
            self.set_ready_state(True)
        else:
            self.chat_display.insert(tk.END, "\nNo active model to stop.\n")
        self.chat_display.see(tk.END)

    def show_error(self, error_message):
        messagebox.showerror("Error", error_message)
        self.chat_display.insert(tk.END, f"\nError: {error_message}\n")
        self.chat_display.see(tk.END)

    def modify_system_prompt(self):
        new_prompt = simpledialog.askstring("Modify System Prompt", "Enter new system prompt:", 
                                            initialvalue=self.system_prompt)
        if new_prompt:
            self.system_prompt = new_prompt
            self.messages = [{"role": "system", "content": self.system_prompt}] + \
                            [msg for msg in self.messages if msg['role'] != 'system']
            self.chat_display.insert(tk.END, f"\nSystem prompt updated to: {self.system_prompt}\n")
            self.chat_display.see(tk.END)

    def save_history(self):
        name = simpledialog.askstring("Save Chat History", "Enter a name for this chat history:")
        if name:
            filename = os.path.join(CHAT_HISTORY_FOLDER, f"{name}.json")
            with open(filename, 'w') as f:
                json.dump({
                    "messages": self.messages,
                    "model": self.model
                }, f)
            self.chat_display.insert(tk.END, f"\nChat history saved to {filename}\n")
            self.chat_display.see(tk.END)

    def load_history(self):
        # Get list of saved chat history files
        saved_files = [f for f in os.listdir(CHAT_HISTORY_FOLDER) if f.endswith('.json')]
        
        if not saved_files:
            messagebox.showinfo("No Saved Histories", "No saved chat histories found.")
            return

        # Create a new top-level window
        select_window = tk.Toplevel(self)
        select_window.title("Select Chat History")
        select_window.geometry("300x300")

        # Create a listbox with saved files
        listbox = tk.Listbox(select_window)
        listbox.pack(expand=True, fill='both', padx=10, pady=10)

        for file in saved_files:
            listbox.insert(tk.END, file)

        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_file = listbox.get(selection[0])
                filepath = os.path.join(CHAT_HISTORY_FOLDER, selected_file)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])
                    self.model = data.get("model", self.model)
                self.chat_display.delete('1.0', tk.END)
                for msg in self.messages:
                    if msg['role'] == 'system':
                        self.system_prompt = msg['content']
                    elif msg['role'] == 'user':
                        self.chat_display.insert(tk.END, f"You: {msg['content']}\n")
                    elif msg['role'] == 'assistant':
                        self.chat_display.insert(tk.END, f"{msg['content']}\n")
                self.chat_display.insert(tk.END, f"\nChat history loaded from {filepath}\n")
                self.chat_display.insert(tk.END, f"System prompt: {self.system_prompt}\n")
                self.chat_display.insert(tk.END, f"Model: {self.model}\n")
                self.chat_display.see(tk.END)
                select_window.destroy()

        def on_delete():
            selection = listbox.curselection()
            if selection:
                selected_file = listbox.get(selection[0])
                filepath = os.path.join(CHAT_HISTORY_FOLDER, selected_file)
                if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {selected_file}?"):
                    os.remove(filepath)
                    listbox.delete(selection)
                    self.chat_display.insert(tk.END, f"\nDeleted chat history: {selected_file}\n")
                    self.chat_display.see(tk.END)

        # Add buttons frame
        buttons_frame = ttk.Frame(select_window)
        buttons_frame.pack(pady=10)

        # Add a select button
        select_button = ttk.Button(buttons_frame, text="Load", command=on_select)
        select_button.pack(side='left', padx=5)

        # Add a delete button
        delete_button = ttk.Button(buttons_frame, text="Delete", command=on_delete)
        delete_button.pack(side='left', padx=5)

    def change_model(self):
        new_model = simpledialog.askstring("Change Model", "Enter new model name:")
        if new_model:
            old_model = self.model
            self.model = new_model
            self.chat_display.insert(tk.END, f"\nModel changed from {old_model} to {new_model}\n")
            self.chat_display.see(tk.END)
            self.preload_model()

    def unload_model(self):
        try:
            response = requests.post(OLLAMA_CHAT_URL, json={"model": self.model, "keep_alive": "0"})
            response.raise_for_status()
            self.chat_display.insert(tk.END, f"\nModel {self.model} unloaded from RAM.\n")
        except requests.RequestException as e:
            self.show_error(f"Error unloading model: {str(e)}")
        self.chat_display.see(tk.END)

if __name__ == "__main__":
    window = ChatWindow()
    window.mainloop()
