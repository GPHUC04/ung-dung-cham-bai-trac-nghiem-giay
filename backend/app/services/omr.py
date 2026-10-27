"""
services/omr.py — Core Engine Nhận diện OMR & Chấm bài trắc nghiệm (GV-03, GV-04, GV-05)

Quy trình xử lý ảnh phiếu trắc nghiệm OpenCV:
1. Tiền xử lý (Grayscale, Gaussian Blur, Adaptive Thresholding)
2. Phát hiện 4 điểm góc định vị (Fiducial Mark Corners)
3. Căn chỉnh góc nghiêng (Perspective Transform) đưa phiếu về kích thước chuẩn (1000 x 1400)
4. Trích xuất & giải mã vùng ô tô:
   - Số báo danh (SBD: 6 chữ số 0-9)
   - Mã đề thi (MD: 3 chữ số 0-9)
   - Đáp án học sinh (20 / 50 câu)
5. Tính tỉ lệ lấp đầy (Fill Density %) & Độ tin cậy (Confidence Score)
6. Phát hiện ô bất thường (tô đè nhiều ô, tẩy xóa dở dang, tô quá mờ) -> CoBatThuong = True
"""
import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any


class OMREngine:
    """OMR Processing Engine for Standard Answer Sheets"""

    # Kích thước chuẩn sau khi warp perspective
    WIDTH = 1000
    HEIGHT = 1400

    @staticmethod
    def preprocess_image(image_bytes: bytes) -> Tuple[np.ndarray, np.ndarray]:
        """Đọc bytes ảnh, chuyển xám, làm mịn và bẫy ngưỡng binary."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Không thể giải mã tệp ảnh.")

        # Rescale if image is excessively large to save RAM & CPU
        h, w = img.shape[:2]
        if max(h, w) > 2400:
            scale = 2400.0 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Ngưỡng nhị phân thích ứng (Adaptive Threshold)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        return img, thresh

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Sắp xếp 4 tọa độ góc theo thứ tự: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]      # Top-Left có tổng x+y nhỏ nhất
        rect[2] = pts[np.argmax(s)]      # Bottom-Right có tổng x+y lớn nhất

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]   # Top-Right có hiệu y-x nhỏ nhất
        rect[3] = pts[np.argmax(diff)]   # Bottom-Left có hiệu y-x lớn nhất
        return rect

    def align_document(self, img: np.ndarray, thresh: np.ndarray) -> np.ndarray:
        """
        Tìm 4 góc vuông định vị của phiếu trả lời và thực hiện Perspective Transform.
        Nếu không tìm thấy 4 góc rõ ràng, fallback sang resize chuẩn.
        """
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        doc_cnt = None
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(c) > (img.shape[0] * img.shape[1] * 0.2):
                doc_cnt = approx
                break

        if doc_cnt is not None:
            pts = doc_cnt.reshape(4, 2)
            rect = self.order_points(pts)
            dst = np.array([
                [0, 0],
                [self.WIDTH - 1, 0],
                [self.WIDTH - 1, self.HEIGHT - 1],
                [0, self.HEIGHT - 1]
            ], dtype="float32")

            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (self.WIDTH, self.HEIGHT))
            return warped
        else:
            # Fallback: Resize trực tiếp nếu góc không được phát hiện rõ
            return cv2.resize(img, (self.WIDTH, self.HEIGHT))

    def evaluate_bubble(self, thresh_crop: np.ndarray) -> float:
        """Tính tỉ lệ phần trăm pixel đen (tô mực) trong một ô tròn trắc nghiệm."""
        total_pixels = thresh_crop.shape[0] * thresh_crop.shape[1]
        if total_pixels == 0:
            return 0.0
        filled_pixels = cv2.countNonZero(thresh_crop)
        return float(filled_pixels / total_pixels)

    def process_sheet(
        self,
        image_bytes: bytes,
        so_cau_hoi: int = 50
    ) -> Dict[str, Any]:
        """
        Quy trình xử lý full phiếu:
        - Nhận diện Số báo danh (6 chữ số)
        - Nhận diện Mã đề thi (3 chữ số)
        - Nhận diện Đáp án tô (A/B/C/D) từng câu
        - Đánh giá độ tin cậy & phát hiện ô bất thường
        """
        img, thresh = self.preprocess_image(image_bytes)
        warped = self.align_document(img, thresh)

        # Chuyển warped sang binarythresh để quét ô
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        _, warped_thresh = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # --- 1. NHẬN DIỆN SỐ BÁO DANH (SBD: 6 CỘT x 10 HÀNG) ---
        # Tọa độ vùng SBD chuẩn trên ảnh warped 1000x1400
        sbd_x, sbd_y, sbd_w, sbd_h = 500, 100, 300, 250
        sbd_crop = warped_thresh[sbd_y:sbd_y + sbd_h, sbd_x:sbd_x + sbd_w]

        recognized_sbd = ""
        sbd_cols = 6
        cell_w = sbd_w // sbd_cols
        cell_h = sbd_h // 10

        for col in range(sbd_cols):
            max_fill = 0.0
            best_digit = 0
            for digit in range(10):
                x1 = col * cell_w
                y1 = digit * cell_h
                cell = sbd_crop[y1:y1 + cell_h, x1:x1 + cell_w]
                fill = self.evaluate_bubble(cell)
                if fill > max_fill:
                    max_fill = fill
                    best_digit = digit
            recognized_sbd += str(best_digit) if max_fill > 0.25 else "0"

        # --- 2. NHẬN DIỆN MÃ ĐỀ THI (MD: 3 CỘT x 10 HÀNG) ---
        md_x, md_y, md_w, md_h = 820, 100, 150, 250
        md_crop = warped_thresh[md_y:md_y + md_h, md_x:md_x + md_w]

        recognized_md = ""
        md_cols = 3
        cell_w = md_w // md_cols
        cell_h = md_h // 10

        for col in range(md_cols):
            max_fill = 0.0
            best_digit = 0
            for digit in range(10):
                x1 = col * cell_w
                y1 = digit * cell_h
                cell = md_crop[y1:y1 + cell_h, x1:x1 + cell_w]
                fill = self.evaluate_bubble(cell)
                if fill > max_fill:
                    max_fill = fill
                    best_digit = digit
            recognized_md += str(best_digit) if max_fill > 0.25 else "1"

        # --- 3. NHẬN DIỆN ĐÁP ÁN CÁC CÂU HỎI ---
        # Vùng đáp án chính bắt đầu từ y=400 đến y=1300
        # Được chia làm 2 cột câu (Mỗi cột chứa 25 câu)
        answers = {}
        confidence_scores = {}
        abnormal_flags = {}

        options_letters = ["A", "B", "C", "D"]

        # Giả định bố cục 2 cột (Cột 1: Câu 1-25; Cột 2: Câu 26-50)
        col_width = 400
        col_height = 850
        start_y = 420

        columns = [
            {"x": 60, "start_q": 1, "count": min(25, so_cau_hoi)},
            {"x": 520, "start_q": 26, "count": max(0, so_cau_hoi - 25)}
        ]

        for col_info in columns:
            if col_info["count"] <= 0:
                continue

            q_h = col_height // 25
            opt_w = col_width // 4

            for i in range(col_info["count"]):
                q_num = col_info["start_q"] + i
                q_y = start_y + i * q_h

                fills = []
                for opt_idx in range(4):
                    opt_x = col_info["x"] + opt_idx * opt_w
                    cell = warped_thresh[q_y:q_y + q_h, opt_x:opt_x + opt_w]
                    fill = self.evaluate_bubble(cell)
                    fills.append(fill)

                # Đánh giá kết quả tô câu hỏi
                filled_indices = [idx for idx, f in enumerate(fills) if f >= 0.35]

                if len(filled_indices) == 1:
                    chosen_idx = filled_indices[0]
                    answers[q_num] = options_letters[chosen_idx]
                    confidence_scores[q_num] = min(1.0, round(fills[chosen_idx] / 0.70, 2))
                    abnormal_flags[q_num] = False
                elif len(filled_indices) > 1:
                    # Tô nhiều ô! Bất thường!
                    best_idx = int(np.argmax(fills))
                    answers[q_num] = options_letters[best_idx]
                    confidence_scores[q_num] = 0.40
                    abnormal_flags[q_num] = True
                else:
                    # Chưa tô (hoặc tô mờ < 0.35)
                    best_idx = int(np.argmax(fills))
                    if fills[best_idx] >= 0.20:
                        # Tô mờ dở dang
                        answers[q_num] = options_letters[best_idx]
                        confidence_scores[q_num] = round(fills[best_idx], 2)
                        abnormal_flags[q_num] = True
                    else:
                        # Bỏ trống
                        answers[q_num] = None
                        confidence_scores[q_num] = 1.0
                        abnormal_flags[q_num] = False

        return {
            "so_bao_danh": recognized_sbd,
            "ma_de": recognized_md,
            "dap_an_da_chon": answers,
            "do_tin_cay": confidence_scores,
            "co_bat_thuong": abnormal_flags,
            "has_any_abnormal": any(abnormal_flags.values())
        }


omr_engine = OMREngine()
