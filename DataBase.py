import mysql.connector
from mysql.connector import Error

# Kết nối đến MySQL
DB_CONFIG = {
    'user': 'root',
    'password': '123456',
    'host': 'localhost'
}

def connect_mysql():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"Lỗi kết nối: {e}")
        return None

# Tạo cơ sở dữ liệu và bảng
def create_database():
    db = connect_mysql()
    if db is None:
        return
    
    cursor = db.cursor()
    
    try:
        # Tạo database
        print("Đang tạo cơ sở dữ liệu...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS student_management")
        print("✓ Cơ sở dữ liệu được tạo thành công")
        
        # Chọn database
        cursor.execute("USE student_management")
        
        # Bảng Vai trò (Role)
        print("\nĐang tạo bảng vai trò...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                role_id INT AUTO_INCREMENT PRIMARY KEY,
                role_name VARCHAR(50) NOT NULL UNIQUE,
                description VARCHAR(255)
            )
        """)
        print(" Bảng vai trò được tạo thành công")
        
        # Bảng Người dùng (User)
        print("Đang tạo bảng người dùng...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role_id INT NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(role_id)
            )
        """)
        print("✓ Bảng người dùng được tạo thành công")
        
        # Bảng Khối lớp (Grade Level)
        print("Đang tạo bảng khối lớp...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grade_levels (
                grade_id INT AUTO_INCREMENT PRIMARY KEY,
                grade_name VARCHAR(50) NOT NULL UNIQUE,
                description VARCHAR(255)
            )
        """)
        print("✓ Bảng khối lớp được tạo thành công")
        
        # Bảng Lớp học (Class)
        print("Đang tạo bảng lớp học...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                class_id INT AUTO_INCREMENT PRIMARY KEY,
                class_name VARCHAR(50) NOT NULL UNIQUE,
                grade_id INT NOT NULL,
                homeroom_teacher_id INT,
                max_students INT DEFAULT 40,
                school_year VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (grade_id) REFERENCES grade_levels(grade_id),
                FOREIGN KEY (homeroom_teacher_id) REFERENCES users(user_id)
            )
        """)
        print("✓ Bảng lớp học được tạo thành công")
        
        # Bảng Học sinh (Student)
        print("Đang tạo bảng học sinh...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                student_code VARCHAR(20) NOT NULL UNIQUE,
                date_of_birth DATE,
                gender ENUM('Nam', 'Nữ', 'Khác'),
                address VARCHAR(255),
                parent_name VARCHAR(100),
                parent_phone VARCHAR(15),
                class_id INT NOT NULL,
                enrollment_date DATE,
                status ENUM('Đang học', 'Nghỉ học', 'Tốt nghiệp') DEFAULT 'Đang học',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (class_id) REFERENCES classes(class_id)
            )
        """)
        print("✓ Bảng học sinh được tạo thành công")
        
        # Bảng Môn học (Subject)
        print("Đang tạo bảng môn học...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL UNIQUE,
                subject_code VARCHAR(20) NOT NULL UNIQUE,
                credit INT,
                description VARCHAR(255)
            )
        """)
        print("✓ Bảng môn học được tạo thành công")
        
        # Bảng Dạy học (Teaching Assignment)
        print("Đang tạo bảng dạy học...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teaching_assignments (
                assignment_id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id INT NOT NULL,
                subject_id INT NOT NULL,
                class_id INT NOT NULL,
                school_year VARCHAR(10),
                semester INT,
                FOREIGN KEY (teacher_id) REFERENCES users(user_id),
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
                FOREIGN KEY (class_id) REFERENCES classes(class_id),
                UNIQUE KEY unique_assignment (teacher_id, subject_id, class_id, school_year, semester)
            )
        """)
        print("✓ Bảng dạy học được tạo thành công")
        
        # Bảng Điểm số (Grade/Score)
        print("Đang tạo bảng điểm số...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                grade_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                subject_id INT NOT NULL,
                assignment_id INT NOT NULL,
                score_type ENUM('Kiểm tra', 'Bài tập', 'Giữa kỳ', 'Cuối kỳ') NOT NULL,
                score DECIMAL(5, 2),
                max_score DECIMAL(5, 2) DEFAULT 10,
                weight DECIMAL(3, 2) DEFAULT 1,
                recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id),
                FOREIGN KEY (assignment_id) REFERENCES teaching_assignments(assignment_id)
            )
        """)
        print("✓ Bảng điểm số được tạo thành công")
        
        # Bảng Điểm danh (Attendance)
        print("Đang tạo bảng điểm danh...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                class_id INT NOT NULL,
                attendance_date DATE NOT NULL,
                status ENUM('Có mặt', 'Vắng mặt', 'Muộn', 'Có phép') DEFAULT 'Có mặt',
                notes VARCHAR(255),
                recorded_by INT,
                recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (class_id) REFERENCES classes(class_id),
                FOREIGN KEY (recorded_by) REFERENCES users(user_id),
                UNIQUE KEY unique_attendance (student_id, attendance_date)
            )
        """)
        print("✓ Bảng điểm danh được tạo thành công")
        
        # Chèn các vai trò mặc định
        print("\nĐang chèn dữ liệu vai trò...")
        cursor.execute("SELECT COUNT(*) FROM roles")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO roles (role_name, description) VALUES
                ('Giáo viên', 'Vai trò giáo viên'),
                ('Học sinh', 'Vai trò học sinh'),
                ('Quản lý', 'Vai trò quản lý')
            """)
            print("✓ Vai trò được chèn thành công")
        else:
            print("✓ Vai trò đã tồn tại")
        
        # Chèn khối lớp mặc định
        print("Đang chèn dữ liệu khối lớp...")
        cursor.execute("SELECT COUNT(*) FROM grade_levels")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO grade_levels (grade_name, description) VALUES
                ('Khối 6', 'Lớp 6'),
                ('Khối 7', 'Lớp 7'),
                ('Khối 8', 'Lớp 8'),
                ('Khối 9', 'Lớp 9')
            """)
            print("✓ Khối lớp được chèn thành công")
        else:
            print("✓ Khối lớp đã tồn tại")
        
        # Chèn môn học mặc định
        print("Đang chèn dữ liệu môn học...")
        cursor.execute("SELECT COUNT(*) FROM subjects")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO subjects (subject_name, subject_code, credit) VALUES
                ('Toán học', 'MATH', 3),
                ('Tiếng Việt', 'VN', 3),
                ('Tiếng Anh', 'ENG', 3),
                ('Lịch Sử', 'HIST', 2),
                ('Địa Lý', 'GEO', 2),
                ('Khoa Học Tự Nhiên', 'SCI', 3),
                ('Giáo Dục Thể Chất', 'PE', 1),
                ('Tin Học', 'CS', 2)
            """)
            print("✓ Môn học được chèn thành công")
        else:
            print("✓ Môn học đã tồn tại")
        
        db.commit()
        
        print("\n" + "="*50)
        print("✓ Cơ sở dữ liệu được thiết lập hoàn tất!")
        print("="*50)
        print("\nThông tin kết nối:")
        print("  Database: student_management")
        print("  Host: localhost")
        print("  User: root")
        print("\nCác bảng được tạo:")
        print("  • roles (Vai trò)")
        print("  • users (Người dùng)")
        print("  • grade_levels (Khối lớp)")
        print("  • classes (Lớp học)")
        print("  • students (Học sinh)")
        print("  • subjects (Môn học)")
        print("  • teaching_assignments (Dạy học)")
        print("  • grades (Điểm số)")
        print("  • attendance (Điểm danh)")
        
    except Error as e:
        print(f"Lỗi: {e}")
    finally:
        cursor.close()
        db.close()

def show_database_info():
    """Hiển thị thông tin chi tiết của cơ sở dữ liệu"""
    db = connect_mysql()
    if db is None:
        return
    
    cursor = db.cursor()
    
    try:
        cursor.execute("USE student_management")
        cursor.execute("SHOW TABLES")
        
        print("\n" + "="*50)
        print("THÔNG TIN CƠ SỞ DỮ LIỆU - STUDENT MANAGEMENT")
        print("="*50)
        
        tables = cursor.fetchall()
        print(f"\nTổng số bảng: {len(tables)}\n")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = cursor.fetchall()
            
            print(f"📋 Bảng: {table_name}")
            print(f"   Số cột: {len(columns)}")
            for column in columns:
                col_name, col_type, col_null, col_key = column[0], column[1], column[2], column[3]
                print(f"   • {col_name}: {col_type} {'(PK)' if col_key == 'PRI' else '(FK)' if col_key == 'MUL' else ''}")
            print()
        
    except Error as e:
        print(f"Lỗi: {e}")
    finally:
        cursor.close()
        db.close()

def insert_sample_data():
    """Chèn dữ liệu mẫu vào database"""
    db = connect_mysql()
    if db is None:
        return
    
    cursor = db.cursor()
    
    try:
        cursor.execute("USE student_management")
        
        print("\nĐang chèn dữ liệu mẫu...")
        
        # Chèn giáo viên mẫu
        try:
            cursor.execute("""
                INSERT INTO users (full_name, username, password, role_id, email, phone) VALUES
                ('Nguyễn Thị An', 'an.nguyen', '123456', 1, 'an@school.edu', '0912345678'),
                ('Trần Văn Bình', 'binh.tran', '123456', 1, 'binh@school.edu', '0912345679')
            """)
            print("✓ Giáo viên mẫu được chèn thành công")
        except:
            print("✓ Giáo viên đã tồn tại hoặc lỗi khác")
        
        # Chèn lớp học mẫu
        try:
            cursor.execute("""
                INSERT INTO classes (class_name, grade_id, homeroom_teacher_id, max_students, school_year) VALUES
                ('6A', 1, 1, 40, '2024-2025'),
                ('7B', 2, 2, 40, '2024-2025')
            """)
            print("✓ Lớp học mẫu được chèn thành công")
        except:
            print("✓ Lớp học đã tồn tại hoặc lỗi khác")
        
        # Chèn học sinh mẫu
        try:
            cursor.execute("""
                INSERT INTO students (user_id, student_code, date_of_birth, gender, address, parent_name, parent_phone, class_id, enrollment_date) VALUES
                (2, 'HS001', '2010-01-15', 'Nam', '123 Đường ABC, Hà Nội', 'Nguyễn Văn A', '0987654321', 1, '2024-09-01'),
                (3, 'HS002', '2010-02-20', 'Nữ', '456 Đường XYZ, Hà Nội', 'Trần Thị B', '0987654322', 1, '2024-09-01')
            """)
            print("✓ Học sinh mẫu được chèn thành công")
        except:
            print("✓ Học sinh đã tồn tại hoặc lỗi khác")
        
        # Chèn dạy học mẫu
        try:
            cursor.execute("""
                INSERT INTO teaching_assignments (teacher_id, subject_id, class_id, school_year, semester) VALUES
                (1, 1, 1, '2024-2025', 1),
                (2, 2, 1, '2024-2025', 1)
            """)
            print("✓ Dạy học mẫu được chèn thành công")
        except:
            print("✓ Dạy học đã tồn tại hoặc lỗi khác")
        
        db.commit()
        print("\n✓ Dữ liệu mẫu được chèn hoàn tất")
        
    except Error as e:
        print(f"Lỗi: {e}")
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    print("🎓 HỆ THỐNG QUẢN LÝ HỌC SINH")
    print("="*50)
    
    # Tạo database
    create_database()
    
    # Hiển thị thông tin database
    show_database_info()
    
    # Chèn dữ liệu mẫu (bỏ comment nếu muốn chèn)
    # insert_sample_data()
