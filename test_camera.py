import cv2

cap = cv2.VideoCapture(0)   # change 0 to 1 if you want the other camera
print("Camera window opening. Click on the window, then press SPACE to take a photo, or Q to quit.")

while True:
    ok, frame = cap.read()
    if not ok:
        print("Could not read from camera")
        break
    cv2.imshow("Camera", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord(" "):
        cv2.imwrite("bottle.jpg", frame)
        print("Saved bottle.jpg")
        break
    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()