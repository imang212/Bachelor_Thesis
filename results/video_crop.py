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

cv2.rectangle(cropped_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 255, 0), 4)
cv2.putText(cropped_frame, f"ROI Zone", (roi_x, roi_y - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# ----------------------------------------------------------------
## Kótování: vzdálenost ROI od levého a horního okraje výřezu
#def put_text_outline(img, text, org, scale, color, thickness):
#    # černý obrys kvůli čitelnosti nad světlým pozadím
#    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
#    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)
# 
#dim_color = (0, 255, 0)
# 
## Vodorovná kóta: od levého okraje (x=0) k levé hraně ROI, uprostřed výšky ROI
#mid_y = roi_y + roi_h // 2
#cv2.arrowedLine(cropped_frame, (6, mid_y), (roi_x, mid_y), dim_color, 2, tipLength=0.2)
#cv2.arrowedLine(cropped_frame, (roi_x, mid_y), (6, mid_y), dim_color, 2, tipLength=0.2)
#put_text_outline(cropped_frame, f"x={roi_x} px", (25, mid_y - 16), 0.5, dim_color, 2)
# 
## Svislá kóta: od horního okraje (y=0) k horní hraně ROI, uprostřed levého okraje
#dim_x = roi_x // 2 + 160
#cv2.arrowedLine(cropped_frame, (dim_x, 6), (dim_x, roi_y), dim_color, 2, tipLength=0.03)
#cv2.arrowedLine(cropped_frame, (dim_x, roi_y), (dim_x, 6), dim_color, 2, tipLength=0.03)
#put_text_outline(cropped_frame, f"y={roi_y} px", (dim_x + 10, roi_y // 2), 0.6, dim_color, 2)


# Červené ohraničení celého výřezu (YOLO vstup 640x640), kreslí se těsně dovnitř obrazu
cv2.rectangle(cropped_frame, (2, 2), (637, 637), (0, 0, 255), 4)

# 5. Spojení do jedné koláže
# Protože levý obrázek má na výšku 720 a pravý 640, musíme levý zmenšit, aby k sobě pasovaly.
vis_resized = cv2.resize(visualization_frame, (int(640 * 1280 / 720), 640))

final_img = cv2.hconcat([vis_resized, cropped_frame])

cv2.imwrite('preprocessing_gstreamer_final.jpg', final_img)
print("Hotovo! Uloženo jako preprocessing_gstreamer_final.jpg")