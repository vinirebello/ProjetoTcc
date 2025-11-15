import cv2
import pytesseract

img = cv2.imread('imagetest.png')

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

txt = pytesseract.image_to_string(img)

print(txt)