import sys, os, time, csv, json, shutil, traceback
import cv2
from ultralytics import YOLO

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QGridLayout,
    QMessageBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QSlider,
)
from PySide6.QtCore import QTimer, Qt, QPoint, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor


# =========================
# CONFIG & PATHS
# =========================
def resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


DETECTOR_PATH = resource_path("detector.pt")
CLASSIFIER_PATH = resource_path("classify.pt")

SAVE_DIR = "saved_images"
ERROR_DIR = os.path.join(SAVE_DIR, "errors")
LOG_DIR = "logs"
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(ERROR_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

CSV_PATH = os.path.join(LOG_DIR, "results.csv")
BACKUP_EVERY = 100  # backup system: every 100 items

# --- PARAMETERS ---
CAM_INDEX = 0
DET_CONF = 0.30
CONF_GREEN = 0.90
CONF_YELLOW = 0.70
STABILITY_FRAMES = 3
TRACK_TTL_SEC = 2.0

DEFAULT_ZONE = (100, 100, 500, 400)

# =========================
# STYLESHEET
# =========================
STYLESHEET = """
QWidget { background-color: #1e1e24; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
QFrame#Card { background-color: #2b2b36; border-radius: 14px; border: 1px solid #3a3a45; }
QLabel#CamDisplay { background-color: #000; border: 2px solid #444; border-radius: 10px; }
QLabel#Title { color: #a0a0ff; font-size: 16px; font-weight: bold; }
QLabel#ResultHuge { color: #fff; font-size: 44px; font-weight: 900; padding: 8px; }
QPushButton { background-color: #3e3e4a; color: white; border-radius: 10px; padding: 12px; font-weight: 900; border: none; }
QPushButton:hover { background-color: #4e4e5b; }
QPushButton#BtnConfirm { background-color: #2e7d32; }
QPushButton#BtnConfirm:hover { background-color: #388e3c; }
QPushButton#BtnReject { background-color: #c62828; }
QPushButton#BtnReject:hover { background-color: #d32f2f; }
QPushButton#BtnBrowse { background-color: #ff9800; color: black; }
QPushButton#BtnDraw { background-color: #0288d1; color: white; }
QPushButton#BtnDraw:checked { background-color: #01579b; border: 2px solid #81d4fa; }
QPushButton#BtnStartStop { background-color: #424242; }
QPushButton#BtnReport { background-color: #607d8b; }
QTableWidget { background-color: #2b2b36; gridline-color: #444; border: none; border-radius: 10px; }
QHeaderView::section { background-color: #333; color: #fff; border: none; padding: 6px; font-weight: 800; }
QSlider::groove:horizontal { height: 10px; border-radius: 5px; background: #444; }
QSlider::handle:horizontal { width: 18px; margin: -6px 0; border-radius: 9px; background: #ddd; }
"""


# =========================
# CUSTOM WIDGET: Drawable Label
# =========================
class DrawableLabel(QLabel):
    """QLabel ที่สามารถลากเมาส์เพื่อวาดกรอบสี่เหลี่ยมได้"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.current_rect = QRect()
        self.is_draw_mode = False
        self.on_zone_selected = None

    def mousePressEvent(self, event):
        if self.is_draw_mode and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.current_rect = QRect(self.start_point, self.end_point)
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and self.is_draw_mode:
            self.end_point = event.pos()
            self.current_rect = QRect(self.start_point, self.end_point).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing and self.is_draw_mode and event.button() == Qt.LeftButton:
            self.drawing = False
            self.current_rect = QRect(self.start_point, event.pos()).normalized()
            if self.on_zone_selected:
                self.on_zone_selected(self.current_rect)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_draw_mode and not self.current_rect.isNull():
            painter = QPainter(self)
            pen = QPen(QColor(0, 255, 255), 3, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.current_rect)


# =========================
# HELPER CLASS (Smart Cam)
# =========================
class SmartCam:
    def __init__(self, src=0):
        self.cap = None
        self.set_source(src)

    def set_source(self, src):
        self.src = src
        self.is_image = False
        self.static_frame = None
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
        self.cap = None

        if isinstance(src, str) and src.lower().endswith((".jpg", ".png", ".jpeg")):
            self.is_image = True
            img = cv2.imread(src)
            self.static_frame = img if img is not None else None
            self.is_connected = self.static_frame is not None
        else:
            self.cap = (
                cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
                if isinstance(self.src, int)
                else cv2.VideoCapture(self.src)
            )
            self.is_connected = self.cap.isOpened()

    def read(self):
        if self.is_image:
            return (
                (True, self.static_frame.copy())
                if self.static_frame is not None
                else (False, None)
            )

        if self.cap is None or not self.cap.isOpened():
            self.is_connected = False
            return False, None

        ret, frame = self.cap.read()

        if not ret and isinstance(self.src, str):  # Loop video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if not ret:
            self.is_connected = False
            return False, None

        self.is_connected = True
        return True, frame

    def reconnect(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except:
            pass
        time.sleep(0.2)
        self.cap = (
            cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
            if isinstance(self.src, int)
            else cv2.VideoCapture(self.src)
        )
        self.is_connected = self.cap.isOpened()
        return self.is_connected

    def release(self):
        try:
            if self.cap:
                self.cap.release()
        except:
            pass


# =========================
# MAIN APP
# =========================
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oil Palm Sorting (Production UI)")
        self.resize(1320, 840)
        self.setStyleSheet(STYLESHEET)

        # State
        self.tracks = {}
        self.frame_count = 0
        self.pending_tid = None
        self.zone = DEFAULT_ZONE
        self.prev_time = time.time()
        self.video_dims = (640, 480)
        self.last_frame = None

        self.is_running = True
        self.session_started_at = time.time()
        self.session_counts_start = {}
        self.log_total = 0

        self.last_reconnect_try = 0.0
        self.reconnect_interval = 1.0  # seconds

        # Speed control (Fast <-> Accurate)
        # 1 = FAST (skip high, imgsz low), 10 = ACCURATE (skip low, imgsz high)
        self.speed_level = 6
        self.proc_skip = 3
        self.proc_imgsz = 416

        # --- ลบบรรทัดนี้ออกครับ เพราะ UI ยังไม่สร้าง ---
        # self.apply_speed(self.speed_level)
        # ----------------------------------------

        # Load Models
        try:
            self.detector = YOLO(DETECTOR_PATH)
            self.classifier = YOLO(CLASSIFIER_PATH)
            self.class_names = (
                self.classifier.names
                if hasattr(self.classifier, "names")
                else {0: "Unripe", 1: "Ripe", 2: "Overripe"}
            )
        except Exception as ex:
            print("Warning: Model not found. Running in UI Test Mode.")
            print(ex)
            self.detector = None
            self.classifier = None
            self.class_names = {0: "Unripe", 1: "Ripe", 2: "Overripe"}

        # counts init
        self.counts = {name: 0 for _, name in self.class_names.items()}
        self.session_counts_start = self.counts.copy()

        # CSV init
        if not os.path.exists(CSV_PATH):
            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(
                    ["Timestamp", "ID", "Class", "Conf", "Decision", "Latency"]
                )

        self.setup_ui()  # สร้าง UI (รวมถึง lbl_speed) ตรงนี้

        self.apply_speed(self.speed_level)  # เรียกตรงนี้ถูกต้องแล้ว (เพราะ UI เสร็จแล้ว)

        # camera
        self.cam = SmartCam(CAM_INDEX)

        # timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_loop)
        self.timer.start(10)

        self.set_status("ok", "READY")

    # =========================
    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # --- Left Panel ---
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        l_layout = QVBoxLayout(left_panel)

        # Toolbar row 1
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("🎥 INPUT:"))

        btn_live = QPushButton("📷 Live")
        btn_live.setFixedWidth(90)
        btn_live.clicked.connect(lambda: self.change_source(CAM_INDEX))

        btn_browse = QPushButton("📁 File")
        btn_browse.setFixedWidth(90)
        btn_browse.setObjectName("BtnBrowse")
        btn_browse.clicked.connect(self.browse_file)

        self.btn_startstop = QPushButton("⏸ STOP")
        self.btn_startstop.setObjectName("BtnStartStop")
        self.btn_startstop.setFixedWidth(110)
        self.btn_startstop.clicked.connect(self.toggle_run)

        row1.addWidget(btn_live)
        row1.addWidget(btn_browse)
        row1.addWidget(self.btn_startstop)
        row1.addStretch()

        # Status light + text
        self.status_light = QLabel("")
        self.status_light.setFixedSize(18, 18)
        self.status_light.setStyleSheet(
            "background:#00c853; border-radius:9px; border: 1px solid #111;"
        )

        self.lbl_status = QLabel("READY")
        self.lbl_status.setStyleSheet("font-weight: 800;")

        row1.addWidget(self.status_light)
        row1.addWidget(self.lbl_status)

        # Toolbar row 2 (zone + sound)
        row2 = QHBoxLayout()

        self.chk_use_zone = QCheckBox("Active Zone")
        self.chk_use_zone.setChecked(True)

        self.btn_draw_zone = QPushButton("✏️ Draw Zone")
        self.btn_draw_zone.setCheckable(True)
        self.btn_draw_zone.setObjectName("BtnDraw")
        self.btn_draw_zone.clicked.connect(self.toggle_draw_mode)

        self.chk_sound = QCheckBox("Sound")
        self.chk_sound.setChecked(True)

        row2.addWidget(self.chk_use_zone)
        row2.addWidget(self.btn_draw_zone)
        row2.addStretch()
        row2.addWidget(self.chk_sound)

        # Speed control
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("🎚️ Speed: Fast"))
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setMinimum(1)
        self.sld_speed.setMaximum(10)
        self.sld_speed.setValue(self.speed_level)
        self.sld_speed.valueChanged.connect(self.on_speed_changed)
        speed_row.addWidget(self.sld_speed)
        self.lbl_speed = QLabel("Accurate")
        speed_row.addWidget(self.lbl_speed)

        # Cam Display
        self.lbl_cam = DrawableLabel()
        self.lbl_cam.setObjectName("CamDisplay")
        self.lbl_cam.setFixedSize(860, 520)
        self.lbl_cam.setAlignment(Qt.AlignCenter)
        self.lbl_cam.on_zone_selected = self.finish_drawing_zone

        # Logs
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Class", "Conf", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(170)

        l_layout.addLayout(row1)
        l_layout.addLayout(row2)
        l_layout.addLayout(speed_row)
        l_layout.addWidget(self.lbl_cam)
        l_layout.addWidget(QLabel("📋 Activity Log"))
        l_layout.addWidget(self.table)

        # --- Right Panel ---
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setFixedWidth(420)
        r_layout = QVBoxLayout(right_panel)

        self.lbl_result = QLabel("READY")
        self.lbl_result.setObjectName("ResultHuge")
        self.lbl_result.setAlignment(Qt.AlignCenter)

        self.lbl_conf = QLabel("-")
        self.lbl_conf.setAlignment(Qt.AlignCenter)
        self.lbl_conf.setStyleSheet("font-size: 18px; font-weight: 800;")

        self.lbl_fps = QLabel("FPS: 0")
        self.lbl_fps.setStyleSheet("color:#aaa;")

        self.chk_assist = QCheckBox("Assisted Mode")
        self.chk_assist.setChecked(True)

        self.btn_confirm = QPushButton("✔ CONFIRM  (Space)")
        self.btn_confirm.setObjectName("BtnConfirm")
        self.btn_confirm.setMinimumHeight(62)
        self.btn_confirm.clicked.connect(self.action_confirm)

        self.btn_reject = QPushButton("✖ REJECT   (Enter)")
        self.btn_reject.setObjectName("BtnReject")
        self.btn_reject.setMinimumHeight(62)
        self.btn_reject.clicked.connect(self.action_reject)

        self.btn_report = QPushButton("🧾 Daily Report / Export")
        self.btn_report.setObjectName("BtnReport")
        self.btn_report.clicked.connect(self.export_daily_report)

        # Stats
        self.grid_stats = QGridLayout()
        self.lbl_counts = {}
        for i, (_, name) in enumerate(self.class_names.items()):
            l_val = QLabel("0 (0.0%)")
            l_val.setStyleSheet("font-weight: 900; font-size: 18px;")
            self.grid_stats.addWidget(QLabel(f"{name}:"), i, 0)
            self.grid_stats.addWidget(l_val, i, 1)
            self.lbl_counts[name] = l_val

        self.lbl_total = QLabel("Total: 0")
        self.lbl_total.setStyleSheet(
            "font-weight: 900; font-size: 16px; color:#cfd8dc;"
        )

        r_layout.addWidget(QLabel("Last Detection:"))
        r_layout.addWidget(self.lbl_result)
        r_layout.addWidget(self.lbl_conf)
        r_layout.addSpacing(10)
        r_layout.addWidget(self.chk_assist)
        r_layout.addWidget(self.btn_confirm)
        r_layout.addWidget(self.btn_reject)
        r_layout.addSpacing(10)
        r_layout.addWidget(self.btn_report)
        r_layout.addSpacing(10)
        r_layout.addWidget(QLabel("Real-time Stats:"))
        r_layout.addLayout(self.grid_stats)
        r_layout.addWidget(self.lbl_total)
        r_layout.addStretch()
        r_layout.addWidget(self.lbl_fps)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    # =========================
    # SPEED CONTROL
    # =========================
    def on_speed_changed(self, val: int):
        self.speed_level = val
        self.apply_speed(val)

    def apply_speed(self, level: int):
        # level 1 -> FAST : skip 8, imgsz 320
        # level 10 -> ACCURATE : skip 1, imgsz 640
        skip = int(round(8 - (level - 1) * (7 / 9)))
        imgsz = int(round(320 + (level - 1) * (320 / 9)))
        self.proc_skip = max(1, skip)
        self.proc_imgsz = max(256, min(960, imgsz))
        self.lbl_speed.setText(
            f"Accurate (skip={self.proc_skip}, imgsz={self.proc_imgsz})"
        )

    # =========================
    # STATUS / SOUND / SCREENSHOT
    # =========================
    def set_status(self, mode: str, text: str):
        # mode: ok, pending, error, stopped
        self.lbl_status.setText(text)
        if mode == "ok":
            self.status_light.setStyleSheet(
                "background:#00c853; border-radius:9px; border: 1px solid #111;"
            )
        elif mode == "pending":
            self.status_light.setStyleSheet(
                "background:#ffea00; border-radius:9px; border: 1px solid #111;"
            )
        elif mode == "error":
            self.status_light.setStyleSheet(
                "background:#ff1744; border-radius:9px; border: 1px solid #111;"
            )
        elif mode == "stopped":
            self.status_light.setStyleSheet(
                "background:#9e9e9e; border-radius:9px; border: 1px solid #111;"
            )
        else:
            self.status_light.setStyleSheet(
                "background:#607d8b; border-radius:9px; border: 1px solid #111;"
            )

    def play_tone(self, kind: str):
        if not self.chk_sound.isChecked():
            return

        # Windows: winsound.Beep for different tones
        try:
            import winsound

            tones = {
                "auto": (900, 120),
                "manual_wait": (650, 120),
                "manual_ok": (1000, 160),
                "reject": (450, 160),
                "error": (300, 250),
            }
            freq, dur = tones.get(kind, (800, 100))
            winsound.Beep(freq, dur)
            return
        except Exception:
            pass

        # Fallback: simple beep
        try:
            QApplication.beep()
        except Exception:
            pass

    def autoscreenshot(self, reason: str):
        if self.last_frame is None:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{reason}.jpg".replace(" ", "_")
        path = os.path.join(ERROR_DIR, fname)
        try:
            cv2.imwrite(path, self.last_frame)
        except Exception:
            pass

    # =========================
    # SESSION CONTROL
    # =========================
    def toggle_run(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_startstop.setText("⏸ STOP")
            self.timer.start(10)
            self.set_status("ok", "RUNNING")
        else:
            self.timer.stop()
            self.btn_startstop.setText("▶ START")
            self.set_status("stopped", "STOPPED")
            self.show_session_summary()

    def show_session_summary(self):
        # summarize session since last start
        dur = int(time.time() - self.session_started_at)
        total = sum(self.counts.values())
        lines = [f"Session Duration: {dur//60:02d}:{dur%60:02d}", f"Total: {total}"]
        for k, v in self.counts.items():
            lines.append(f"- {k}: {v}")
        QMessageBox.information(self, "Session Summary", "\n".join(lines))

    # =========================
    # ZONE DRAWING LOGIC
    # =========================
    def toggle_draw_mode(self):
        if self.btn_draw_zone.isChecked():
            self.lbl_cam.is_draw_mode = True
            self.lbl_cam.setCursor(Qt.CrossCursor)
            self.timer.stop()
            QMessageBox.information(
                self,
                "Draw Zone",
                "ลากเมาส์บนหน้าจอเพื่อกำหนดพื้นที่นับสินค้า\n(Drag mouse to draw zone)",
            )
        else:
            self.lbl_cam.is_draw_mode = False
            self.lbl_cam.setCursor(Qt.ArrowCursor)
            if self.is_running:
                self.timer.start(10)

    def finish_drawing_zone(self, rect_ui: QRect):
        ui_w, ui_h = self.lbl_cam.width(), self.lbl_cam.height()
        vid_w, vid_h = self.video_dims

        scale_x = vid_w / ui_w
        scale_y = vid_h / ui_h

        x1 = int(rect_ui.left() * scale_x)
        y1 = int(rect_ui.top() * scale_y)
        x2 = int(rect_ui.right() * scale_x)
        y2 = int(rect_ui.bottom() * scale_y)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(vid_w, x2), min(vid_h, y2)

        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            QMessageBox.warning(self, "Zone", "Zone เล็กเกินไป ลองวาดใหม่อีกครั้ง")
            return

        self.zone = (x1, y1, x2, y2)

        self.btn_draw_zone.setChecked(False)
        self.lbl_cam.is_draw_mode = False
        self.lbl_cam.setCursor(Qt.ArrowCursor)
        if self.is_running:
            self.timer.start(10)

        self.set_status("ok", f"ZONE OK ({x1},{y1})-({x2},{y2})")

    # =========================
    # RUN LOOP
    # =========================
    def run_loop(self):
        if not self.is_running:
            return

        t0 = time.time()

        try:
            ret, frame = self.cam.read()
            if not ret or frame is None:
                self.handle_cam_disconnect()
                return

            self.last_frame = frame.copy()

            h, w = frame.shape[:2]
            self.video_dims = (w, h)

            self.frame_count += 1

            detections = []
            if self.detector and (self.frame_count % self.proc_skip == 0):
                results = self.detector.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    imgsz=self.proc_imgsz,
                    verbose=False,
                    conf=DET_CONF,
                )
                if results and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    ids = results[0].boxes.id.cpu().numpy().astype(int)
                    for b, tid in zip(boxes, ids):
                        detections.append((tid, b))

            # Process Tracks
            for tid, box in detections:
                x1, y1, x2, y2 = map(int, box)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                if tid not in self.tracks:
                    self.tracks[tid] = {
                        "seen": 0,
                        "cls": None,
                        "conf": 0.0,
                        "done": False,
                        "last": time.time(),
                    }
                trk = self.tracks[tid]
                trk["last"] = time.time()

                in_zone = True
                if self.chk_use_zone.isChecked():
                    zx1, zy1, zx2, zy2 = self.zone
                    in_zone = (zx1 < cx < zx2) and (zy1 < cy < zy2)

                if in_zone:
                    trk["seen"] += 1
                    if trk["seen"] >= STABILITY_FRAMES and not trk["cls"]:
                        crop = frame[max(0, y1) : max(0, y2), max(0, x1) : max(0, x2)]
                        if crop.size > 0 and self.classifier:
                            res = self.classifier.predict(crop, verbose=False)[0]
                            trk["cls"] = res.names[res.probs.top1]
                            trk["conf"] = float(res.probs.top1conf)

                # finalize logic
                if in_zone and trk["cls"] and not trk["done"]:
                    if not self.chk_assist.isChecked() or trk["conf"] >= CONF_GREEN:
                        self.finalize_track(tid, "AUTO")
                    else:
                        # manual gate
                        if trk["conf"] >= 0.4 and self.pending_tid is None:
                            self.pending_tid = tid
                            self.update_ui_wait(trk)

                # Draw AI Box
                if trk["done"]:
                    color = (0, 255, 0)
                elif tid == self.pending_tid:
                    color = (0, 255, 255)
                else:
                    color = (120, 120, 120)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                if trk["cls"]:
                    cv2.putText(
                        frame,
                        f"{trk['cls']} {trk['conf']:.2f}",
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                    )

            # Draw User Zone
            if self.chk_use_zone.isChecked():
                zx1, zy1, zx2, zy2 = self.zone
                cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 255, 0), 2)
                cv2.putText(
                    frame,
                    "ZONE",
                    (zx1, max(20, zy1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2,
                )

            self.cleanup_tracks()
            self.display_frame(frame)

            fps = 1.0 / (time.time() - t0 + 1e-6)
            self.lbl_fps.setText(f"FPS: {int(fps)}")

            # status hint
            if self.pending_tid is None:
                self.set_status("ok", "RUNNING")
            else:
                self.set_status("pending", "WAIT MANUAL")

        except Exception:
            self.set_status("error", "ERROR")
            self.play_tone("error")
            self.autoscreenshot("exception")
            traceback.print_exc()
            # แนะนำให้หยุดไว้เพื่อความปลอดภัยของหน้างาน
            self.timer.stop()
            QMessageBox.critical(
                self,
                "Error",
                "เกิดข้อผิดพลาดในระบบ\nดูรายละเอียดใน console และภาพใน saved_images/errors/",
            )
            self.is_running = False
            self.btn_startstop.setText("▶ START")

    def handle_cam_disconnect(self):
        # auto recovery for live camera
        self.set_status("error", "CAM DISCONNECTED")
        self.play_tone("error")
        self.autoscreenshot("cam_lost")

        # try reconnect only for live camera
        if not isinstance(self.cam.src, int):
            return

        now = time.time()
        if now - self.last_reconnect_try < self.reconnect_interval:
            return

        self.last_reconnect_try = now
        ok = self.cam.reconnect()
        if ok:
            self.set_status("ok", "RECOVERED")
            self.play_tone("manual_ok")
        else:
            self.set_status("error", "RECONNECTING...")

    # =========================
    # ACTIONS / UTILS
    # =========================
    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media",
            "",
            "Video/Image (*.mp4 *.avi *.mov *.mkv *.jpg *.png *.jpeg)",
        )
        if f:
            self.change_source(f)

    def change_source(self, src):
        self.timer.stop()
        self.tracks = {}
        self.pending_tid = None
        self.lbl_result.setText("READY")
        self.lbl_conf.setText("-")
        self.cam.set_source(src)
        if self.is_running:
            self.timer.start(10)

    def update_stats_ui(self):
        total = sum(self.counts.values())
        self.lbl_total.setText(f"Total: {total}")
        for name, val in self.counts.items():
            pct = (val / total * 100.0) if total > 0 else 0.0
            self.lbl_counts[name].setText(f"{val} ({pct:.1f}%)")

    def finalize_track(self, tid, dec):
        trk = self.tracks.get(tid)
        if not trk or trk.get("done"):
            return
        trk["done"] = True
        trk["dec"] = dec

        cls = trk.get("cls") or "Unknown"
        conf = float(trk.get("conf") or 0.0)

        # update counts
        if cls not in self.counts:
            self.counts[cls] = 0
        self.counts[cls] += 1
        self.update_stats_ui()

        # UI label
        self.lbl_result.setText(cls.upper())
        if dec == "AUTO":
            self.lbl_result.setStyleSheet("color: #00e676;")
            self.play_tone("auto")
        else:
            self.lbl_result.setStyleSheet("color: #ffea00;")
            self.play_tone("manual_ok")

        self.lbl_conf.setText(f"{conf*100:.1f}%")

        # clear pending
        if self.pending_tid == tid:
            self.pending_tid = None

        # log
        self.save_log(tid, cls, conf, dec)

        # backup every N logs
        if self.log_total > 0 and (self.log_total % BACKUP_EVERY == 0):
            self.make_backup()

    def update_ui_wait(self, trk):
        self.lbl_result.setText(f"{trk['cls'].upper()} ?")
        self.lbl_result.setStyleSheet(
            "color: #ffea00; background-color: #3b2f00; border-radius: 10px;"
        )
        self.lbl_conf.setText(f"{trk['conf']*100:.1f}%")
        self.play_tone("manual_wait")

    def action_confirm(self):
        if self.pending_tid:
            self.finalize_track(self.pending_tid, "MANUAL")

    def action_reject(self):
        if self.pending_tid:
            tid = self.pending_tid
            if tid in self.tracks:
                self.tracks[tid]["done"] = True
            self.lbl_result.setText("REJECTED")
            self.lbl_result.setStyleSheet("color: #b0bec5;")
            self.lbl_conf.setText("-")
            self.play_tone("reject")
            self.save_log(
                tid, self.tracks.get(tid, {}).get("cls", "Unknown"), 0.0, "REJECT"
            )
            self.pending_tid = None

    def cleanup_tracks(self):
        now = time.time()
        for t in list(self.tracks.keys()):
            if now - self.tracks[t]["last"] > TRACK_TTL_SEC:
                if t == self.pending_tid:
                    self.pending_tid = None
                del self.tracks[t]

    def save_log(self, tid, cls, conf, status):
        # table
        row = self.table.rowCount()
        if row > 9:
            self.table.removeRow(0)
            row -= 1
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        self.table.setItem(row, 1, QTableWidgetItem(str(cls)))
        self.table.setItem(row, 2, QTableWidgetItem(f"{conf:.2f}"))
        self.table.setItem(row, 3, QTableWidgetItem(status))
        self.table.scrollToBottom()

        # csv
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    tid,
                    cls,
                    f"{conf:.3f}",
                    status,
                    "0",
                ]
            )

        self.log_total += 1

    def make_backup(self):
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_csv = os.path.join(LOG_DIR, f"results_backup_{ts}.csv")
        backup_json = os.path.join(LOG_DIR, f"stats_{ts}.json")
        try:
            shutil.copy2(CSV_PATH, backup_csv)
        except Exception:
            pass
        try:
            payload = {
                "timestamp": ts,
                "counts": self.counts,
                "total": sum(self.counts.values()),
                "speed_level": self.speed_level,
                "proc_skip": self.proc_skip,
                "proc_imgsz": self.proc_imgsz,
            }
            with open(backup_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self.set_status("ok", f"BACKUP OK ({BACKUP_EVERY})")

    def export_daily_report(self):
        # create report content
        day = time.strftime("%Y-%m-%d")
        total = sum(self.counts.values())
        dur = int(time.time() - self.session_started_at)

        lines = []
        lines.append(f"Oil Palm Sorting - Daily Report ({day})")
        lines.append(f"Session Duration: {dur//60:02d}:{dur%60:02d}")
        lines.append(f"Total: {total}")
        lines.append("")

        for k, v in self.counts.items():
            pct = (v / total * 100.0) if total > 0 else 0.0
            lines.append(f"- {k}: {v} ({pct:.1f}%)")

        report_txt = "\n".join(lines)

        # default paths in logs
        txt_path = os.path.join(LOG_DIR, f"daily_report_{day}.txt")
        csv_path = os.path.join(LOG_DIR, f"daily_report_{day}.csv")

        # ask user where to save (optional)
        save_to, _ = QFileDialog.getSaveFileName(
            self, "Save Report TXT", txt_path, "Text File (*.txt)"
        )
        if not save_to:
            return

        try:
            with open(save_to, "w", encoding="utf-8") as f:
                f.write(report_txt)
        except Exception:
            QMessageBox.warning(self, "Report", "บันทึกไฟล์ TXT ไม่สำเร็จ")
            return

        # also create csv summary next to txt
        try:
            base = os.path.splitext(save_to)[0]
            csv_out = base + ".csv"
            with open(csv_out, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["date", "class", "count", "percent"])
                for k, v in self.counts.items():
                    pct = (v / total * 100.0) if total > 0 else 0.0
                    w.writerow([day, k, v, f"{pct:.1f}"])
        except Exception:
            pass

        QMessageBox.information(self, "Report", "Export report เรียบร้อยแล้ว")

    def display_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        # IgnoreAspectRatio เพื่อให้ mapping วาดโซนตรงกับภาพที่แสดง (ยืดเต็มกรอบเสมอ)
        self.lbl_cam.setPixmap(
            QPixmap.fromImage(img).scaled(self.lbl_cam.size(), Qt.IgnoreAspectRatio)
        )

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self.action_confirm()
        elif e.key() in [Qt.Key_Return, Qt.Key_Enter]:
            self.action_reject()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.cam.release()
        e.accept()


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainApp()
    w.show()
    sys.exit(app.exec())
