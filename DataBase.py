import mysql.connector
from mysql.connector import Error

DB_CONFIG = {'user': 'root', 'password': '123456', 'host': 'localhost'}

def create_database():
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS student_management")
        cursor.execute("USE student_management")

        tables = [
            "CREATE TABLE IF NOT EXISTS roles (role_id INT AUTO_INCREMENT PRIMARY KEY, role_name VARCHAR(50) NOT NULL UNIQUE, description VARCHAR(255))",
            """CREATE TABLE IF NOT EXISTS users (user_id INT AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(100) NOT NULL, username VARCHAR(50) NOT NULL UNIQUE, 
               password VARCHAR(255) NOT NULL, role_id INT NOT NULL, email VARCHAR(100), phone VARCHAR(15), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
               FOREIGN KEY (role_id) REFERENCES roles(role_id))""",
            "CREATE TABLE IF NOT EXISTS grade_levels (grade_id INT AUTO_INCREMENT PRIMARY KEY, grade_name VARCHAR(50) NOT NULL UNIQUE, description VARCHAR(255))",
            """CREATE TABLE IF NOT EXISTS classes (class_id INT AUTO_INCREMENT PRIMARY KEY, class_name VARCHAR(50) NOT NULL UNIQUE, grade_id INT NOT NULL, 
               homeroom_teacher_id INT, max_students INT DEFAULT 40, school_year VARCHAR(10), FOREIGN KEY (grade_id) REFERENCES grade_levels(grade_id), 
               FOREIGN KEY (homeroom_teacher_id) REFERENCES users(user_id))""",
            """CREATE TABLE IF NOT EXISTS students (student_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL UNIQUE, student_code VARCHAR(20) NOT NULL UNIQUE, 
               date_of_birth DATE, gender ENUM('Nam', 'Nữ', 'Khác'), address VARCHAR(255), parent_name VARCHAR(100), parent_phone VARCHAR(15), 
               class_id INT NOT NULL, enrollment_date DATE, status ENUM('Đang học', 'Nghỉ học', 'Tốt nghiệp') DEFAULT 'Đang học', 
               FOREIGN KEY (user_id) REFERENCES users(user_id), FOREIGN KEY (class_id) REFERENCES classes(class_id))""",
            "CREATE TABLE IF NOT EXISTS subjects (subject_id INT AUTO_INCREMENT PRIMARY KEY, subject_name VARCHAR(100) NOT NULL UNIQUE, subject_code VARCHAR(20) NOT NULL UNIQUE, credit INT)",
            """CREATE TABLE IF NOT EXISTS teaching_assignments (assignment_id INT AUTO_INCREMENT PRIMARY KEY, teacher_id INT NOT NULL, subject_id INT NOT NULL, 
               class_id INT NOT NULL, school_year VARCHAR(10), semester INT, FOREIGN KEY (teacher_id) REFERENCES users(user_id), 
               FOREIGN KEY (subject_id) REFERENCES subjects(subject_id), FOREIGN KEY (class_id) REFERENCES classes(class_id))""",
            """CREATE TABLE IF NOT EXISTS grades (grade_id INT AUTO_INCREMENT PRIMARY KEY, student_id INT NOT NULL, subject_id INT NOT NULL, 
               assignment_id INT NOT NULL, score_type ENUM('Kiểm tra', 'Bài tập', 'Giữa kỳ', 'Cuối kỳ') NOT NULL, score DECIMAL(5, 2), 
               FOREIGN KEY (student_id) REFERENCES students(student_id), FOREIGN KEY (subject_id) REFERENCES subjects(subject_id))""",
            """CREATE TABLE IF NOT EXISTS attendance (attendance_id INT AUTO_INCREMENT PRIMARY KEY, student_id INT NOT NULL, class_id INT NOT NULL, 
               attendance_date DATE NOT NULL, status ENUM('Có mặt', 'Vắng mặt', 'Muộn', 'Có phép') DEFAULT 'Có mặt', recorded_by INT, 
               FOREIGN KEY (student_id) REFERENCES students(student_id), FOREIGN KEY (class_id) REFERENCES classes(class_id), 
               UNIQUE KEY unique_attendance (student_id, attendance_date))""",
            """CREATE TABLE IF NOT EXISTS self_attendance_configs (config_id INT AUTO_INCREMENT PRIMARY KEY, class_id INT NOT NULL, 
               auth_date DATE NOT NULL, start_time TIME NOT NULL, end_time TIME NOT NULL, 
               FOREIGN KEY (class_id) REFERENCES classes(class_id), 
               UNIQUE KEY unique_class_date (class_id, auth_date))"""
        ]
        for table in tables: cursor.execute(table)

        cursor.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO roles (role_name, description) VALUES
                ('Giáo viên', 'Vai trò giáo viên'),
                ('Học sinh', 'Vai trò học sinh'),
                ('Quản lý', 'Vai trò quản lý')""")
        db.commit()

        cursor.execute("SELECT COUNT(*) FROM grade_levels")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO grade_levels (grade_name) VALUES ('Khối 6'), ('Khối 7'), ('Khối 8'), ('Khối 9')")

        cursor.execute("SELECT COUNT(*) FROM subjects")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO subjects (subject_name, subject_code, credit) VALUES ('Toán', 'MATH', 3), ('Văn', 'LIT', 3), ('Anh', 'ENG', 3), ('Giáo viên chủ nhiệm', 'GVCN', 0)")

        db.commit()
        print("✓ Database setup completed!")
    except Error as e: print(f"Lỗi: {e}")
    finally: db.close()

if __name__ == "__main__": create_database()
