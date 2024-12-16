# config.py
from datetime import datetime
import os

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///attendance.db'
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    face_encoding = db.Column(db.PickleType)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='present')

# face_recognition_service.py
import cv2
import face_recognition
import numpy as np
from models import Student, Attendance, db

class FaceRecognitionService:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.known_face_encodings = []
        self.known_face_ids = []
        self.load_known_faces()

    def load_known_faces(self):
        students = Student.query.all()
        for student in students:
            if student.face_encoding is not None:
                self.known_face_encodings.append(student.face_encoding)
                self.known_face_ids.append(student.id)

    def detect_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            if True in matches:
                first_match_index = matches.index(True)
                student_id = self.known_face_ids[first_match_index]
                student = Student.query.get(student_id)
                if student:
                    name = student.name
                    self.mark_attendance(student)

            face_names.append(name)

        return zip(face_locations, face_names)

    def mark_attendance(self, student):
        last_attendance = Attendance.query.filter_by(
            student_id=student.id
        ).order_by(Attendance.timestamp.desc()).first()

        if last_attendance is None or \
           (datetime.utcnow() - last_attendance.timestamp).total_seconds() > 3600:
            attendance = Attendance(student_id=student.id)
            db.session.add(attendance)
            db.session.commit()
            return True
        return False

