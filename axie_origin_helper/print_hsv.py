import cv2

img = cv2.imread("test_images/window1.png")
if img is None:
    raise FileNotFoundError("找不到图片文件，请检查路径。")

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        H, S, V = hsv[y, x]
        print(f"Clicked at (x={x}, y={y})  ->  HSV = ({int(H)}, {int(S)}, {int(V)})")

        # 在图上画个圈并显示文字
        disp = img.copy()
        cv2.circle(disp, (x, y), 5, (0, 255, 255), 2)  # 画圈（BGR的黄）
        cv2.putText(disp, f"({x},{y}) HSV=({int(H)},{int(S)},{int(V)})",
                    (x+10, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)
        cv2.imshow("Image (click to read HSV)", disp)

cv2.namedWindow("Image (click to read HSV)")
cv2.setMouseCallback("Image (click to read HSV)", on_mouse)
cv2.imshow("Image (click to read HSV)", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
