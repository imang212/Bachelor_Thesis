import cv2

frame_numbers = [300, 330, 360, 390]

cap = cv2.VideoCapture('analysed_recording_20260218_113609_gpu.mp4')
frames = []

for fn in frame_numbers:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
    ret, frame = cap.read()
    if ret:
        h, w, _ = frame.shape
        crop_start_y = int(h * 0.65) 
        cropped_frame = frame[crop_start_y:h, int(w*0.065):int(w*0.9)]
        
        text = f"Frame: {fn}"
        cv2.putText(cropped_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(cropped_frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Přidání hotového snímku do seznamu pro pozdější spojení
        frames.append(cropped_frame)

cap.release()

# Spojení snímků do mřížky 2x2
if len(frames) == 4:
    # Horizontální spojení (vedle sebe)
    row1 = cv2.hconcat([frames[0], frames[1]])
    row2 = cv2.hconcat([frames[2], frames[3]])
    
    # Vertikální spojení řádků (pod sebe)
    final_grid = cv2.vconcat([row1, row2])
    
    # Uložení finálního obřího obrázku do bezztrátového PNG
    output_filename = 'tracking_grid_final.png'
    cv2.imwrite(output_filename, final_grid)
    print(f"Mřížka byla úspěšně uložena jako {output_filename} v maximální kvalitě.")
else:
    print(f"Chyba: Načteno pouze {len(frames)} ze 4 snímků.")