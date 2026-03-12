import easyocr
import re
import cv2

class OCRReader:

    def __init__(self):

        # Load OCR model only once
        self.reader = easyocr.Reader(['en'], gpu=False)


    def clean_plate(self, text):

        """
        Clean OCR text to keep only valid plate characters
        """

        text = text.upper()

        # Remove anything not A-Z or 0-9
        text = re.sub(r'[^A-Z0-9]', '', text)

        return text


    def read_plate(self, image):

        if image is None or image.size == 0:
            return None

        # Resize plate image for faster OCR
        plate = cv2.resize(image, (200, 80))

        results = self.reader.readtext(plate)

        if not results:
            return None

        best_text = ""
        best_conf = 0

        for bbox, text, confidence in results:

            if confidence > best_conf:
                best_text = text
                best_conf = confidence

        cleaned_text = self.clean_plate(best_text)

        # Reject very short results (noise)
        if len(cleaned_text) < 5:
            return None

        return cleaned_text