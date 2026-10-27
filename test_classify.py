import sys, cv2
from segbin import classify

frame = cv2.imread(sys.argv[1])
print(classify(frame))