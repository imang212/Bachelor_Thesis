import cv2
import numpy as np

# 1. Načtení surového videa (bez detekcí)
cap = cv2.VideoCapture('outputx264-202601091552_default.mp4') 
cap.set(cv2.CAP_PROP_POS_FRAMES, 50)  # Vybere 50. snímek
ret, frame = cap.read()
cap.release()

if not ret:
    print("Chyba: Nepodařilo se načíst video.")
    exit()

# 2. Simulace kroku: ! videoscale ! video/x-raw,width=1280,height=720
scaled_frame = cv2.resize(frame, (1280, 720))

# 3. Vykreslení oblasti, kde proběhne ořez (jen pro vizualizaci doleva)
visualization_frame = scaled_frame.copy()
# Souřadnice pro vykreslení: (left, top), (right, bottom)
# right = 1280 - 440 = 840, bottom = 720 - 0 = 720
cv2.rectangle(visualization_frame, (200, 80), (840, 720), (0, 0, 255), 4)
cv2.putText(visualization_frame, "Video Crop", (210, 120), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

# 4. Simulace kroku: ! videocrop top=80 left=200 right=440 bottom=0
# V Pythonu to je výřez pole [y_start:y_end, x_start:x_end]
cropped_frame = scaled_frame[80:720, 200:840] 

# Přidáme popisek i na výsledný výřez
cv2.putText(cropped_frame, "YOLO Input (640x640)", (20, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 1, (55, 200, 0), 3)

# --- NOVÁ ČÁST: Vykreslení aplikační ROI zóny přímo do výřezu ---
roi_x = int(640 * 0.15)
roi_y = int(640 * 0.85)
roi_w = int(640 * 0.35)
roi_h = int(640 * 0.14)

# Vykreslení zeleného obdélníku s popiskem
cv2.rectangle(cropped_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 4)
cv2.putText(cropped_frame, "ROI Zone", (roi_x, roi_y - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
# ----------------------------------------------------------------

# 5. Spojení do jedné koláže
# Protože levý obrázek má na výšku 720 a pravý 640, musíme levý zmenšit, aby k sobě pasovaly.
vis_resized = cv2.resize(visualization_frame, (int(640 * 1280 / 720), 640))

final_img = cv2.hconcat([vis_resized, cropped_frame])

cv2.imwrite('preprocessing_gstreamer_final.jpg', final_img)
print("Hotovo! Uloženo jako preprocessing_gstreamer_final.jpg")