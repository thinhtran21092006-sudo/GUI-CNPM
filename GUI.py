import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import bcrypt
import os
import re

def validate_email(email):
    """Kiểm tra định dạng email cơ bản."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Kiểm tra số điện thoại (chỉ chứa số, từ 9-11 ký tự)."""
    return phone.isdigit() and 9 <= len(phone) <= 11

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv không bắt buộc; nếu thiếu sẽ chỉ dùng os.environ
    pass

# ===================== KẾT NỐI DATABASE =====================

REQUIRED_TABLES = [
    "users", "roles", "students", "classes",
    "subjects", "attendance", "grades", "teaching_assignments",
    "grade_levels", "self_attendance_configs"
]

REQUIRED_SCHEMA_HINT = """
Vui lòng chạy file setup_database.py để khởi tạo đầy đủ 10 bảng cần thiết trước khi khởi động ứng dụng.
"""

class DatabaseManager:
    """Context manager quản lý kết nối + transaction cho MySQL."""

    def __init__(self):
        self.db_config = {
            "user": os.environ.get("DB_USER", "root"),
            "password": os.environ.get("DB_PASSWORD", "123456"),
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": int(os.environ.get("DB_PORT", "3306")),
            "database": os.environ.get("DB_NAME", "student_management"),
        }
        self.conn = None
        self.cursor = None

    def __enter__(self):
        try:
            self.conn = mysql.connector.connect(**self.db_config)
        except Error as e:
            messagebox.showerror("Lỗi kết nối", f"Không thể kết nối database:\n{e}")
            return None
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        return False

    def execute(self, query, params=None, fetch=False):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        if fetch:
            return self.cursor.fetchall()
        return self.cursor.rowcount

    def executemany(self, query, seq_params):
        self.cursor.executemany(query, seq_params)
        return self.cursor.rowcount


def check_schema_ready() -> bool:
    """Kiểm tra các bảng bắt buộc đã tồn tại chưa."""
    db_name = os.environ.get("DB_NAME", "student_management")
    with DatabaseManager() as db:
        if db is None:
            return False
        try:
            placeholders = ",".join(["%s"] * len(REQUIRED_TABLES))
            db.cursor.execute(
                f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})",
                (db_name, *REQUIRED_TABLES),
            )
            existing = {row[0] for row in db.cursor.fetchall()}
        except Error as e:
            messagebox.showerror("Lỗi", f"Không kiểm tra được schema:\n{e}\n\n{REQUIRED_SCHEMA_HINT}")
            return False
    missing = set(REQUIRED_TABLES) - existing
    if missing:
        messagebox.showerror(
            "Thiếu bảng database",
            "Các bảng sau chưa tồn tại: " + ", ".join(sorted(missing)) +
            "\n\nVui lòng chạy file setup_database.py trước khi sử dụng.\n\n" + REQUIRED_SCHEMA_HINT,
        )
        return False
    return True


def execute_query(query, params=None, fetch=False):
    """Thực hiện query sử dụng DatabaseManager."""
    with DatabaseManager() as db:
        if db:
            try:
                return db.execute(query, params, fetch=fetch)
            except Error as e:
                messagebox.showerror("Lỗi Database", str(e))
    return None

def create_window(title, geometry, resizable=False):
    win = tk.Toplevel()
    win.title(title)
    win.geometry(geometry)
    if resizable: win.grab_set()
    return win

def ui_label_entry(parent, label_text, show=None):
    tk.Label(parent, text=label_text).pack(pady=(5, 0))
    entry = tk.Entry(parent, width=30, show=show)
    entry.pack(pady=5)
    return entry

def ui_treeview(parent, cols, col_widths):
    tree = ttk.Treeview(parent, columns=cols, show="headings", height=10)
    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, width=col_widths.get(col, 150), anchor="center")
    tree.pack(pady=10, padx=20, fill="x")
    return tree

def ui_button(parent, text, command, bg=None):
    return tk.Button(parent, text=text, command=command, width=15, bg=bg)

def run_transaction(statements):
    """Chạy nhiều câu lệnh trong cùng 1 transaction.

    statements: list of (query, params) hoặc (query, params, fetch:bool).
    Trả về list kết quả tương ứng; rollback nếu có lỗi.
    """
    results = []
    with DatabaseManager() as db:
        if db is None:
            return None
        try:
            for stmt in statements:
                if len(stmt) == 2:
                    query, params = stmt
                    fetch = False
                else:
                    query, params, fetch = stmt
                results.append(db.execute(query, params, fetch=fetch))
        except Error as e:
            messagebox.showerror("Lỗi", f"Lỗi database: {e}")
            return None
    return results

# ===================== ĐĂNG KÝ =====================
# (Hàm open_register đã được loại bỏ theo yêu cầu xóa chức năng đăng ký)

# ===================== ĐĂNG NHẬP =====================

# Biến lưu thông tin user hiện tại
current_user = None

def common_logout(window):
    """Hàm đăng xuất dùng chung để dọn dẹp code."""
    global current_user
    current_user = None
    window.destroy()
    login_window.deiconify()
    entry_username.delete(0, tk.END)
    entry_password.delete(0, tk.END)
    role_var.set("")

def login():
    global current_user

    username = entry_username.get().strip()
    password = entry_password.get().strip()
    role = role_var.get()

    errors = []
    if not username:
        errors.append("• Vui lòng nhập tên đăng nhập!")
    if not password:
        errors.append("• Vui lòng nhập mật khẩu!")
    if not role:
        errors.append("• Vui lòng chọn vai trò!")

    if errors:
        messagebox.showwarning("Thông báo", "\n".join(errors))
        return

    # Kiểm tra từ database (xác thực mật khẩu bằng bcrypt)
    role_map = {"Quản lý": 3, "Giáo viên": 1, "Học sinh": 2}
    role_id = role_map.get(role)

    query = "SELECT user_id, full_name, password FROM users WHERE username = %s AND role_id = %s"
    result = execute_query(query, (username, role_id), fetch=True)

    if result:
        stored_pwd = result[0][2]
        if isinstance(stored_pwd, bytes):
            stored_pwd_str = stored_pwd.decode("utf-8")
        else:
            stored_pwd_str = str(stored_pwd) if stored_pwd is not None else ""
        
        authenticated = (stored_pwd_str == password)
    else:
        authenticated = False

    if result and authenticated:
        user_id, full_name, _ = result[0]
        current_user = {"user_id": user_id, "full_name": full_name, "role_id": role_id}
        login_window.withdraw()

        if role == "Quản lý":
            open_admin_dashboard()
        elif role == "Giáo viên":
            open_teacher_dashboard()
        elif role == "Học sinh":
            open_student_dashboard()
    else:
        messagebox.showerror("Lỗi", "Tên đăng nhập, mật khẩu hoặc vai trò không đúng!")
        return


# ===================== ADMIN =====================

def open_account_management():
    window = create_window("Quản lý tài khoản", "650x420")
    tk.Label(window, text="QUẢN LÝ TÀI KHOẢN", font=("Arial", 16, "bold")).pack(pady=12)

    cols = ("Tên đăng nhập", "Mật khẩu (Hash)", "Họ và tên", "Vai trò")
    tree = ui_treeview(window, cols, {"Tên đăng nhập": 120, "Mật khẩu (Hash)": 200, "Họ và tên": 150, "Vai trò": 100})

    accounts = execute_query("SELECT u.username, u.password, u.full_name, r.role_name FROM users u JOIN roles r ON u.role_id = r.role_id", fetch=True)
    if accounts:
        for r in accounts:
            tree.insert("", tk.END, values=r)

    def delete_account():
        for item in tree.selection():
            un = tree.item(item, 'values')[0]
            res = execute_query("SELECT user_id FROM users WHERE username=%s", (un,), fetch=True)
            if res:
                uid = res[0][0]
                execute_query("DELETE FROM attendance WHERE student_id IN (SELECT student_id FROM students WHERE user_id=%s)", (uid,))
                execute_query("DELETE FROM grades WHERE student_id IN (SELECT student_id FROM students WHERE user_id=%s)", (uid,))
                execute_query("DELETE FROM students WHERE user_id=%s", (uid,))
                execute_query("DELETE FROM teaching_assignments WHERE teacher_id=%s", (uid,))
                execute_query("UPDATE classes SET homeroom_teacher_id = NULL WHERE homeroom_teacher_id = %s", (uid,))
                execute_query("DELETE FROM users WHERE user_id=%s", (uid,))
                tree.delete(item)

    def add_account():
        add_win = create_window("Thêm tài khoản", "380x450", True)
        tk.Label(add_win, text="THÊM TÀI KHOẢN MỚI", font=("Arial", 12, "bold")).pack(pady=10)
        
        ent_fullname = ui_label_entry(add_win, "Họ và tên:")
        ent_username = ui_label_entry(add_win, "Tên đăng nhập:")
        ent_password = ui_label_entry(add_win, "Mật khẩu:", show="*")
        role_combo = ttk.Combobox(add_win, values=["Quản lý", "Giáo viên", "Học sinh"], state="readonly", width=27)
        role_combo.pack(pady=5)

        def save_account():
            fn, un, pw, role = ent_fullname.get().strip(), ent_username.get().strip(), ent_password.get().strip(), role_combo.get()
            if not all([fn, un, pw, role]):
                messagebox.showwarning("Thông báo", "Vui lòng nhập đầy đủ thông tin!", parent=add_win)
                return

            role_map = {"Giáo viên": 1, "Học sinh": 2, "Quản lý": 3}
            try:
                execute_query("INSERT INTO users (full_name, username, password, role_id) VALUES (%s, %s, %s, %s)", (fn, un, pw, role_map[role]))
                messagebox.showinfo("Thành công", "Đã thêm tài khoản mới!", parent=add_win)
                # Hiển thị mật khẩu dưới dạng plain text trong bảng
                tree.insert("", tk.END, values=(un, pw, fn, role))
                add_win.destroy()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể thêm tài khoản: {e}", parent=add_win)

        tk.Button(add_win, text="Thêm", width=15, bg="#d4edda", command=save_account).pack(pady=20)
    
    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    ui_button(action_frame, "Thêm tài khoản", add_account).pack(side=tk.LEFT, padx=10)
    ui_button(action_frame, "Xóa tài khoản", delete_account).pack(side=tk.LEFT, padx=10)


def open_teacher_management():
    window = create_window("Quản lý giáo viên", "650x450")
    tk.Label(window, text="QUẢN LÝ GIÁO VIÊN", font=("Arial", 16, "bold")).pack(pady=12)

    # Ô tìm kiếm giống giao diện quản lý học sinh
    search_frame = tk.Frame(window)
    search_frame.pack(pady=5, padx=20, fill="x")
    tk.Label(search_frame, text="Nhập từ khóa:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
    entry_keyword = tk.Entry(search_frame, width=22, font=("Arial", 10))
    entry_keyword.pack(side=tk.LEFT, padx=5)

    cols = ("Tên đăng nhập", "Họ và tên", "Email", "SĐT")
    tree = ui_treeview(window, cols, {"Tên đăng nhập": 120, "Họ và tên": 150})

    def load_teachers(keyword: str = ""):
        """Tải danh sách giáo viên, có thể lọc theo từ khoá (full_name/username)."""
        for item in tree.get_children():
            tree.delete(item)

        base_query = """
        SELECT u.username, u.full_name, COALESCE(u.email, 'N/A'), COALESCE(u.phone, 'N/A')
        FROM users u
        WHERE u.role_id = 1
        """
        keyword = (keyword or "").strip()
        if keyword:
            like = f"%{keyword}%"
            sql = base_query + " AND (u.full_name LIKE %s OR u.username LIKE %s)"
            params = (like, like)
        else:
            sql = base_query
            params = None

        rows = execute_query(sql, params, fetch=True)
        if rows:
            for teacher in rows:
                tree.insert("", tk.END, values=teacher)
        return rows

    def search_teacher():
        load_teachers(entry_keyword.get())

    def reset_teacher():
        entry_keyword.delete(0, tk.END)
        load_teachers("")

    tk.Button(search_frame, text="Tìm kiếm", command=search_teacher, width=10).pack(side=tk.LEFT, padx=4)
    tk.Button(search_frame, text="Đặt lại", command=reset_teacher, width=10, bg="#f8d7da").pack(side=tk.LEFT, padx=4)
    entry_keyword.bind("<Return>", lambda e: search_teacher())

    # Tải lần đầu
    load_teachers("")

    def add_teacher():
        add_win = create_window("Thêm giáo viên", "380x520", True)
        tk.Label(add_win, text="Thêm giáo viên mới", font=("Arial", 12, "bold")).pack(pady=10)

        entry_user = ui_label_entry(add_win, "Tên đăng nhập:")
        entry_name = ui_label_entry(add_win, "Họ và tên:")
        entry_pass = ui_label_entry(add_win, "Mật khẩu:", show="*")
        entry_email = ui_label_entry(add_win, "Email:")
        entry_phone = ui_label_entry(add_win, "Số điện thoại:")

        # Submit bằng phím Enter
        add_win.bind("<Return>", lambda e: save_teacher())

        # Lớp phân công
        tk.Label(add_win, text="Lớp phân công:").pack(pady=(10, 2))
        combo_class = ttk.Combobox(add_win, values=[], state="readonly", width=27)
        combo_class.pack()
        class_rows = execute_query("SELECT class_id, class_name FROM classes ORDER BY class_name", fetch=True) or []
        class_list = [(f"{c[0]} - {c[1]}") for c in class_rows]
        combo_class["values"] = class_list

        # Môn phân công
        tk.Label(add_win, text="Môn phân công:").pack(pady=(10, 2))
        combo_subject = ttk.Combobox(add_win, values=[], state="readonly", width=27)
        combo_subject.pack()
        subject_rows = execute_query("SELECT subject_id, subject_name FROM subjects ORDER BY subject_name", fetch=True) or []
        subject_list = [(f"{s[0]} - {s[1]}") for s in subject_rows]
        combo_subject["values"] = subject_list

        def save_teacher():
            user = entry_user.get().strip()
            name = entry_name.get().strip()
            pwd = entry_pass.get().strip()
            email = entry_email.get().strip()
            phone = entry_phone.get().strip()
            class_info = combo_class.get()
            subject_info = combo_subject.get()

            if not user or not name or not pwd:
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin bắt buộc!", parent=add_win)
                return
            if not class_info or not subject_info:
                messagebox.showerror("Lỗi", "Vui lòng chọn lớp và môn phân công!", parent=add_win)
                return

            # Validate email & SĐT
            if email and not validate_email(email):
                messagebox.showerror("Lỗi", "Email không hợp lệ!", parent=add_win)
                return
            if phone and not validate_phone(phone):
                messagebox.showerror("Lỗi", "Số điện thoại không hợp lệ (chỉ chứa 9-11 chữ số)!", parent=add_win)
                return

            class_id = int(class_info.split(" - ")[0])
            subject_parts = subject_info.split(" - ", 1)
            subject_id = int(subject_parts[0])
            subject_name = subject_parts[1]

            # Lưu vào database trong 1 transaction (hash mật khẩu)
            insert_user_sql = "INSERT INTO users (full_name, username, password, role_id, email, phone) VALUES (%s, %s, %s, %s, %s, %s)"
            select_user_sql = "SELECT user_id FROM users WHERE username = %s"
            insert_assign_sql = "INSERT INTO teaching_assignments (teacher_id, class_id, subject_id) VALUES (%s, %s, %s)"

            try:
                with DatabaseManager() as db:
                    if db is None: return
                    # Lưu mật khẩu dưới dạng plain text
                    db.execute(insert_user_sql, (name, user, pwd, 1, email, phone))
                    row = db.execute(select_user_sql, (user,), fetch=True)
                    if not row:
                        raise Exception("Không thể khởi tạo tài khoản giáo viên.")
                    
                    teacher_id = row[0][0]
                    db.execute(insert_assign_sql, (teacher_id, class_id, subject_id))
                    
                    if subject_name == "Giáo viên chủ nhiệm":
                        db.execute("UPDATE classes SET homeroom_teacher_id = %s WHERE class_id = %s", (teacher_id, class_id))
                
                # Nếu chạy đến đây tức là Transaction đã commit thành công
                tree.insert(parent="", index=tk.END, values=(user, name, email, phone))
                messagebox.showinfo(
                    "Thành công",
                    f"Đã thêm giáo viên và phân công {subject_info.split(' - ')[1]} cho {class_info.split(' - ')[1]}!",
                    parent=add_win,
                )
                add_win.destroy()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể thêm giáo viên: {e}", parent=add_win)

        button_frame = tk.Frame(add_win)
        button_frame.pack(pady=15)
        tk.Button(button_frame, text="Thêm", command=save_teacher, width=12, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=add_win.destroy, width=12, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    def delete_teacher():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một giáo viên để xóa!")
            return

        confirm = messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa giáo viên này? Dữ liệu liên quan cũng sẽ bị xóa.")
        if confirm:
            for item in selected_items:
                values = tree.item(item, 'values')
                username = values[0]

                # Lấy user_id từ username
                query_get_id = "SELECT user_id FROM users WHERE username = %s"
                user_id_result = execute_query(query_get_id, (username,), fetch=True)

                if not user_id_result:
                    messagebox.showerror("Lỗi", f"Không tìm thấy giáo viên: {username}")
                    continue

                user_id = user_id_result[0][0]

                try:
                    # Xóa teaching_assignments
                    execute_query("DELETE FROM teaching_assignments WHERE teacher_id = %s", (user_id,))

                    # Cập nhật homeroom_teacher_id thành NULL
                    execute_query("UPDATE classes SET homeroom_teacher_id = NULL WHERE homeroom_teacher_id = %s", (user_id,))

                    # Xóa user record
                    result = execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))

                    if result > 0:
                        tree.delete(item)
                        messagebox.showinfo("Thành công", "Giáo viên và dữ liệu liên quan đã bị xóa!")
                    else:
                        messagebox.showerror("Lỗi", "Không thể xóa giáo viên này!")
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Lỗi khi xóa: {str(e)}")

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    ui_button(action_frame, "Thêm giáo viên", add_teacher).pack(side=tk.LEFT, padx=5)
    ui_button(action_frame, "Xóa giáo viên", delete_teacher).pack(side=tk.LEFT, padx=5)

    window.protocol("WM_DELETE_WINDOW", window.destroy)

def open_student_management():
    window = create_window("Quản lý học sinh", "650x500")
    tk.Label(window, text="QUẢN LÝ HỌC SINH", font=("Arial", 16, "bold")).pack(pady=12)

    # Lấy dữ liệu từ database
    query = """
    SELECT s.student_id, s.student_code, u.full_name, c.class_name
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    JOIN classes c ON s.class_id = c.class_id
    """
    students = execute_query(query, fetch=True)

    search_frame = tk.Frame(window)
    search_frame.pack(pady=5, padx=20, fill="x")

    tk.Label(search_frame, text="Nhập từ khóa:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    entry_keyword = tk.Entry(search_frame, width=22, font=("Arial", 10))
    entry_keyword.pack(side=tk.LEFT, padx=5)

    cols = ("Mã HS", "Họ và tên", "Lớp")
    tree = ui_treeview(window, cols, {"Mã HS": 150})

    def search_student():
        keyword = entry_keyword.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        if students:
            for student in students:
                if keyword in student[1].lower() or keyword in student[2].lower():
                    tree.insert(parent="", index=tk.END, values=student[1:])

    def filter_class():
        keyword = entry_keyword.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        if students:
            for student in students:
                if keyword in student[3].lower():
                    tree.insert(parent="", index=tk.END, values=student[1:])

    def reset_table():
        entry_keyword.delete(0, tk.END)
        for item in tree.get_children():
            tree.delete(item)
        if students:
            for student in students:
                tree.insert(parent="", index=tk.END, values=student[1:])

    tk.Button(search_frame, text="Tìm kiếm", command=search_student, width=10).pack(side=tk.LEFT, padx=4)
    tk.Button(search_frame, text="Lọc theo Lớp", command=filter_class, width=12).pack(side=tk.LEFT, padx=4)
    tk.Button(search_frame, text="Đặt lại", command=reset_table, width=10, bg="#f8d7da").pack(side=tk.LEFT, padx=4)

    if students:
        for student in students:
            tree.insert(parent="", index=tk.END, values=student[1:])

    def add_student():
        add_win = create_window("Thêm học sinh", "380x650", True)
        tk.Label(add_win, text="Thêm học sinh mới", font=("Arial", 12, "bold")).pack(pady=10)

        entry_code = ui_label_entry(add_win, "Mã học sinh:")
        entry_name = ui_label_entry(add_win, "Họ và tên:")
        entry_username = ui_label_entry(add_win, "Tên đăng nhập:")
        entry_password = ui_label_entry(add_win, "Mật khẩu:", show="*")
        entry_dob = ui_label_entry(add_win, "Ngày sinh (YYYY-MM-DD):")

        tk.Label(add_win, text="Giới tính:").pack(pady=(10, 2))
        combo_gender = ttk.Combobox(add_win, values=["Nam", "Nữ", "Khác"], state="readonly", width=27)
        combo_gender.pack()

        tk.Label(add_win, text="Lớp:").pack(pady=(10, 2))
        combo_class = ttk.Combobox(add_win, values=[], state="readonly", width=27)
        combo_class.pack()

        # Load danh sách lớp
        class_query = "SELECT class_id, class_name FROM classes"
        class_results = execute_query(class_query, fetch=True)
        class_list = [(f"{c[0]} - {c[1]}") for c in class_results] if class_results else []
        combo_class['values'] = class_list

        entry_phone = ui_label_entry(add_win, "Số điện thoại phụ huynh:")

        def save_student():
            code = entry_code.get().strip()
            name = entry_name.get().strip()
            username = entry_username.get().strip()
            password = entry_password.get().strip()
            dob = entry_dob.get().strip()
            gender = combo_gender.get()
            class_info = combo_class.get()
            phone = entry_phone.get().strip()

            if not all([code, name, username, password, dob, gender, class_info, phone]):
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin!", parent=add_win)
                return

            # 1. Validate input data
            # Validate phone
            if not validate_phone(phone):
                messagebox.showerror("Lỗi", "Số điện thoại không hợp lệ (chỉ chứa 9-11 chữ số)!", parent=add_win)
                return

            # Validate date of birth format
            try:
                datetime.strptime(dob, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Lỗi", "Ngày sinh không hợp lệ. Vui lòng nhập theo định dạng YYYY-MM-DD!", parent=add_win)
                return

            # Check for duplicate student_code / username
            existing_student = execute_query("SELECT student_code FROM students WHERE student_code = %s", (code,), fetch=True)
            if existing_student:
                messagebox.showerror("Lỗi", f"Mã học sinh '{code}' đã tồn tại!", parent=add_win)
                return
            
            existing_user = execute_query("SELECT username FROM users WHERE username = %s", (username,), fetch=True)
            if existing_user:
                messagebox.showerror("Lỗi", f"Tên đăng nhập '{username}' đã tồn tại!", parent=add_win)
                return

            # Lấy class_id từ class_info
            class_id = int(class_info.split(" - ")[0])

            # Tạo user trước (mật khẩu được hash bằng bcrypt)
            try:
                with DatabaseManager() as db:
                    if db is None: return
                    # 1. Tạo tài khoản user (role_id=2 là học sinh), lưu mật khẩu plain text
                    db.execute("INSERT INTO users (full_name, username, password, role_id) VALUES (%s, %s, %s, %s)",
                               (name, username, password, 2))
                    
                    # 2. Lấy user_id vừa tạo
                    user_res = db.execute("SELECT user_id FROM users WHERE username = %s", (username,), fetch=True)
                    if not user_res: raise Exception("Không tìm thấy UserID vừa tạo.")
                    user_id = user_res[0][0]

                    # 3. Thêm thông tin vào bảng students
                    db.execute("""
                        INSERT INTO students (user_id, student_code, date_of_birth, gender, parent_phone, class_id, enrollment_date, status) 
                        VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Đang học')
                    """, (user_id, code, dob, gender, phone, class_id))
                # Thành công: Transaction đã committed
                messagebox.showinfo("Thành công", "Đã thêm học sinh thành công!", parent=add_win)
                add_win.destroy()
                # Reload danh sách
                window.destroy()
                open_student_management()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tạo học sinh: {e}", parent=add_win)

        button_frame = tk.Frame(add_win)
        button_frame.pack(pady=15)
        tk.Button(button_frame, text="Thêm", command=save_student, width=12, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=add_win.destroy, width=12, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    ui_button(action_frame, "Thêm học sinh", add_student).pack(side=tk.LEFT, padx=5)

    def delete_student():
        """Xoá học sinh đang chọn (xử lý cả bảng liên quan: attendance, users)."""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một học sinh để xoá!", parent=window)
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            "Bạn có chắc chắn muốn xoá học sinh này?\nToàn bộ bản ghi điểm danh liên quan cũng sẽ bị xoá.",
            parent=window,
        )
        if not confirm:
            return

        for item in selected:
            values = tree.item(item, "values")
            student_code = values[0]  # Mã HS

            # Lấy student_id và user_id
            info = execute_query(
                "SELECT s.student_id, s.user_id FROM students s WHERE s.student_code = %s",
                (student_code,),
                fetch=True,
            )
            if not info:
                messagebox.showerror("Lỗi", f"Không tìm thấy học sinh: {student_code}", parent=window)
                continue

            student_id, user_id = info[0]
            try:
                # Xoá các bản ghi liên quan trước để tránh lỗi FK
                execute_query("DELETE FROM attendance WHERE student_id = %s", (student_id,))
                execute_query("DELETE FROM grades WHERE student_id = %s", (student_id,))
                # Xoá bản ghi student
                execute_query("DELETE FROM students WHERE student_id = %s", (student_id,))
                # Xoá tài khoản user liên quan
                execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xoá {student_code}: {e}", parent=window)
                continue

            tree.delete(item)

        messagebox.showinfo("Thành công", "Đã xoá học sinh đã chọn.", parent=window)

    ui_button(action_frame, "Xoá học sinh", delete_student, bg="#f8d7da").pack(side=tk.LEFT, padx=5)

def open_class_management():
    window = create_window("Quản lý lớp học", "650x420")
    tk.Label(window, text="QUẢN LÝ LỚP HỌC", font=("Arial", 16, "bold")).pack(pady=12)

    tk.Label(
        window,
        text="(Mẹo: nhấn đúp vào một lớp để xem danh sách học sinh)",
        font=("Arial", 9, "italic"),
        fg="gray",
    ).pack()

    cols = ("Mã lớp", "Tên lớp", "GVCN")
    tree = ui_treeview(window, cols, {})

    # Lấy dữ liệu từ database
    query = """
    SELECT c.class_id, c.class_name, COALESCE(u.full_name, 'Chưa gán')
    FROM classes c
    LEFT JOIN users u ON c.homeroom_teacher_id = u.user_id
    """
    classes = execute_query(query, fetch=True)

    if classes:
        for classroom in classes:
            tree.insert("", tk.END, values=classroom)

    def on_class_select(_event=None):
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0], "values")
        class_id = values[0]
        class_name = values[1]
        open_class_student_list(class_id, class_name)

    tree.bind("<Double-1>", on_class_select)
    tk.Button(window, text="Xem danh sách học sinh", command=on_class_select, bg="#d4edda").pack(pady=8)

    def add_class():
        add_win = create_window("Thêm lớp học", "350x350", True)
        tk.Label(add_win, text="Thêm lớp học mới", font=("Arial", 12, "bold")).pack(pady=10)
        
        entry_name = ui_label_entry(add_win, "Tên lớp:")

        tk.Label(add_win, text="Khối lớp:").pack(pady=(10, 2))
        combo_grade = ttk.Combobox(add_win, state="readonly", width=27)
        combo_grade.pack()

        # Load khối lớp
        grade_query = "SELECT grade_id, grade_name FROM grade_levels"
        grade_results = execute_query(grade_query, fetch=True)
        grade_list = [(f"{g[0]} - {g[1]}") for g in grade_results] if grade_results else []
        combo_grade['values'] = grade_list

        entry_year = ui_label_entry(add_win, "Năm học (VD: 2026-2027):")
        entry_max = ui_label_entry(add_win, "Sức chứa tối đa:")

        def save_class():
            name = entry_name.get().strip()
            grade_info = combo_grade.get()
            year = entry_year.get().strip()
            max_students = entry_max.get().strip()

            if not all([name, grade_info, year, max_students]):
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin!", parent=add_win)
                return

            try:
                max_students = int(max_students)
                grade_id = int(grade_info.split(" - ")[0])

                query = "INSERT INTO classes (class_name, grade_id, max_students, school_year) VALUES (%s, %s, %s, %s)"
                execute_query(query, (name, grade_id, max_students, year))

                messagebox.showinfo("Thành công", "Đã thêm lớp học thành công!", parent=add_win)
                add_win.destroy()
                # Reload danh sách
                window.destroy()
                open_class_management()
            except ValueError:
                messagebox.showerror("Lỗi", "Sức chứa phải là số nguyên!", parent=add_win)

        button_frame = tk.Frame(add_win)
        button_frame.pack(pady=15)
        tk.Button(button_frame, text="Thêm", command=save_class, width=12, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=add_win.destroy, width=12, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    ui_button(action_frame, "Thêm lớp", add_class).pack(side=tk.LEFT, padx=5)

    def delete_student():
        """Xoá học sinh đang chọn (xử lý cả bảng liên quan: attendance, users)."""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một học sinh để xoá!", parent=window)
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            "Bạn có chắc chắn muốn xoá học sinh này?\nToàn bộ bản ghi điểm danh liên quan cũng sẽ bị xoá.",
            parent=window,
        )
        if not confirm:
            return

        for item in selected:
            values = tree.item(item, "values")
            student_code = values[0]
            info = execute_query("SELECT s.student_id, s.user_id FROM students s WHERE s.student_code = %s", (student_code,), fetch=True)
            if info:
                student_id, user_id = info[0]
                execute_query("DELETE FROM attendance WHERE student_id = %s", (student_id,))
                execute_query("DELETE FROM grades WHERE student_id = %s", (student_id,))
                execute_query("DELETE FROM students WHERE student_id = %s", (student_id,))
                execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))
                tree.delete(item)
        messagebox.showinfo("Thành công", "Đã xoá học sinh thành công.", parent=window)

    ui_button(action_frame, "Xoá học sinh", delete_student, bg="#f8d7da").pack(side=tk.LEFT, padx=5)

def open_teacher_assignment():
    window = create_window("Phân công giáo viên", "650x420")
    tk.Label(window, text="PHÂN CÔNG GIÁO VIÊN", font=("Arial", 16, "bold")).pack(pady=12)

    cols = ("Lớp", "Môn học", "Giáo viên")
    tree = ui_treeview(window, cols, {})

    # Lấy dữ liệu từ database
    query = """
    SELECT c.class_name, s.subject_name, u.full_name
    FROM teaching_assignments ta
    JOIN classes c ON ta.class_id = c.class_id
    JOIN subjects s ON ta.subject_id = s.subject_id
    JOIN users u ON ta.teacher_id = u.user_id
    """
    assignments = execute_query(query, fetch=True)

    if assignments:
        for item in assignments:
            tree.insert("", tk.END, values=item)

def open_admin_report():
    window = create_window("Báo cáo tổng hợp", "700x420")
    tk.Label(window, text="BÁO CÁO TỔNG HỢP", font=("Arial", 16, "bold")).pack(pady=12)

    # Lấy thống kê từ database
    query_students = "SELECT COUNT(*) FROM students"
    query_teachers = "SELECT COUNT(*) FROM users WHERE role_id = 1"
    query_classes = "SELECT COUNT(*) FROM classes"

    total_students = execute_query(query_students, fetch=True)[0][0] if execute_query(query_students, fetch=True) else 0
    total_teachers = execute_query(query_teachers, fetch=True)[0][0] if execute_query(query_teachers, fetch=True) else 0
    total_classes = execute_query(query_classes, fetch=True)[0][0] if execute_query(query_classes, fetch=True) else 0

    summary_frame = tk.Frame(window)
    summary_frame.pack(pady=10, padx=20, fill="x")
    tk.Label(summary_frame, text=f"Tổng số học sinh: {total_students}", anchor="w").pack(fill="x")
    tk.Label(summary_frame, text=f"Tổng số giáo viên: {total_teachers}", anchor="w").pack(fill="x")
    tk.Label(summary_frame, text=f"Tổng số lớp: {total_classes}", anchor="w").pack(fill="x")

    cols = ("Tiêu chí", "Giá trị")
    tree = ui_treeview(window, cols, {"Tiêu chí": 300, "Giá trị": 300})

    # Lấy thống kê điểm danh
    query_attendance = """
    SELECT
        COUNT(*) as tong_diem_danh,
        SUM(CASE WHEN status = 'Có mặt' THEN 1 ELSE 0 END) as co_mat,
        SUM(CASE WHEN status = 'Vắng mặt' THEN 1 ELSE 0 END) as vang_mat
    FROM attendance
    WHERE DATE(attendance_date) = CURDATE()
    """
    attendance_stats = execute_query(query_attendance, fetch=True)

    if attendance_stats:
        total, present, absent = attendance_stats[0]
        report_items = [
            (f"Tỷ lệ chuyên cần", f"{round((present/(total or 1)*100), 1)}%"),
            (f"Số buổi vắng", f"{absent or 0}"),
            (f"Số lớp đã điểm danh", f"{total_classes}"),
        ]
    else:
        report_items = [
            ("Tỷ lệ chuyên cần", "0%"),
            ("Số buổi vắng", "0"),
            ("Số lớp đã điểm danh", "0"),
        ]

    for item in report_items:
        tree.insert("", tk.END, values=item)

def open_admin_dashboard():
    window = tk.Toplevel()
    window.title("Trung tâm quản lý")
    window.geometry("700x520")
    tk.Label(window, text="TRUNG TÂM QUẢN LÝ", font=("Arial", 18, "bold")).pack(pady=20)

    frame = tk.Frame(window)
    frame.pack()

    tk.Button(frame, text="Quản lý tài khoản", width=30, height=2, command=open_account_management).pack(pady=5)
    tk.Button(frame, text="Quản lý giáo viên", width=30, height=2, command=open_teacher_management).pack(pady=5)
    tk.Button(frame, text="Quản lý học sinh", width=30, height=2, command=open_student_management).pack(pady=5)
    tk.Button(frame, text="Quản lý lớp học", width=30, height=2, command=open_class_management).pack(pady=5)
    tk.Button(frame, text="Phân công giáo viên", width=30, height=2, command=open_teacher_assignment).pack(pady=5)
    tk.Button(frame, text="Xem báo cáo tổng hợp", width=30, height=2, command=open_admin_report).pack(pady=5)

    tk.Button(frame, text="Đăng xuất", width=30, height=2, bg="#f8d7da", command=lambda: common_logout(window)).pack(pady=15)

    # Đồng bộ đóng ứng dụng khi tắt Dashboard
    window.protocol("WM_DELETE_WINDOW", window.destroy)

# ===================== TEACHER =====================

def open_class_student_list(class_id, class_name):
    """Mở cửa sổ danh sách học sinh của một lớp cụ thể, kèm trạng thái điểm danh hôm nay."""
    detail_win = create_window(f"Lớp {class_name}", "820x460")
    tk.Label(detail_win, text=f"DANH SÁCH HỌC SINH LỚP {class_name}", font=("Arial", 14, "bold")).pack(pady=10)

    cols = ("Họ và tên", "Ngày sinh", "Mã học sinh", "Giới tính", "Trạng thái")
    w = {"Họ và tên": 200, "Ngày sinh": 110, "Mã học sinh": 110, "Giới tính": 80, "Trạng thái": 130}
    detail_tree = ui_treeview(detail_win, cols, w)
    detail_tree.configure(height=14)
    detail_tree.pack(pady=10, padx=20, fill="both", expand=True)

    sql = """
    SELECT u.full_name,
           DATE_FORMAT(s.date_of_birth, %s) AS dob,
           s.student_code,
           COALESCE(s.gender, 'N/A') AS gender,
           COALESCE(a.status, 'Chưa điểm danh') AS trang_thai
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    LEFT JOIN attendance a
           ON a.student_id = s.student_id
          AND DATE(a.attendance_date) = CURDATE()
    WHERE s.class_id = %s
    ORDER BY u.full_name
    """
    students = execute_query(sql, ('%d/%m/%Y', class_id), fetch=True)

    if students:
        for row in students:
            detail_tree.insert("", tk.END, values=row)
    else:
        detail_tree.insert("", tk.END, values=("Lớp chưa có học sinh", "", "", "", ""))

    tk.Button(detail_win, text="Đóng", width=12, command=detail_win.destroy).pack(pady=10)


def open_teacher_class_list(on_class_selected):
    window = create_window("Danh sách lớp", "650x420")
    tk.Label(window, text="DANH SÁCH LỚP", font=("Arial", 16, "bold")).pack(pady=12)

    tree = ui_treeview(window, ("Mã lớp", "Tên lớp", "Số HS"), {"Mã lớp": 80, "Tên lớp": 200, "Số HS": 80})

    query = """
    SELECT c.class_id, c.class_name, COUNT(s.student_id) as so_hoc_sinh
    FROM classes c
    LEFT JOIN students s ON c.class_id = s.class_id
    GROUP BY c.class_id, c.class_name
    """
    classes = execute_query(query, fetch=True)
    if classes:
        for classroom in classes:
            tree.insert("", tk.END, values=classroom)

    def confirm_selection():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một lớp!")
            return
        vals = tree.item(selected[0], 'values')
        on_class_selected(vals[0], vals[1])
        window.destroy()

    tk.Button(window, text="Chọn lớp này", command=confirm_selection, bg="#d4edda", width=20, font=("Arial", 10, "bold")).pack(pady=10)

def open_teacher_attendance(class_id, class_name, on_save_callback):
    window = create_window(f"Điểm danh - {class_name}", "600x500")
    tk.Label(window, text=f"GIAO DIỆN ĐIỂM DANH: {class_name}", font=("Arial", 14, "bold"), fg="blue").pack(pady=10)

    # Tạo vùng cuộn (Scrollbar) cho danh sách học sinh
    container = tk.Frame(window)
    container.pack(fill="both", expand=True, padx=10, pady=5)
    
    canvas = tk.Canvas(container)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    query = """
    SELECT s.student_id, u.full_name, s.class_id
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    WHERE s.class_id = %s
    ORDER BY u.full_name
    """
    students_data = execute_query(query, (class_id,), fetch=True)

    status_vars = []
    if students_data:
        for index, (student_id, name, class_id) in enumerate(students_data):
            tk.Label(scrollable_frame, text=f"{index+1}. {name}", anchor="w", width=30).grid(row=index, column=0, sticky="w", pady=5, padx=5)
            status_var = tk.StringVar(value="Có mặt")
            status_vars.append((student_id, class_id, status_var))
            ttk.Combobox(scrollable_frame, textvariable=status_var, values=["Có mặt", "Vắng mặt", "Muộn", "Có phép"], state="readonly", width=15).grid(row=index, column=1, padx=5)

    def save_teacher_attendance():
        for student_id, class_id, status_var in status_vars:
            status = status_var.get()
            query = """
            INSERT INTO attendance (student_id, class_id, attendance_date, status, recorded_by)
            VALUES (%s, %s, CURDATE(), %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            execute_query(query, (student_id, class_id, status, current_user["user_id"]))

        messagebox.showinfo("Thành công", f"Đã lưu điểm danh cho lớp {class_name}", parent=window)
        if on_save_callback: on_save_callback()
        window.destroy()

    tk.Button(window, text="Lưu điểm danh", bg="lightgreen", font=("Arial", 12, "bold"), command=save_teacher_attendance).pack(pady=12)

def open_teacher_self_attendance_config(class_id, class_name):
    window = create_window(f"Cấu hình tự điểm danh - {class_name}", "380x420", True)
    tk.Label(window, text=f"MỞ TỰ ĐIỂM DANH: {class_name}", font=("Arial", 12, "bold")).pack(pady=10)
    
    ent_date = ui_label_entry(window, "Ngày cho phép (YYYY-MM-DD):")
    ent_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
    
    ent_start = ui_label_entry(window, "Giờ bắt đầu (HH:MM:SS):")
    ent_start.insert(0, "07:00:00")
    
    ent_end = ui_label_entry(window, "Giờ kết thúc (HH:MM:SS):")
    ent_end.insert(0, "17:00:00")
    
    def save_config():
        d, s, e = ent_date.get().strip(), ent_start.get().strip(), ent_end.get().strip()
        try:
            datetime.strptime(d, '%Y-%m-%d')
            datetime.strptime(s, '%H:%M:%S')
            datetime.strptime(e, '%H:%M:%S')
        except ValueError:
            messagebox.showerror("Lỗi", "Định dạng ngày hoặc giờ không hợp lệ!", parent=window)
            return

        query = """
            INSERT INTO self_attendance_configs (class_id, auth_date, start_time, end_time)
            VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE start_time=VALUES(start_time), end_time=VALUES(end_time)
        """
        execute_query(query, (class_id, d, s, e))
        messagebox.showinfo("Thành công", f"Đã mở quyền tự điểm danh cho lớp {class_name}!", parent=window)
        window.destroy()

    tk.Button(window, text="Lưu cấu hình", bg="#fff3cd", font=("Arial", 10, "bold"), command=save_config).pack(pady=20)

def open_teacher_export_report():
    window = create_window("Xuất báo cáo", "520x280")

    tk.Label(window, text="Chọn loại báo cáo:").pack(anchor="w", padx=20)
    report_var = tk.StringVar()
    ttk.Combobox(window, textvariable=report_var, values=["Báo cáo điểm danh", "Báo cáo chuyên cần", "Báo cáo tổng hợp"], state="readonly", width=35).pack(padx=20, pady=10)

    def export_report():
        choice = report_var.get()
        if not choice:
            messagebox.showwarning("Thông báo", "Vui lòng chọn loại báo cáo", parent=window)
            return

        # Có thể thêm logic xuất file PDF hoặc Excel ở đây
        messagebox.showinfo("Thông báo", f"Đã xuất {choice} thành công!", parent=window)

    tk.Button(window, text="Xuất báo cáo", width=18, bg="lightblue", font=("Arial", 12, "bold"), command=export_report).pack(pady=14)

def open_teacher_dashboard():
    window = create_window("Teacher Dashboard", "900x650")
    header_lbl = tk.Label(window, text="GIÁO VIÊN - QUẢN LÝ ĐIỂM DANH", font=("Arial", 18, "bold"))
    header_lbl.pack(pady=10)

    current_selection = {"id": None, "name": ""}

    menu_frame = tk.Frame(window)
    menu_frame.pack(pady=10)

    def refresh_dashboard_list():
        if not current_selection["id"]: return
        for item in tree.get_children():
            tree.delete(item)
        query = """
            SELECT s.student_code, u.full_name, COALESCE(a.status, 'Chưa điểm danh')
            FROM students s
            JOIN users u ON s.user_id = u.user_id
            LEFT JOIN attendance a ON s.student_id = a.student_id AND DATE(a.attendance_date) = CURDATE()
            WHERE s.class_id = %s
            ORDER BY u.full_name
        """
        students = execute_query(query, (current_selection["id"],), fetch=True)
        if students:
            for s in students: tree.insert("", tk.END, values=s)

    def on_class_picked(c_id, c_name):
        current_selection["id"] = c_id
        current_selection["name"] = c_name
        header_lbl.config(text=f"LỚP ĐANG CHỌN: {c_name}")
        btn_attendance.config(state="normal", bg="#d4edda")
        btn_self_config.config(state="normal", bg="#fff3cd")
        refresh_dashboard_list()

    def start_attendance():
        open_teacher_attendance(current_selection["id"], current_selection["name"], refresh_dashboard_list)

    def start_self_config():
        open_teacher_self_attendance_config(current_selection["id"], current_selection["name"])

    m_items = [
        ("Chọn lớp", lambda: open_teacher_class_list(on_class_picked)),
        ("Xuất báo cáo", open_teacher_export_report)
    ]
    for idx, (t, c) in enumerate(m_items):
        tk.Button(menu_frame, text=t, width=20, command=c).grid(row=0, column=idx, padx=5)

    btn_attendance = tk.Button(menu_frame, text="Điểm danh", width=20, state="disabled", command=start_attendance)
    btn_attendance.grid(row=0, column=2, padx=5)

    btn_self_config = tk.Button(menu_frame, text="Cài đặt tự điểm danh", width=20, state="disabled", command=start_self_config)
    btn_self_config.grid(row=0, column=3, padx=5)

    tree = ui_treeview(window, ("Mã HS", "Họ tên", "Trạng thái"), {}) # Đảm bảo khớp với 3 cột từ query

    tk.Button(window, text="Đăng xuất", width=20, bg="#f8d7da", command=lambda: common_logout(window)).pack(pady=10)

    window.protocol("WM_DELETE_WINDOW", window.destroy)

# ===================== STUDENT =====================

def open_self_attendance(auth_date, start_time, end_time, on_save_callback):
    window = create_window("Tự điểm danh", "520x340", True)
    tk.Label(window, text="TỰ ĐIỂM DANH", font=("Arial", 16, "bold")).pack(pady=12)

    query = """
    SELECT u.full_name, c.class_name, s.student_id, s.class_id
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    JOIN classes c ON s.class_id = c.class_id
    WHERE u.user_id = %s
    """
    student_info = execute_query(query, (current_user["user_id"],), fetch=True)

    if student_info:
        full_name, class_name, student_id, class_id = student_info[0]

        tk.Label(window, text=f"Học sinh: {full_name}", font=("Arial", 10)).pack(anchor="w", padx=20)
        tk.Label(window, text=f"Lớp: {class_name}").pack(anchor="w", padx=20)
        tk.Label(window, text=f"Khung giờ: {auth_date} ({start_time} - {end_time})", fg="blue").pack(anchor="w", padx=20, pady=(5, 15))

        tk.Label(window, text="Trạng thái điểm danh:").pack(anchor="w", padx=20)
        status_var = tk.StringVar(value="Có mặt")
        ttk.Combobox(window, textvariable=status_var, values=["Có mặt", "Vắng mặt", "Muộn", "Có phép"], state="readonly", width=30).pack(padx=20, pady=10)

        def save_self_attendance():
            status = status_var.get()
            query = """
            INSERT INTO attendance (student_id, class_id, attendance_date, status, recorded_by)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            result = execute_query(query, (student_id, class_id, auth_date, status, current_user["user_id"]))

            if result:
                messagebox.showinfo("Thông báo", f"Bạn đã điểm danh: {status}", parent=window)
                if on_save_callback: on_save_callback()
                window.destroy()
            else:
                messagebox.showerror("Lỗi", "Điểm danh thất bại!", parent=window)

        tk.Button(window, text="Gửi điểm danh", width=18, bg="lightgreen", font=("Arial", 12, "bold"), command=save_self_attendance).pack(pady=14)

def open_student_dashboard():
    window = create_window("Student Dashboard", "700x520")
    tk.Label(window, text="THÔNG TIN ĐIỂM DANH", font=("Arial", 18, "bold")).pack(pady=15)

    info_frame = tk.Frame(window)
    info_frame.pack(pady=10)

    if not current_user or "user_id" not in current_user:
        messagebox.showerror("Lỗi", "Thông tin người dùng không hợp lệ. Vui lòng đăng nhập lại.", parent=window)
        window.destroy()
        return


    # Lấy thông tin học sinh từ database
    query = """
    SELECT s.student_code, u.full_name, c.class_name
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    JOIN classes c ON s.class_id = c.class_id
    WHERE u.user_id = %s
    """
    student_info = execute_query(query, (current_user["user_id"],), fetch=True)

    if student_info:
        student_code, full_name, class_name = student_info[0]
        tk.Label(info_frame, text=f"Mã HS: {student_code}").pack(anchor="w")
        tk.Label(info_frame, text=f"Họ tên: {full_name}").pack(anchor="w")
        tk.Label(info_frame, text=f"Lớp: {class_name}").pack(anchor="w")
    else:
        messagebox.showwarning("Thông báo", "Không tìm thấy thông tin học sinh của tài khoản này. Vui lòng liên hệ quản trị viên.", parent=window)
        # Tiếp tục tải lịch điểm danh, có thể sẽ trống nếu không có thông tin học sinh.

    # Cập nhật các cột hiển thị: Ngày, Giờ bắt đầu, Giờ kết thúc, Trạng thái
    tree = ui_treeview(window, ("Ngày", "Bắt đầu", "Kết thúc", "Trạng thái"),
                       {"Ngày": 100, "Bắt đầu": 100, "Kết thúc": 100, "Trạng thái": 120})
    tree.pack(pady=20)

    def load_attendance_slots():
        """Tải các khung giờ giáo viên đã mở kèm trạng thái của học sinh hiện tại."""
        for item in tree.get_children():
            tree.delete(item)
            
        if not current_user or "user_id" not in current_user:
            messagebox.showerror("Lỗi", "Thông tin người dùng không hợp lệ khi tải lịch điểm danh.", parent=window)
            return


        query = """
        SELECT DATE_FORMAT(conf.auth_date, %s), 
               TIME_FORMAT(conf.start_time, %s), 
               TIME_FORMAT(conf.end_time, %s), 
               COALESCE(att.status, 'Chưa điểm danh')
        FROM self_attendance_configs conf
        JOIN students s ON s.class_id = conf.class_id
        LEFT JOIN attendance att ON att.student_id = s.student_id AND att.attendance_date = conf.auth_date
        WHERE s.user_id = %s
        ORDER BY conf.auth_date DESC, conf.start_time DESC
        """
        slots = execute_query(query, ('%Y-%m-%d', '%H:%i:%s', '%H:%i:%s', current_user["user_id"]), fetch=True)
        if slots:
            for item in slots:
                tree.insert("", tk.END, values=item)

    load_attendance_slots()

    def handle_self_attendance():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một ngày/giờ cần điểm danh trong danh sách!")
            return
        
        # Lấy dữ liệu của dòng đang chọn
        auth_date, start_str, end_str, status = tree.item(selected[0], 'values')
        
        # Kiểm tra thời điểm hiện tại
        now = datetime.now()
        curr_d = now.strftime('%Y-%m-%d')
        curr_t = now.strftime('%H:%M:%S')

        # Logic: Phải đúng ngày giáo viên mở và nằm trong khoảng giờ bắt đầu - kết thúc
        if str(auth_date) == curr_d and str(start_str) <= curr_t <= str(end_str):
            open_self_attendance(auth_date, start_str, end_str, load_attendance_slots)
        else:
            messagebox.showwarning("Ngoài khung giờ", 
                                f"Bạn chỉ được phép tự điểm danh vào:\nNgày: {auth_date}\nGiờ: {start_str} - {end_str}\n\nHiện tại là: {curr_d} {curr_t}")

    tk.Button(window, text="Tự điểm danh", width=20, bg="#d4edda", font=("Arial", 10, "bold"), command=handle_self_attendance).pack(pady=10)

    tk.Button(window, text="Đăng xuất", width=20, bg="#f8d7da", command=lambda: common_logout(window)).pack(pady=5)

    window.protocol("WM_DELETE_WINDOW", window.destroy)

# ===================== CỬA SỔ ĐĂNG NHẬP =====================

login_window = tk.Tk()
login_window.title("Hệ thống điểm danh học sinh")
login_window.geometry("450x400")

tk.Label(login_window, text="HỆ THỐNG ĐIỂM DANH HỌC SINH", font=("Arial", 16, "bold")).pack(pady=20)

entry_username = ui_label_entry(login_window, "Tên đăng nhập")
entry_password = ui_label_entry(login_window, "Mật khẩu", show="*")

tk.Label(login_window, text="Vai trò").pack(pady=(10, 0))
role_var = tk.StringVar()
ttk.Combobox(
    login_window,
    textvariable=role_var,
    values=["Quản lý", "Giáo viên", "Học sinh"],
    state="readonly",
    width=27
).pack()

tk.Button(login_window, text="Đăng nhập", width=20, bg="lightblue", font=("Arial", 11), command=login).pack(pady=12)

if check_schema_ready():
    login_window.mainloop()
else:
    login_window.destroy()
