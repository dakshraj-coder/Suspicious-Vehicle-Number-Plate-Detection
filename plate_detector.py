
import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk
from dotenv import load_dotenv
from google import genai
from google.genai import errors


# ==========================================
# 1. GEMINI CONFIGURATION
# ==========================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Please check your .env file."
    )

client = genai.Client(api_key=api_key)

# Confirm this model ID is available to your API key.
MODEL_NAME = "gemini-3.5-flash"


# ==========================================
# 2. VEHICLE WATCHLIST
# ==========================================

watchlist = [
    "KA 64 N 0099",
    "TS10EL9988",
    "KA01MJ4521",
]


def normalize_plate(plate):
    """Remove spaces and punctuation for comparison."""
    return "".join(
        character
        for character in plate.upper()
        if character.isalnum()
    )


# ==========================================
# 3. MAIN APPLICATION
# ==========================================

class PlateApp:

    def __init__(self, master):
        self.master = master

        master.title("Vehicle Number Plate Detector")
        master.geometry("520x560")
        master.resizable(False, False)

        self.label = tk.Label(
            master,
            text="Suspicious Vehicle Number Plate Detection",
            font=("Arial", 14, "bold"),
            wraplength=480,
        )
        self.label.pack(pady=15)

        self.image_label = tk.Label(master)
        self.image_label.pack(pady=10)

        self.result_label = tk.Label(
            master,
            text="Choose a vehicle image to begin.",
            font=("Arial", 12),
            wraplength=470,
            justify="center",
        )
        self.result_label.pack(pady=15)

        self.upload_button = tk.Button(
            master,
            text="Choose Vehicle Image",
            font=("Arial", 12),
            command=self.upload_image,
        )
        self.upload_button.pack(pady=15)

    # ======================================
    # 4. SELECT AND DISPLAY IMAGE
    # ======================================

    def upload_image(self):

        file_path = filedialog.askopenfilename(
            title="Select Vehicle Image",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png"),
            ],
        )

        if not file_path:
            return

        try:
            with Image.open(file_path) as original:
                display_image = original.convert("RGB")
                display_image.thumbnail((350, 300))

            photo = ImageTk.PhotoImage(display_image)

            self.image_label.config(image=photo)
            self.image_label.image = photo

        except Exception as error:
            messagebox.showerror(
                "Image Error",
                f"Could not open the selected image:\n{error}",
            )
            return

        self.upload_button.config(state=tk.DISABLED)
        self.result_label.config(
            text="Analyzing vehicle image...",
            fg="blue",
        )
        self.master.update_idletasks()

        # Schedule processing without blocking the initial UI update.
        self.master.after(
            100,
            lambda: self.analyze_image(file_path),
        )

    # ======================================
    # 5. ANALYZE NUMBER PLATE
    # ======================================

    def analyze_image(self, file_path):

        try:
            with Image.open(file_path) as original:
                image_for_ai = original.convert("RGB")

            prompt = """
            Read the Indian vehicle registration number plate
            visible in this image.

            Instructions:
            - Return only the registration number.
            - Do not include explanations or markdown.
            - Do not guess unclear characters.
            - Preserve the letters and digits accurately.
            - If the plate cannot be read, return exactly:
              Number plate not readable.
            """

            # One API call: the SDK handles certain transient retries.
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, image_for_ai],
            )

            plate_text = (response.text or "").strip()
            cleaned_plate = plate_text.strip("\"'").upper()

            print("Extracted plate:", repr(cleaned_plate))

            if (
                not cleaned_plate
                or "NUMBER PLATE NOT READABLE" in cleaned_plate
            ):
                self.result_label.config(
                    text="Number plate not readable.",
                    fg="orange",
                )
                return

            detected = normalize_plate(cleaned_plate)

            normalized_watchlist = {
                normalize_plate(plate)
                for plate in watchlist
            }

            # ==================================
            # 6. WATCHLIST COMPARISON
            # ==================================

            if detected in normalized_watchlist:

                self.result_label.config(
                    text=(
                        f"Watchlist Match: {cleaned_plate}\n"
                        "Please verify the result."
                    ),
                    fg="red",
                    font=("Arial", 12, "bold"),
                )

                messagebox.showwarning(
                    "Watchlist Match",
                    f"The detected plate matches an entry "
                    f"in the configured watchlist:\n\n"
                    f"{cleaned_plate}\n\n"
                    "Verify the plate manually.",
                )

            else:

                self.result_label.config(
                    text=(
                        f"Plate Number: {cleaned_plate}\n"
                        "No watchlist match found."
                    ),
                    fg="green",
                    font=("Arial", 12),
                )

        # ======================================
        # 7. ERROR HANDLING
        # ======================================

        except errors.APIError as error:

            if error.code == 503:
                error_message = (
                    "Gemini is temporarily overloaded.\n"
                    "Please wait a few minutes and try again."
                )
                self.result_label.config(
                    text=error_message,
                    fg="orange",
                )
                print("Gemini service is temporarily unavailable:", error)

            elif error.code == 429:
                error_message = (
                    "Gemini API quota or rate limit reached.\n"
                    "Check your API usage and limits."
                )
                self.result_label.config(
                    text=error_message,
                    fg="orange",
                )
                print("Gemini rate limit:", error)

            else:
                self.result_label.config(
                    text=f"Gemini API error: {error}",
                    fg="red",
                )
                print("Gemini API error:", error)

        except Exception as error:

            self.result_label.config(
                text=f"An error occurred:\n{error}",
                fg="red",
            )
            print("Application error:", error)

        finally:
            self.upload_button.config(state=tk.NORMAL)


# ==========================================
# 8. START APPLICATION
# ==========================================

if __name__ == "__main__":

    root = tk.Tk()
    app = PlateApp(root)
    root.mainloop()
