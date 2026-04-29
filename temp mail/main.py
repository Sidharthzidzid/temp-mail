import tkinter as tk
from tkinter import ttk, messagebox
from mailtm import Email  # Ensure the mailtm library is installed
import threading
import base64
import os
import webbrowser
import ast  # For safely parsing string representations of Python literals
import requests  # Required for downloading attachments using `downloadUrl`
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class TempEmailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Temporary Email Service")
        self.email = None
        self.listening = False
        self.listener_thread = None

        # Main Frame
        self.main_frame = tk.Frame(root, padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Email Address Section
        self.email_frame = tk.Frame(self.main_frame)
        self.email_frame.pack(pady=10, fill=tk.X)

        self.email_label = tk.Label(self.email_frame, text="Temporary Email Address:", font=("Arial", 12, "bold"))
        self.email_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.email_address = tk.StringVar(value="Loading...")
        self.email_display = tk.Entry(self.email_frame, textvariable=self.email_address, font=("Arial", 12),
                                       state="readonly", width=40)
        self.email_display.grid(row=0, column=1, padx=5, pady=5)

        # Buttons for Email Actions
        self.buttons_frame = tk.Frame(self.main_frame)
        self.buttons_frame.pack(pady=10, fill=tk.X)

        self.copy_button = tk.Button(self.buttons_frame, text="Copy", command=self.copy_email)
        self.copy_button.grid(row=0, column=0, padx=5, pady=5)

        self.refresh_button = tk.Button(self.buttons_frame, text="Refresh", command=self.refresh_email)
        self.refresh_button.grid(row=0, column=1, padx=5, pady=5)

        self.delete_button = tk.Button(self.buttons_frame, text="Delete", command=self.delete_email)
        self.delete_button.grid(row=0, column=2, padx=5, pady=5)

        self.new_email_button = tk.Button(self.buttons_frame, text="New Email", command=self.generate_email)
        self.new_email_button.grid(row=0, column=3, padx=5, pady=5)

        self.send_email_button = tk.Button(self.buttons_frame, text="Send Email", command=self.open_send_email_window)
        self.send_email_button.grid(row=0, column=4, padx=5, pady=5)

        self.listen_button = tk.Button(self.buttons_frame, text="Start Listening", command=self.start_listening)
        self.listen_button.grid(row=0, column=5, padx=5, pady=5)

        self.stop_button = tk.Button(self.buttons_frame, text="Stop Listening", command=self.stop_listening,
                                     state=tk.DISABLED)
        self.stop_button.grid(row=0, column=6, padx=5, pady=5)

        # Inbox Section
        self.inbox_label = tk.Label(self.main_frame, text="Inbox:", font=("Arial", 12, "bold"))
        self.inbox_label.pack(pady=5, anchor="w")

        columns = ("sender", "subject", "preview", "content", "attachments")
        self.inbox_tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", height=10)
        self.inbox_tree.heading("sender", text="Sender")
        self.inbox_tree.heading("subject", text="Subject")
        self.inbox_tree.heading("preview", text="Content Preview")
        self.inbox_tree.heading("attachments", text="Attachments")
        self.inbox_tree.pack(pady=5, fill=tk.BOTH, expand=True)

        # Bind the click event to open a detailed email view
        self.inbox_tree.bind("<Double-1>", self.view_email)

    def copy_email(self):
        email = self.email_address.get()
        if email and email != "Loading...":
            self.root.clipboard_clear()
            self.root.clipboard_append(email)
            self.root.update()
            messagebox.showinfo("Copied", "Email address copied to clipboard!")

    def refresh_email(self):
        if self.email:
            self.email_address.set("Refreshing...")
            self.email_address.set(self.email.address)
            messagebox.showinfo("Refreshed", "Email address refreshed!")

    def delete_email(self):
        if self.listening:
            self.stop_listening()
        self.email_address.set("Deleted")
        messagebox.showinfo("Deleted", "Temporary email address deleted!")

    def generate_email(self):
        try:
            self.email = Email()
            self.email.register()
            self.email_address.set(self.email.address)
            messagebox.showinfo("Generated", f"New email address generated: {self.email.address}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate email: {e}")

    def open_send_email_window(self):
        send_email_window = tk.Toplevel(self.root)
        send_email_window.title("Send Email")

        tk.Label(send_email_window, text="To:").grid(row=0, column=0, padx=5, pady=5)
        recipient_entry = tk.Entry(send_email_window, width=40)
        recipient_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(send_email_window, text="Subject:").grid(row=1, column=0, padx=5, pady=5)
        subject_entry = tk.Entry(send_email_window, width=40)
        subject_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(send_email_window, text="Body:").grid(row=2, column=0, padx=5, pady=5)
        body_text = tk.Text(send_email_window, width=40, height=10)
        body_text.grid(row=2, column=1, padx=5, pady=5)

        send_button = tk.Button(send_email_window, text="Send", command=lambda: self.send_email_with_sendgrid(
            recipient_entry.get(), subject_entry.get(), body_text.get("1.0", tk.END)))
        send_button.grid(row=3, column=1, padx=5, pady=5)

    def send_email_with_sendgrid(self, to_email, subject, body):
        if not self.email:
            messagebox.showerror("Error", "No temporary email address available.")
            return

        try:
            message = Mail(
                from_email=self.email.address,  # Use the temporary email address
                to_emails=to_email,
                subject=subject,
                plain_text_content=body
            )
            sg = SendGridAPIClient('your_sendgrid_api_key')  # Replace with your SendGrid API key
            response = sg.send(message)
            messagebox.showinfo("Success", f"Email sent successfully! Status code: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send email: {e}")

    def start_listening(self):
        if self.email and not self.listening:
            self.listening = True
            self.listener_thread = threading.Thread(target=self.run_listener, daemon=True)
            self.listener_thread.start()
            self.stop_button.config(state=tk.NORMAL)
            messagebox.showinfo("Listening", "Started listening for new emails!")

    def run_listener(self):
        def listener(message):
            print(f"Full message: {message}")  # Debugging

            sender = message.get("from", "Unknown sender")
            subject = message.get("subject", "No subject")

            # Prioritize HTML content or fallback to text content
            content = message.get("html") or message.get("text") or "No content available"
            print(f"Selected content: {content}")  # Debugging

            if isinstance(content, list):
                content = " ".join(content)

            attachments = message.get("attachments", [])
            attachment_files = []
            for attachment in attachments:
                filename = attachment.get("filename", "unknown")
                data = attachment.get("data", "")
                if data:
                    file_path = os.path.join(os.getcwd(), filename)
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(data))
                    attachment_files.append(file_path)

            attachments_str = ", ".join(attachment_files)

            self.inbox_tree.insert(
                "", "end",
                values=(str(sender), str(subject), str(content[:50]) + "...", str(content), str(attachments_str))
            )

        try:
            self.email.start(listener, 1)
        except Exception as e:
            messagebox.showerror("Error", f"Listener failed: {e}")

    def stop_listening(self):
        if self.listening:
            self.listening = False
            if self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=1)
            self.stop_button.config(state=tk.DISABLED)
            messagebox.showinfo("Stopped", "Stopped listening for emails!")

    def view_email(self, event):
        selected_item = self.inbox_tree.selection()
        if selected_item:
            item = self.inbox_tree.item(selected_item)
            email_content = item["values"][3]
            attachments_str = item["values"][4]

            # Safely parse the attachments
            try:
                attachments = ast.literal_eval(attachments_str) if attachments_str else []
            except (ValueError, SyntaxError):
                attachments = []

            self.show_email(email_content, attachments)

    def show_email(self, content, attachments):
        # Handle email content fallback
        if not content or content.strip() in ["<div dir=\"ltr\"><br></div>", "No content available"]:
            content = "This email contains no body content or is empty."
            print("Email body is empty. Using fallback message.")  # Debugging

        # Save the email content to a temporary file
        temp_file = os.path.join(os.getcwd(), "temp_email.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Email content saved to {temp_file}")  # Debugging

        # Open the email content in the default web browser
        webbrowser.open(f"file://{temp_file}")
        print("Email content opened in browser.")  # Debugging

        # Ensure attachments are processed
        if attachments:
            print("Processing attachments...")  # Debugging
            attachment_dir = os.path.join(os.getcwd(), "attachments")
            if not os.path.exists(attachment_dir):
                os.makedirs(attachment_dir)

            for attachment in attachments:
                try:
                    filename = attachment.get("filename", "unknown_file")
                    data = attachment.get("data", "")
                    download_url = attachment.get("downloadUrl", "")
                    print(f"Attachment found: {filename}")  # Debugging

                    # Save the attachment if data or downloadUrl is available
                    file_path = os.path.join(attachment_dir, filename)

                    if data:
                        # Save the file using the base64 data
                        with open(file_path, "wb") as f:
                            f.write(base64.b64decode(data))
                        print(f"Attachment saved to {file_path} using base64 data.")  # Debugging
                    elif download_url:
                        # Download the file using the downloadUrl
                        response = requests.get(f"https://api.mail.tm{download_url}")
                        response.raise_for_status()
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                        print(f"Attachment downloaded and saved to {file_path}.")  # Debugging
                    else:
                        print(f"No data or downloadUrl available for attachment: {filename}")  # Debugging
                        continue

                    # Create and pack the button for the attachment
                    btn = tk.Button(self.root, text=f"Open {filename}",
                                    command=lambda f=file_path: self.open_file(f))
                    btn.pack(pady=5)
                    print(f"Button added for {filename}")  # Debugging
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to process attachment: {e}")
                    print(f"Error processing attachment: {e}")  # Debugging

    def open_file(self, file_path):
        try:
            os.startfile(file_path)
            print(f"File opened: {file_path}")  # Debugging
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open file: {e}")
            print(f"Error opening file: {e}")  # Debugging


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = TempEmailApp(root)
    root.mainloop()