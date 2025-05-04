import sys
import cv2
import os # Added for path manipulation
import platform # To detect OS for backend suggestion
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QSlider, QShortcut, QSizePolicy, QFrame, QToolTip,
                             QSpacerItem, QMenu, QAction) # Added QMenu, QAction
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize, QUrl, QMimeData, QSettings # Added QSettings
# Import necessary QMediaPlayer enums for state/status checking
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QAudio, QMediaPlayer
# QVideoWidget is often needed for QMediaPlayer even if not displayed directly
from PyQt5.QtMultimediaWidgets import QVideoWidget

# RECENT: Define constants for settings
ORGANIZATION_NAME = "YourOrganization" # Change if desired
APPLICATION_NAME = "FramePlayer"
RECENT_FILES_KEY = "recentFiles"
MAX_RECENT_FILES = 10

# ROTATE: Define rotation constants for clarity
ROTATE_90_CLOCKWISE = cv2.ROTATE_90_CLOCKWISE
ROTATE_180 = cv2.ROTATE_180
ROTATE_90_COUNTERCLOCKWISE = cv2.ROTATE_90_COUNTERCLOCKWISE

class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame-by-Frame Video Player")
        self.setGeometry(100, 100, 900, 700)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Set NERV-inspired color scheme
        self.apply_nerv_style()

        # Initialize video variables
        self.cap = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0
        self.is_playing = False
        self.current_frame_data = None
        self.current_video_path = None
        self.was_playing_before_slider_press = False
        self.rotation_angle = 0 # ROTATE: Initialize rotation angle

        # Initialize audio player
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self._video_widget = QVideoWidget() # Keep track of the video widget
        self.media_player.setVideoOutput(self._video_widget)
        self.media_player.setNotifyInterval(50)

        # --- Audio Debugging Signals ---
        self.media_player.error.connect(self.handle_media_error)
        self.media_player.stateChanged.connect(self.handle_media_state)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        # --- End Audio Debugging ---

        # --- UI Widget Placeholders ---
        self.audio_error_label = None
        self.volume_icon_label = None
        self.volume_slider = None
        self.volume_value_label = None
        self.recent_button = None # RECENT: Placeholder for the recent button
        self.recent_menu = None # RECENT: Placeholder for the recent files menu
        # --- End UI Placeholders ---

        # RECENT: Initialize settings and load recent files list
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        self.recent_files = []
        self.load_settings() # Load recent files on startup

        # Create UI components
        self.init_ui()

        # Timer for video playback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # Setup keyboard shortcuts
        self.setup_shortcuts()

    def apply_nerv_style(self):
        # (StyleSheet remains the same)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #ff6600; /* NERV Orange */
                font-family: 'Courier New', monospace; /* Monospaced font */
            }
            QPushButton {
                background-color: #2a2a2a; /* Darker grey */
                color: #ff6600;
                border: 1px solid #ff6600;
                border-radius: 3px;
                padding: 5px 8px; /* Adjusted padding slightly */
                min-width: 110px; /* Increased min-width for hotkey text */
                font-weight: bold; /* Make button text bold */
            }
            QPushButton:hover {
                background-color: #3a3a3a; /* Slightly lighter grey on hover */
            }
            QPushButton:pressed {
                background-color: #ff6600; /* Orange background when pressed */
                color: #000000; /* Black text when pressed */
            }
            QPushButton:disabled {
                color: #666666; /* Greyed out text when disabled */
                border: 1px solid #666666;
                background-color: #222222; /* Darker background when disabled */
            }
            /* Specific widths for icon-like buttons */
            QPushButton#playPauseButton, QPushButton#prevButton, QPushButton#nextButton {
                 min-width: 0; /* Override min-width */
                 width: 120px; /* Fixed width for Play/Pause/Prev/Next */
                 padding: 5px; /* Reset padding if needed */
            }
            QPushButton#openButton, QPushButton#recentButton { /* RECENT: Apply style to recent button */
                 min-width: 120px; /* Ensure Open/Recent buttons have enough space */
            }

            QSlider::groove:horizontal {
                border: 1px solid #ff6600;
                height: 6px;
                background: #2a2a2a;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ff6600;
                border: 1px solid #ff6600;
                width: 14px;
                margin: -4px 0; /* Adjust handle vertical position */
                border-radius: 3px;
            }
            QLabel {
                color: #ff6600;
                border: 0px;
            }
            /* Style for the Frame Counter Label */
            QLabel#frameCounterLabel {
                 font-weight: bold;
                 padding-left: 10px; /* Add some space before frame count */
            }
            /* Style for the Volume Percentage Label */
            QLabel#volumeValueLabel {
                 font-weight: bold;
            }
            /* Style for the main Video Frame */
            QFrame#videoFrame {
                border: 2px solid #ff6600; /* Slightly thicker border */
                border-radius: 3px;
                padding: 0px; /* No internal padding for the video frame */
                background-color: #000000; /* Black background for video area */
            }
             /* Style for Info/Control Frames */
            QFrame#infoFrame, QFrame#controlsVolumeFrame {
                border: 1px solid #444444; /* Subtle border for control areas */
                border-radius: 3px;
                padding: 5px;
            }
            QToolTip {
                background-color: #2a2a2a;
                color: #ff6600;
                border: 1px solid #ff6600;
                font-family: 'Courier New', monospace;
            }
            QLabel#nervHeaderLabel {
                 border-bottom: 1px solid #ff6600; /* Add underline to header */
                 padding-bottom: 5px;
                 margin-bottom: 5px;
            }
            QLabel#statusLabel {
                 color: #aaaaaa; /* Lighter grey for status */
                 font-size: 9pt; /* Smaller font for status */
                 margin-top: 5px;
            }
            /* Style for the Audio Error Label */
            QLabel#audioErrorLabel {
                color: #ff6600; /* NERV Orange */
                font-weight: bold;
                padding: 2px 5px;
                border-radius: 3px;
                text-align: center; /* Center align text */
            }
            /* RECENT: Style for the Recent Files Menu */
            QMenu {
                background-color: #2a2a2a;
                color: #ff6600;
                border: 1px solid #ff6600;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 15px; /* Add padding to menu items */
                font-family: 'Courier New', monospace;
            }
            QMenu::item:selected {
                background-color: #ff6600;
                color: #000000;
            }
            QMenu::item:disabled {
                color: #666666;
            }
        """)

    def setup_shortcuts(self):
        # (Shortcuts remain the same)
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_next.activated.connect(self.next_frame)
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_prev.activated.connect(self.prev_frame)
        self.shortcut_play = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcut_play.activated.connect(self.toggle_play)
        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.open_file_dialog)

    def init_ui(self):
        # (UI Initialization remains the same)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)
        nerv_header = QLabel("FRAME-BY-FRAME VIDEO PLAYER")
        nerv_header.setObjectName("nervHeaderLabel"); nerv_header.setAlignment(Qt.AlignCenter)
        nerv_font = QFont("Courier New", 16, QFont.Bold); nerv_header.setFont(nerv_font)
        main_layout.addWidget(nerv_header)
        video_frame = QFrame(); video_frame.setObjectName("videoFrame"); video_frame.setFrameShape(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_frame); video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_label = QLabel("DRAG & DROP VIDEO FILE HERE\nOR PRESS CTRL+O")
        self.video_label.setAlignment(Qt.AlignCenter); self.video_label.setMinimumSize(640, 360)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding); self.video_label.setAcceptDrops(True)
        video_layout.addWidget(self.video_label); main_layout.addWidget(video_frame, 1)
        timeline_frame = QFrame(); timeline_frame.setObjectName("infoFrame")
        timeline_layout = QHBoxLayout(timeline_frame); timeline_label = QLabel("TIMELINE:")
        timeline_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed); timeline_layout.addWidget(timeline_label)
        self.timeline_slider = QSlider(Qt.Horizontal); self.timeline_slider.setEnabled(False)
        self.timeline_slider.sliderMoved.connect(self.set_position); self.timeline_slider.sliderPressed.connect(self.slider_pressed)
        self.timeline_slider.sliderReleased.connect(self.slider_released); timeline_layout.addWidget(self.timeline_slider)
        main_layout.addWidget(timeline_frame)
        controls_volume_frame = QFrame(); controls_volume_frame.setObjectName("controlsVolumeFrame")
        controls_volume_layout = QHBoxLayout(controls_volume_frame); controls_volume_layout.setContentsMargins(5, 5, 5, 5); controls_volume_layout.setSpacing(10)
        main_controls_layout = QHBoxLayout(); main_controls_layout.setSpacing(6)
        self.play_button = QPushButton("▶ PLAY [SPACE]"); self.play_button.setObjectName("playPauseButton"); self.play_button.setToolTip("Play/Pause Video (Spacebar)")
        self.play_button.setEnabled(False); self.play_button.clicked.connect(self.toggle_play); main_controls_layout.addWidget(self.play_button)
        self.prev_button = QPushButton("◀ PREV [←]"); self.prev_button.setObjectName("prevButton"); self.prev_button.setToolTip("Previous Frame (Left Arrow)")
        self.prev_button.setEnabled(False); self.prev_button.clicked.connect(self.prev_frame); main_controls_layout.addWidget(self.prev_button)
        self.next_button = QPushButton("NEXT [→] ▶"); self.next_button.setObjectName("nextButton"); self.next_button.setToolTip("Next Frame (Right Arrow)")
        self.next_button.setEnabled(False); self.next_button.clicked.connect(self.next_frame); main_controls_layout.addWidget(self.next_button)
        self.open_button = QPushButton("OPEN [CTRL+O]"); self.open_button.setObjectName("openButton"); self.open_button.setToolTip("Open Video File (Ctrl+O)")
        self.open_button.clicked.connect(self.open_file_dialog); main_controls_layout.addWidget(self.open_button)
        self.recent_button = QPushButton("RECENT"); self.recent_button.setObjectName("recentButton"); self.recent_button.setToolTip("Open a recently used video file")
        self.recent_menu = QMenu(self); self.recent_button.clicked.connect(self.show_recent_files_menu)
        self.recent_button.setEnabled(bool(self.recent_files)); main_controls_layout.addWidget(self.recent_button)
        self.frame_counter = QLabel("FRAME: - / -"); self.frame_counter.setObjectName("frameCounterLabel"); self.frame_counter.setToolTip("Current Frame / Total Frames")
        main_controls_layout.addWidget(self.frame_counter); main_controls_layout.addStretch(1); controls_volume_layout.addLayout(main_controls_layout); controls_volume_layout.addStretch(1)
        volume_layout = QHBoxLayout(); volume_layout.setSpacing(5)
        self.volume_icon_label = QLabel("VOLUME:"); self.volume_icon_label.setToolTip("Volume Control"); volume_layout.addWidget(self.volume_icon_label)
        self.volume_slider = QSlider(Qt.Horizontal); self.volume_slider.setRange(0, 100); self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume); self.volume_slider.setFixedWidth(100); self.volume_slider.setToolTip("Adjust Volume"); volume_layout.addWidget(self.volume_slider)
        self.volume_value_label = QLabel("70%"); self.volume_value_label.setObjectName("volumeValueLabel"); self.volume_value_label.setFixedWidth(40)
        self.volume_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter); volume_layout.addWidget(self.volume_value_label)
        self.audio_error_label = QLabel("AUDIO CODEC ERROR"); self.audio_error_label.setObjectName("audioErrorLabel"); self.audio_error_label.setAlignment(Qt.AlignCenter)
        self.audio_error_label.setMinimumWidth(self.volume_icon_label.sizeHint().width() + self.volume_slider.minimumSizeHint().width() + self.volume_value_label.minimumSizeHint().width() + 10)
        self.audio_error_label.setVisible(False); volume_layout.addWidget(self.audio_error_label)
        controls_volume_layout.addLayout(volume_layout); main_layout.addWidget(controls_volume_frame)
        self.status_label = QLabel("SYSTEM READY. Drag & Drop a video file or press CTRL+O.")
        self.status_label.setObjectName("statusLabel"); self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        self.set_volume(self.volume_slider.value())


    # --- Drag and Drop Implementation ---
    def dragEnterEvent(self, event: 'QDragEnterEvent'):
        # (Remains the same)
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile(); _, ext = os.path.splitext(file_path)
                    if ext.lower() in self.get_supported_formats():
                        event.acceptProposedAction(); self.status_label.setText(f"DROP FILE: {os.path.basename(file_path)}")
                        return
        event.ignore(); self.status_label.setText("INVALID FILE TYPE FOR DROP")

    def dropEvent(self, event: 'QDropEvent'):
        # (Remains the same)
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile(); _, ext = os.path.splitext(file_path)
                    if ext.lower() in self.get_supported_formats():
                        self.status_label.setText(f"PROCESSING DROPPED FILE: {os.path.basename(file_path)}")
                        QApplication.processEvents(); self.load_video(file_path); event.acceptProposedAction()
                        return
        event.ignore(); self.status_label.setText("SYSTEM READY.")


    # --- File Handling ---
    def get_supported_formats(self):
        """Returns a list of supported video file extensions."""
        return ['.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.mpeg', '.mpg', '.webm']

    def open_file_dialog(self):
        # (Remains the same)
        supported_ext_str = " ".join([f"*{ext}" for ext in self.get_supported_formats()])
        supported_formats_str = f"Video Files ({supported_ext_str});;All Files (*)"
        start_dir = os.path.dirname(self.recent_files[0]) if self.recent_files else ""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", start_dir, supported_formats_str)
        if file_path: self.load_video(file_path)

    def load_video(self, file_path):
        if not os.path.exists(file_path):
            self.status_label.setText(f"ERROR: File not found - {file_path}")
            self.video_label.setText("ERROR: FILE NOT FOUND"); self.reset_ui()
            if file_path in self.recent_files:
                self.recent_files.remove(file_path); self.save_settings()
                self.recent_button.setEnabled(bool(self.recent_files))
            return

        self.status_label.setText("LOADING VIDEO FILE...")
        QApplication.processEvents()

        # Resetting State
        self.pause_video()
        if self.media_player.state() != QMediaPlayer.StoppedState: self.media_player.stop()
        if self.cap is not None: self.cap.release(); self.cap = None
        self.rotation_angle = 0 # ROTATE: Reset rotation angle

        # Reset Audio UI State
        if self.audio_error_label: self.audio_error_label.setVisible(False)
        if self.volume_icon_label: self.volume_icon_label.setVisible(True)
        if self.volume_slider: self.volume_slider.setVisible(True)
        if self.volume_value_label: self.volume_value_label.setVisible(True)

        self.current_video_path = file_path
        self.cap = cv2.VideoCapture(file_path, cv2.CAP_ANY)

        if not self.cap.isOpened():
            self.video_label.setText("ERROR: UNABLE TO OPEN VIDEO FILE (OpenCV)")
            self.status_label.setText("VIDEO LOAD FAILED (OpenCV)"); self.reset_ui()
            return

        # ROTATE: Attempt to get rotation metadata
        try:
            # cv2.CAP_PROP_ORIENTATION_META uses EXIF orientation tags:
            # 1: 0 degrees (Horizontal)
            # 3: 180 degrees
            # 6: 270 degrees (90 clockwise)
            # 8: 90 degrees (90 counter-clockwise)
            orientation_raw = self.cap.get(cv2.CAP_PROP_ORIENTATION_META)
            print(f"Raw orientation metadata: {orientation_raw} (type: {type(orientation_raw)})")
            self.rotation_angle = orientation_raw
            print(f"Determined rotation angle: {self.rotation_angle} degrees")

        except Exception as e:
            print(f"Error getting or processing orientation metadata (cv2.CAP_PROP_ORIENTATION_META): {e}")
            self.rotation_angle = 0 # Fallback to no rotation
        # --- End Rotation Check ---

        # RECENT: Add successfully loaded file to recent list
        self.update_recent_files(file_path)

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if self.total_frames <= 0: self.status_label.setText("WARNING: Could not read total frame count accurately."); self.total_frames = 0

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.status_label.setText("WARNING: Could not read FPS accurately. Using default 30 FPS."); self.fps = 30

        self.current_frame = 0

        # Update UI Timeline
        if self.total_frames > 0: self.timeline_slider.setRange(0, self.total_frames - 1); self.timeline_slider.setEnabled(True)
        else: self.timeline_slider.setEnabled(False)
        self.timeline_slider.setValue(0); self.update_frame_counter()

        # Enable controls
        self.play_button.setEnabled(True); self.play_button.setText("▶ PLAY [SPACE]")
        self.next_button.setEnabled(True); self.prev_button.setEnabled(True)

        # Setup audio playback
        self.setup_audio(file_path)

        # Display first frame
        self.set_frame_position(0)

        self.status_label.setText(f"VIDEO LOADED: {os.path.basename(file_path)}")
        self.video_label.setText("") # Clear the initial text

    def reset_ui(self):
        # (Remains the same)
        print("Resetting UI elements (disabling controls)...")
        self.play_button.setEnabled(False); self.play_button.setText("▶ PLAY [SPACE]")
        self.next_button.setEnabled(False); self.prev_button.setEnabled(False)
        self.timeline_slider.setEnabled(False); self.timeline_slider.setValue(0)
        self.frame_counter.setText("FRAME: - / -")
        self.current_frame = 0; self.total_frames = 0; self.fps = 0
        self.is_playing = False
        if self.timer.isActive(): self.timer.stop()
        if self.media_player.state() != QMediaPlayer.StoppedState: self.media_player.stop()
        self.current_frame_data = None; self.current_video_path = None
        self.rotation_angle = 0 # ROTATE: Reset rotation angle
        if self.audio_error_label: self.audio_error_label.setVisible(False)
        if self.volume_icon_label: self.volume_icon_label.setVisible(True)
        if self.volume_slider: self.volume_slider.setVisible(True)
        if self.volume_value_label: self.volume_value_label.setVisible(True)


    # --- RECENT: Settings and Recent Files List Management ---
    def load_settings(self):
        # (Remains the same)
        print("Loading settings...")
        files = self.settings.value(RECENT_FILES_KEY, [], type=list)
        seen_files = set(); valid_files = []
        for f in files:
            if isinstance(f, str) and f not in seen_files and os.path.exists(f):
                valid_files.append(f); seen_files.add(f)
        self.recent_files = valid_files[:MAX_RECENT_FILES]
        print(f"Loaded {len(self.recent_files)} recent files.")

    def save_settings(self):
        # (Remains the same)
        print(f"Saving {len(self.recent_files)} recent files...")
        self.settings.setValue(RECENT_FILES_KEY, self.recent_files); self.settings.sync()

    def update_recent_files(self, file_path):
        # (Remains the same)
        print(f"Updating recent files with: {file_path}")
        try:
            if file_path in self.recent_files: self.recent_files.remove(file_path)
            self.recent_files.insert(0, file_path)
            self.recent_files = self.recent_files[:MAX_RECENT_FILES]
            if self.recent_button: self.recent_button.setEnabled(True)
            self.save_settings()
        except Exception as e: print(f"Error updating recent files list: {e}")

    def show_recent_files_menu(self):
        # (Remains the same)
        if not self.recent_menu or not self.recent_button: print("Error: Recent menu or button not initialized."); return
        self.recent_menu.clear(); print(f"Populating recent files menu. Current list: {self.recent_files}")
        valid_recent_files = [f for f in self.recent_files if os.path.exists(f)]
        if valid_recent_files != self.recent_files:
            print(f"Filtered recent files. Removed non-existent files. New list: {valid_recent_files}")
            self.recent_files = valid_recent_files; self.save_settings()
        if not self.recent_files:
            print("No recent files found or all were invalid.")
            no_files_action = QAction("No Recent Files", self); no_files_action.setEnabled(False)
            self.recent_menu.addAction(no_files_action); self.recent_button.setEnabled(False)
        else:
            print(f"Adding {len(self.recent_files)} files to menu.")
            for i, file_path in enumerate(self.recent_files):
                base_name = os.path.basename(file_path); action_text = f"&{i+1} {base_name}" if i < 9 else base_name
                action = QAction(action_text, self); action.setToolTip(file_path)
                action.triggered.connect(lambda checked=False, path=file_path: self.open_recent_file(path))
                self.recent_menu.addAction(action)
            self.recent_button.setEnabled(True)
        print("Showing recent files menu popup.")
        self.recent_menu.popup(self.recent_button.mapToGlobal(self.recent_button.rect().bottomLeft()))

    def open_recent_file(self, file_path):
        # (Remains the same)
        print(f"Opening recent file: {file_path}")
        if os.path.exists(file_path): self.load_video(file_path)
        else:
            self.status_label.setText(f"ERROR: Recent file not found - {file_path}")
            if file_path in self.recent_files:
                self.recent_files.remove(file_path); self.save_settings()
                self.recent_button.setEnabled(bool(self.recent_files))
            QToolTip.showText(self.recent_button.mapToGlobal(self.recent_button.rect().topLeft()), f"File not found:\n{file_path}", self.recent_button, self.recent_button.rect(), 2000)


    # --- Audio Handling ---
    def setup_audio(self, file_path):
        # (Remains the same)
        print(f"Setting up audio for: {file_path}")
        try:
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            if self.media_player.state() != QMediaPlayer.StoppedState: self.media_player.stop()
            self.media_player.setMedia(media_content)
        except Exception as e: self.status_label.setText(f"ERROR setting up audio: {e}"); print(f"Exception during audio setup: {e}")

    def set_volume(self, volume):
        # (Remains the same)
        if self.volume_value_label: self.volume_value_label.setText(f"{volume}%")
        if self.media_player: self.media_player.setVolume(volume)

    # --- Audio Debugging Handlers ---
    def handle_media_error(self):
        # (Remains the same)
        error_code = self.media_player.error(); error_string = self.media_player.errorString()
        error_details = f"Code={error_code}, Message='{error_string}'"
        if error_code == QMediaPlayer.ResourceError: error_details += " (Resource Error)"
        elif error_code == QMediaPlayer.FormatError: error_details += " (Format Error)"
        elif error_code == QMediaPlayer.NetworkError: error_details += " (Network Error)"
        elif error_code == QMediaPlayer.AccessDeniedError: error_details += " (Access Denied Error)"
        elif error_code == QMediaPlayer.ServiceMissingError: error_details += " (Service Missing Error)"
        print(f"AUDIO ERROR: {error_details}"); self.status_label.setText(f"AUDIO ERROR: {error_string or error_details}")

    def handle_media_state(self, state):
        # (Remains the same)
        state_map = { QMediaPlayer.StoppedState: "StoppedState", QMediaPlayer.PlayingState: "PlayingState", QMediaPlayer.PausedState: "PausedState" }
        print(f"AUDIO STATE CHANGED TO: {state_map.get(state, 'UnknownState')} ({state})")

    def handle_media_status(self, status):
        # (Remains the same)
        status_map = { QMediaPlayer.UnknownMediaStatus: "UnknownMediaStatus", QMediaPlayer.NoMedia: "NoMedia", QMediaPlayer.LoadingMedia: "LoadingMedia", QMediaPlayer.LoadedMedia: "LoadedMedia", QMediaPlayer.StalledMedia: "StalledMedia", QMediaPlayer.BufferingMedia: "BufferingMedia", QMediaPlayer.BufferedMedia: "BufferedMedia", QMediaPlayer.EndOfMedia: "EndOfMedia", QMediaPlayer.InvalidMedia: "InvalidMedia" }
        current_status = status_map.get(status, 'UnknownStatus'); print(f"AUDIO MEDIA STATUS CHANGED TO: {current_status} ({status})")
        show_error = False
        if status == QMediaPlayer.LoadedMedia:
            if not self.media_player.isAudioAvailable(): self.status_label.setText("WARNING: Audio track not found or unavailable.")
        elif status == QMediaPlayer.InvalidMedia:
            self.status_label.setText("ERROR: Invalid audio media (codec/format issue?). Video controls remain active.")
            show_error = True;
            if self.audio_error_label: self.audio_error_label.setText("AUDIO CODEC ERROR")
        elif status == QMediaPlayer.EndOfMedia:
            if self.is_playing: self.pause_video();
            if self.total_frames > 0: self.set_frame_position(self.total_frames - 1)
        if self.audio_error_label: self.audio_error_label.setVisible(show_error)
        if self.volume_icon_label: self.volume_icon_label.setVisible(not show_error)
        if self.volume_slider: self.volume_slider.setVisible(not show_error)
        if self.volume_value_label: self.volume_value_label.setVisible(not show_error)


    # --- Video Frame Handling ---
    def display_frame(self, frame_data):
        # (Remains the same as previous version with rotation logic)
        if frame_data is None: print("Warning: display_frame called with None data."); return
        self.current_frame_data = frame_data.copy()
        # ROTATE: Apply rotation based on metadata detected during load
        rotated_frame = frame_data # Start with original
        if self.rotation_angle == 90:
            rotated_frame = cv2.rotate(frame_data, ROTATE_90_COUNTERCLOCKWISE)
            # print("Applied 90 degree counter-clockwise rotation.") # Reduce console spam
        elif self.rotation_angle == 180:
            rotated_frame = cv2.rotate(frame_data, ROTATE_180)
            # print("Applied 180 degree rotation.") # Reduce console spam
        elif self.rotation_angle == 270:
            rotated_frame = cv2.rotate(frame_data, ROTATE_90_CLOCKWISE)
            # print("Applied 90 degree clockwise rotation.") # Reduce console spam

        # Use the rotated_frame for subsequent processing
        frame_processed = rotated_frame

        try:
            if len(frame_processed.shape) == 3 and frame_processed.shape[2] == 3: frame_rgb = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2RGB)
            elif len(frame_processed.shape) == 2: frame_rgb = cv2.cvtColor(frame_processed, cv2.COLOR_GRAY2RGB)
            else: print(f"Error: Unexpected frame shape after rotation {frame_processed.shape}"); self.status_label.setText("Error processing rotated frame format."); return
        except cv2.error as e: print(f"Error converting color space after rotation: {e}"); self.status_label.setText("Error processing rotated frame color."); return
        h, w, ch = frame_rgb.shape; bytes_per_line = ch * w; q_image_format = QImage.Format_RGB888
        img = QImage(frame_rgb.data, w, h, bytes_per_line, q_image_format)
        if img.isNull(): print("Warning: Created null QImage after rotation."); return
        pixmap = QPixmap.fromImage(img); self.update_video_display(pixmap)

    def update_video_display(self, pixmap):
        # (Remains the same)
        if pixmap and not pixmap.isNull():
            if hasattr(self, 'video_label') and self.video_label:
                scaled_pixmap = pixmap.scaled( self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation )
                self.video_label.setPixmap(scaled_pixmap)
        else:
            if hasattr(self, 'video_label') and self.video_label:
                self.video_label.clear(); self.video_label.setText("ERROR DISPLAYING FRAME\nDRAG & DROP OR OPEN FILE")

    def update_frame(self):
        # (Remains the same)
        if self.cap is not None and self.is_playing:
            if not self.cap.isOpened(): self.pause_video(); self.status_label.setText("ERROR: Video source lost."); return
            ret, frame = self.cap.read()
            if ret:
                new_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)); self.current_frame = new_frame_pos - 1
                if self.current_frame < 0: self.current_frame = 0
                self.display_frame(frame); self.update_frame_counter()
                self.timeline_slider.blockSignals(True)
                slider_val = min(self.current_frame, self.total_frames - 1) if self.total_frames > 0 else 0
                self.timeline_slider.setValue(slider_val); self.timeline_slider.blockSignals(False)
                if self.total_frames > 0 and self.current_frame >= self.total_frames - 1:
                    self.pause_video(); self.set_frame_position(self.total_frames - 1); self.status_label.setText("VIDEO END REACHED")
            else:
                self.pause_video();
                if self.total_frames > 0: self.set_frame_position(self.total_frames - 1)
                self.status_label.setText("VIDEO END OR READ ERROR")


    # --- Playback Control ---
    def toggle_play(self):
        # (Remains the same)
        if self.cap is not None:
            if self.is_playing: self.pause_video()
            else:
                if self.total_frames > 0 and self.current_frame >= self.total_frames - 1: self.set_frame_position(0)
                self.play_video()

    def play_video(self):
        # (Remains the same)
        if not self.cap or self.is_playing: return
        can_play_audio = False; player_state = self.media_player.state(); media_status = self.media_player.mediaStatus()
        if player_state == QMediaPlayer.StoppedState or player_state == QMediaPlayer.PausedState:
             if media_status in [QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia, QMediaPlayer.BufferingMedia]: can_play_audio = True
             elif media_status == QMediaPlayer.EndOfMedia: time_ms = self.get_time_ms_from_frame(self.current_frame); print(f"Audio at end, seeking to {time_ms}ms before play."); self.media_player.setPosition(time_ms); can_play_audio = True
             else: self.status_label.setText("Waiting for media...")
        else: print(f"Cannot play audio: Player is already in state {player_state}")
        self.is_playing = True; self.play_button.setText("❚❚ PAUSE [SPACE]"); self.play_button.setToolTip("Pause Video (Spacebar)")
        interval = int(1000 / self.fps) if self.fps > 0 else 33; self.timer.start(interval)
        if can_play_audio:
            time_ms = self.get_time_ms_from_frame(self.current_frame); current_audio_pos = self.media_player.position()
            if abs(current_audio_pos - time_ms) > 200: print(f"Setting audio position to {time_ms}ms (Frame {self.current_frame}) before playing."); self.media_player.setPosition(time_ms)
            self.media_player.play(); self.status_label.setText("PLAYBACK ACTIVE (Video + Audio)")
        else: self.status_label.setText("PLAYBACK ACTIVE (Video Only)")

    def pause_video(self):
        # (Remains the same)
        if not self.is_playing: return
        print("Pausing video/audio..."); self.is_playing = False
        self.play_button.setText("▶ PLAY [SPACE]"); self.play_button.setToolTip("Play Video (Spacebar)")
        self.timer.stop();
        if self.media_player.state() == QMediaPlayer.PlayingState: self.media_player.pause()
        self.status_label.setText("PLAYBACK PAUSED")

    def next_frame(self):
        # (Remains the same)
        if self.cap is not None and self.total_frames > 0:
            was_playing = self.is_playing;
            if self.is_playing: self.pause_video()
            if self.current_frame < self.total_frames - 1:
                new_frame = self.current_frame + 1; self.set_frame_position(new_frame); self.status_label.setText(f"ADVANCED TO FRAME {new_frame}")
            else: self.status_label.setText("ALREADY AT LAST FRAME");
            if was_playing and self.current_frame >= self.total_frames - 1: self.pause_video() # Ensure stays paused if was playing and hit end

    def prev_frame(self):
        # (Remains the same)
        if self.cap is not None:
            was_playing = self.is_playing;
            if self.is_playing: self.pause_video()
            if self.current_frame > 0:
                new_frame = self.current_frame - 1; self.set_frame_position(new_frame); self.status_label.setText(f"RETURNED TO FRAME {new_frame}")
            else: self.status_label.setText("ALREADY AT FIRST FRAME");
            if was_playing and self.current_frame <= 0: self.pause_video() # Ensure stays paused if was playing and hit start

    def set_frame_position(self, frame_number):
        # (Remains the same)
        if self.cap is None or self.total_frames <= 0: return
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number); ret, frame = self.cap.read()
        if ret:
            actual_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1;
            if actual_frame_pos < 0: actual_frame_pos = 0
            self.current_frame = actual_frame_pos; self.display_frame(frame); self.update_frame_counter()
            self.timeline_slider.blockSignals(True); self.timeline_slider.setValue(self.current_frame); self.timeline_slider.blockSignals(False)
            time_ms = self.get_time_ms_from_frame(self.current_frame)
            if self.media_player.isAvailable() and self.media_player.mediaStatus() in [QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia, QMediaPlayer.BufferingMedia, QMediaPlayer.EndOfMedia] and self.media_player.state() != QMediaPlayer.StoppedState:
                self.media_player.setPosition(time_ms)
        else:
            print(f"Error seeking to frame: {frame_number} (read failed after seek)"); self.status_label.setText(f"ERROR SEEKING TO FRAME {frame_number}")
            current_pos_after_fail = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            self.current_frame = int(current_pos_after_fail) - 1 if current_pos_after_fail and current_pos_after_fail > 0 else frame_number
            if self.current_frame < 0: self.current_frame = 0
            self.update_frame_counter(); self.timeline_slider.blockSignals(True); self.timeline_slider.setValue(self.current_frame); self.timeline_slider.blockSignals(False)


    def get_time_ms_from_frame(self, frame_number):
        # (Remains the same)
        if self.fps > 0: return int((frame_number * 1000) / self.fps)
        return 0

    def set_position(self, position):
        # (Remains the same)
        if self.cap is not None:
            if position != self.current_frame:
                 self.set_frame_position(position); self.status_label.setText(f"SLIDER MOVED TO FRAME {position}")

    def slider_pressed(self):
        # (Remains the same)
        if self.cap is not None:
            self.was_playing_before_slider_press = self.is_playing;
            if self.is_playing: self.pause_video()

    def slider_released(self):
        # (Remains the same)
        if self.cap is not None:
            final_pos = self.timeline_slider.value()
            if final_pos != self.current_frame: self.set_frame_position(final_pos); self.status_label.setText(f"JUMPED TO FRAME {final_pos}")
            if self.was_playing_before_slider_press:
                 if self.total_frames == 0 or self.current_frame < self.total_frames -1: self.play_video()
                 else: self.play_button.setText("▶ PLAY [SPACE]"); self.play_button.setToolTip("Play Video (Spacebar)"); self.status_label.setText("VIDEO END REACHED")
        self.was_playing_before_slider_press = False

    def update_frame_counter(self):
        # (Remains the same)
        total_display = self.total_frames - 1 if self.total_frames > 0 else "-"
        current_display = self.current_frame if self.cap and self.total_frames > 0 else "-"
        self.frame_counter.setText(f"FRAME: {current_display} / {total_display}")


    # --- Window Events ---
    def resizeEvent(self, event):
        # (Remains the same)
        super().resizeEvent(event)
        if hasattr(self, 'current_frame_data') and self.current_frame_data is not None:
            if hasattr(self, 'video_label') and self.video_label: self.display_frame(self.current_frame_data)

    def closeEvent(self, event):
        # (Remains the same)
        print("Closing application..."); self.save_settings(); self.pause_video()
        if self.cap is not None: self.cap.release(); self.cap = None; print("Video capture released.")
        if self.media_player: self.media_player.stop(); self.media_player.setMedia(QMediaContent()); print("Media player stopped and cleared.")
        event.accept()


if __name__ == "__main__":
    # (Main execution block remains the same)
    print(f"Running on platform: {sys.platform}")
    backend_to_try = ''
    if sys.platform == "win32": print("Suggesting 'windowsmediafoundation' backend for Windows.")
    elif sys.platform == "darwin": print("Suggesting 'avfoundation' backend for macOS.")
    else: print("Suggesting 'gstreamer' backend for Linux/other.")
    # if backend_to_try: os.environ['QT_MULTIMEDIA_BACKEND'] = backend_to_try
    # else: print("Using Qt's default multimedia backend.")
    app = QApplication(sys.argv)
    app.setOrganizationName(ORGANIZATION_NAME); app.setApplicationName(APPLICATION_NAME)
    player = VideoPlayer(); player.show(); sys.exit(app.exec_())
