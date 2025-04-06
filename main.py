import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QSlider, QShortcut, QSizePolicy, QFrame)
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize

class VideoPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NERV Video Analysis System")
        self.setGeometry(100, 100, 800, 600)
        
        # Set NERV-inspired color scheme
        self.apply_nerv_style()
        
        # Initialize video variables
        self.cap = None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0
        self.is_playing = False
        self.current_frame_data = None  # Store current frame data for resize events
        
        # Create UI components
        self.init_ui()
        
        # Timer for video playback
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
        # Keyboard shortcuts
        self.shortcut_next = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_next.activated.connect(self.next_frame)
        
        self.shortcut_prev = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_prev.activated.connect(self.prev_frame)
    
    def apply_nerv_style(self):
        # Set dark theme with NERV-inspired colors
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #ff6600;
                font-family: 'Courier New';
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #ff6600;
                border: 1px solid #ff6600;
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #ff6600;
                color: #000000;
            }
            QPushButton:disabled {
                color: #666666;
                border: 1px solid #666666;
            }
            QSlider::groove:horizontal {
                border: 1px solid #ff6600;
                height: 6px;
                background: #2a2a2a;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #ff6600;
                border: 1px solid #ff6600;
                width: 14px;
                margin: -4px 0;
                border-radius: 2px;
            }
            QLabel {
                color: #ff6600;
                border: 0px;
            }
            QFrame#infoFrame {
                border: 1px solid #ff6600;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Add NERV header
        nerv_header = QLabel("NERV VIDEO ANALYSIS SYSTEM")
        nerv_header.setAlignment(Qt.AlignCenter)
        nerv_font = QFont("Courier New", 12, QFont.Bold)
        nerv_header.setFont(nerv_font)
        main_layout.addWidget(nerv_header)
        
        # Video display area with border frame
        video_frame = QFrame()
        video_frame.setObjectName("infoFrame")
        video_frame.setFrameShape(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_frame)
        
        self.video_label = QLabel("WAITING FOR VIDEO INPUT")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout.addWidget(self.video_label)
        
        main_layout.addWidget(video_frame)
        
        # Timeline slider
        timeline_frame = QFrame()
        timeline_frame.setObjectName("infoFrame")
        timeline_layout = QVBoxLayout(timeline_frame)
        
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setEnabled(False)
        self.timeline_slider.sliderMoved.connect(self.set_position)
        self.timeline_slider.sliderPressed.connect(self.pause_video)
        self.timeline_slider.sliderReleased.connect(self.slider_released)
        timeline_layout.addWidget(self.timeline_slider)
        
        main_layout.addWidget(timeline_frame)
        
        # Control buttons layout
        controls_frame = QFrame()
        controls_frame.setObjectName("infoFrame")
        controls_layout = QHBoxLayout(controls_frame)
        
        # Play/Pause button
        self.play_button = QPushButton("▶ PLAY")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_button)
        
        # Previous frame button
        self.prev_button = QPushButton("◀ PREV")
        self.prev_button.setEnabled(False)
        self.prev_button.clicked.connect(self.prev_frame)
        controls_layout.addWidget(self.prev_button)
        
        # Next frame button
        self.next_button = QPushButton("NEXT ▶")
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_frame)
        controls_layout.addWidget(self.next_button)
        
        # Open file button
        self.open_button = QPushButton("OPEN VIDEO")
        self.open_button.clicked.connect(self.open_file)
        controls_layout.addWidget(self.open_button)
        
        # Frame counter label
        self.frame_counter = QLabel("FRAME: 0 / 0")
        controls_layout.addWidget(self.frame_counter)
        
        main_layout.addWidget(controls_frame)
        
        # Status bar
        self.status_label = QLabel("SYSTEM READY")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", 
                                                  "Video Files (*.mov *.mp4 *.avi)")
        
        if file_path:
            self.status_label.setText("LOADING VIDEO FILE...")
            # Close any existing video
            if self.cap is not None:
                self.cap.release()
            
            # Open the new video file
            self.cap = cv2.VideoCapture(file_path)
            
            if not self.cap.isOpened():
                self.video_label.setText("ERROR: UNABLE TO OPEN VIDEO FILE")
                self.status_label.setText("VIDEO LOAD FAILED")
                return
            
            # Get video properties
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.current_frame = 0
            
            # Update UI
            self.timeline_slider.setRange(0, self.total_frames - 1)
            self.timeline_slider.setValue(0)
            self.frame_counter.setText(f"FRAME: 0 / {self.total_frames - 1}")
            
            # Enable controls
            self.play_button.setEnabled(True)
            self.next_button.setEnabled(True)
            self.prev_button.setEnabled(True)
            self.timeline_slider.setEnabled(True)
            
            # Display first frame
            self.display_frame()
            self.status_label.setText(f"VIDEO LOADED: {file_path.split('/')[-1]}")
    
    def display_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Store current frame for resize events
            self.current_frame_data = frame.copy()
            
            # Fix vertical flip: flip the frame vertically
            frame = cv2.flip(frame, 0)
            
            # Convert frame from BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage and display
            h, w, ch = frame_rgb.shape
            img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            
            # Scale the image to fit the label while maintaining aspect ratio
            pixmap = QPixmap.fromImage(img)
            self.update_video_display(pixmap)
            
            # Update frame counter and slider
            self.frame_counter.setText(f"FRAME: {self.current_frame} / {self.total_frames - 1}")
            self.timeline_slider.setValue(self.current_frame)
    
    def update_video_display(self, pixmap):
        """Update the video display with the given pixmap, scaling to fit the label."""
        if pixmap:
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
    
    def update_frame(self):
        if self.cap is not None and self.is_playing:
            self.current_frame += 1
            
            if self.current_frame >= self.total_frames:
                self.current_frame = 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.status_label.setText("VIDEO LOOPING")
            
            self.display_frame()
    
    def toggle_play(self):
        if self.cap is not None:
            if self.is_playing:
                self.pause_video()
            else:
                self.play_video()
    
    def play_video(self):
        self.is_playing = True
        self.play_button.setText("❚❚ PAUSE")
        # Set timer interval based on FPS (milliseconds)
        interval = int(1000 / self.fps) if self.fps > 0 else 33
        self.timer.start(interval)
        self.status_label.setText("PLAYBACK ACTIVE")
    
    def pause_video(self):
        self.is_playing = False
        self.play_button.setText("▶ PLAY")
        self.timer.stop()
        self.status_label.setText("PLAYBACK PAUSED")
    
    def next_frame(self):
        if self.cap is not None:
            # Ensure we're paused when stepping through frames
            if self.is_playing:
                self.pause_video()
            
            if self.current_frame < self.total_frames - 1:
                self.current_frame += 1
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                self.display_frame()
                self.status_label.setText(f"ADVANCED TO FRAME {self.current_frame}")
    
    def prev_frame(self):
        if self.cap is not None:
            # Ensure we're paused when stepping through frames
            if self.is_playing:
                self.pause_video()
            
            if self.current_frame > 0:
                self.current_frame -= 1
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                self.display_frame()
                self.status_label.setText(f"RETURNED TO FRAME {self.current_frame}")
    
    def set_position(self, position):
        if self.cap is not None:
            self.current_frame = position
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            self.display_frame()
            self.status_label.setText(f"JUMPED TO FRAME {position}")
    
    def slider_released(self):
        # Resume playback if it was playing before slider was pressed
        if self.cap is not None and self.play_button.text() == "❚❚ PAUSE":
            self.play_video()
    
    def resizeEvent(self, event):
        """Handle window resize events by updating the video display."""
        super().resizeEvent(event)
        if hasattr(self, 'current_frame_data') and self.current_frame_data is not None:
            # Fix vertical flip: flip the frame vertically
            frame = cv2.flip(self.current_frame_data, 0)
            
            # Convert frame from BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage and display
            h, w, ch = frame_rgb.shape
            img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self.update_video_display(pixmap)
    
    def closeEvent(self, event):
        # Clean up resources when window is closed
        if self.cap is not None:
            self.cap.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec_())