import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import bcrypt
import os
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
    "grade_levels",
]

REQUIRED_SCHEMA_HINT = """
Vui lòng chạy file setup_database.py để khởi tạo đầy đủ 9 bảng cần thiết trước khi khởi động ứng dụng.
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
            "\n\nVui lòng chạy file schema.sql đính kèm trước khi sử dụng.\n\n" + REQUIRED_SCHEMA_HINT,
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
    role_map = {"Quản trị viên": 3, "Giáo viên": 1, "Học sinh": 2}
    role_id = role_map.get(role)

    query = "SELECT user_id, full_name, password FROM users WHERE username = %s AND role_id = %s"
    result = execute_query(query, (username, role_id), fetch=True)

    if result:
        stored_pwd = result[0][2]
        if isinstance(stored_pwd, bytes):
            stored_pwd_str = stored_pwd.decode("utf-8", errors="ignore")
        else:
            stored_pwd_str = str(stored_pwd) if stored_pwd is not None else ""
        authenticated = False
        # Thử bcrypt trước
        try:
            if stored_pwd_str.startswith("$2"):
                authenticated = bcrypt.checkpw(password.encode("utf-8"), stored_pwd_str.encode("utf-8"))
        except Exception:
            authenticated = False
        # Fallback: so sánh plain text (cho tài khoản đăng ký cũ chưa được hash)
        if not authenticated and stored_pwd_str == password:
            authenticated = True
            # Tự động nâng cấp lên bcrypt
            try:
                pwd_hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                execute_query(
                    "UPDATE users SET password = %s WHERE user_id = %s",
                    (pwd_hashed, result[0][0]),
                )
            except Exception:
                pass
    else:
        authenticated = False

    if result and authenticated:
        user_id, full_name, _ = result[0]
        current_user = {"user_id": user_id, "full_name": full_name, "role_id": role_id}
        login_window.withdraw()

        if role == "Quản trị viên":
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
    window = tk.Toplevel()
    window.title("Quản lý tài khoản")
    window.geometry("650x420")

    tk.Label(window, text="QUẢN LÝ TÀI KHOẢN", font=("Arial", 16, "bold")).pack(pady=12)

    columns = ("Tên đăng nhập", "Họ và tên", "Vai trò")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

    # Lấy dữ liệu từ database
    query = """
    SELECT u.username, u.full_name, r.role_name
    FROM users u
    JOIN roles r ON u.role_id = r.role_id
    """
    accounts = execute_query(query, fetch=True)

    if accounts:
        for account in accounts:
            tree.insert("", tk.END, values=account)

    def delete_account():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tài khoản để xóa!")
            return

        confirm = messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa tài khoản này? Dữ liệu liên quan cũng sẽ bị xóa.")
        if confirm:
            for item in selected_items:
                values = tree.item(item, 'values')
                username = values[0]

                # Lấy user_id từ username
                query_get_id = "SELECT user_id FROM users WHERE username = %s"
                user_id_result = execute_query(query_get_id, (username,), fetch=True)

                if not user_id_result:
                    messagebox.showerror("Lỗi", f"Không tìm thấy tài khoản: {username}")
                    continue

                user_id = user_id_result[0][0]

                try:
                    # Xóa các dữ liệu liên quan
                    # 1. Xóa attendance records
                    execute_query("DELETE FROM attendance WHERE student_id IN (SELECT student_id FROM students WHERE user_id = %s)", (user_id,))

                    # 2. Xóa grades records
                    execute_query("DELETE FROM grades WHERE student_id IN (SELECT student_id FROM students WHERE user_id = %s)", (user_id,))

                    # 3. Xóa teaching_assignments (nếu là giáo viên)
                    execute_query("DELETE FROM teaching_assignments WHERE teacher_id = %s", (user_id,))

                    # 4. Cập nhật homeroom_teacher_id thành NULL (nếu là GVCN)
                    execute_query("UPDATE classes SET homeroom_teacher_id = NULL WHERE homeroom_teacher_id = %s", (user_id,))

                    # 5. Xóa student record
                    execute_query("DELETE FROM students WHERE user_id = %s", (user_id,))

                    # 6. Xóa user record
                    result = execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))

                    if result > 0:
                        tree.delete(item)
                        messagebox.showinfo("Thành công", "Tài khoản và dữ liệu liên quan đã bị xóa!")
                    else:
                        messagebox.showerror("Lỗi", "Không thể xóa tài khoản này!")
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Lỗi khi xóa: {str(e)}")

    def add_account():
        add_win = tk.Toplevel(window)
        add_win.title("Thêm tài khoản")
        add_win.geometry("300x250")
        add_win.grab_set()

        tk.Label(add_win, text="Tên đăng nhập:").pack(pady=(10, 2))
        entry_user = tk.Entry(add_win, width=30)
        entry_user.pack()

        tk.Label(add_win, text="Họ và tên:").pack(pady=(10, 2))
        entry_name = tk.Entry(add_win, width=30)
        entry_name.pack()

        tk.Label(add_win, text="Mật khẩu:").pack(pady=(10, 2))
        entry_pass = tk.Entry(add_win, width=30, show="*")
        entry_pass.pack()

        tk.Label(add_win, text="Vai trò:").pack(pady=(10, 2))
        combo_role = ttk.Combobox(add_win, values=["Giáo viên", "Học sinh", "Quản lý"], state="readonly", width=27)
        combo_role.pack()

        def save_new_account():
            user = entry_user.get().strip()
            name = entry_name.get().strip()
            pwd = entry_pass.get().strip()
            role = combo_role.get()

            if not user or not name or not pwd or not role:
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin!")
                return

            # Lưu vào database
            role_map = {"Giáo viên": 1, "Học sinh": 2, "Quản lý": 3}
            role_id = role_map.get(role, 2)

            # Hash mật khẩu trước khi lưu (Sửa lỗi bảo mật)
            pwd_hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt())
            query = "INSERT INTO users (full_name, username, password, role_id) VALUES (%s, %s, %s, %s)"
            result = execute_query(query, (name, user, pwd_hashed, role_id))

            if result:
                tree.insert(parent="", index=tk.END, values=(user, name, role))
                messagebox.showinfo("Thành công", "Đã thêm tài khoản thành công!")
                add_win.destroy()
            else:
                messagebox.showerror("Lỗi", "Tài khoản đã tồn tại hoặc lỗi khác!")

        button_frame = tk.Frame(add_win)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="Thêm", command=save_new_account, width=12, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=add_win.destroy, width=12, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    tk.Button(action_frame, text="Thêm tài khoản", width=15, command=add_account).pack(side=tk.LEFT, padx=10)
    tk.Button(action_frame, text="Xóa tài khoản", width=15, command=delete_account).pack(side=tk.LEFT, padx=10)


def open_teacher_management():
    window = tk.Toplevel()
    window.title("Quản lý giáo viên")
    window.geometry("650x450")

    tk.Label(window, text="QUẢN LÝ GIÁO VIÊN", font=("Arial", 16, "bold")).pack(pady=12)

    # Ô tìm kiếm giống giao diện quản lý học sinh
    search_frame = tk.Frame(window)
    search_frame.pack(pady=5, padx=20, fill="x")
    tk.Label(search_frame, text="Nhập từ khóa:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
    entry_keyword = tk.Entry(search_frame, width=22, font=("Arial", 10))
    entry_keyword.pack(side=tk.LEFT, padx=5)

    columns = ("Tên đăng nhập", "Họ và tên", "Email", "SĐT")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=140)
    tree.pack(pady=10, padx=20, fill="x")

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
        add_win = tk.Toplevel(window)
        add_win.title("Thêm giáo viên")
        add_win.geometry("380x500")
        add_win.grab_set()

        tk.Label(add_win, text="Thêm giáo viên mới", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(add_win, text="Tên đăng nhập:").pack(pady=(10, 2))
        entry_user = tk.Entry(add_win, width=30)
        entry_user.pack()

        tk.Label(add_win, text="Họ và tên:").pack(pady=(10, 2))
        entry_name = tk.Entry(add_win, width=30)
        entry_name.pack()

        tk.Label(add_win, text="Mật khẩu:").pack(pady=(10, 2))
        entry_pass = tk.Entry(add_win, width=30, show="*")
        entry_pass.pack()

        tk.Label(add_win, text="Email:").pack(pady=(10, 2))
        entry_email = tk.Entry(add_win, width=30)
        entry_email.pack()

        tk.Label(add_win, text="Số điện thoại:").pack(pady=(10, 2))
        entry_phone = tk.Entry(add_win, width=30)
        entry_phone.pack()

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
            subject_id = int(subject_info.split(" - ")[0])

            # Lưu vào database trong 1 transaction (hash mật khẩu)
            pwd_hashed = bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt())
            insert_user_sql = "INSERT INTO users (full_name, username, password, role_id, email, phone) VALUES (%s, %s, %s, %s, %s, %s)"
            select_user_sql = "SELECT user_id FROM users WHERE username = %s"
            insert_assign_sql = "INSERT INTO teaching_assignments (teacher_id, class_id, subject_id) VALUES (%s, %s, %s)"

            teacher_id = None
            with DatabaseManager() as db:
                if db is None:
                    return
                try:
                    db.execute(insert_user_sql, (name, user, pwd_hashed, 1, email, phone))
                    row = db.execute(select_user_sql, (user,), fetch=True)
                    if row:
                        teacher_id = row[0][0]
                        db.execute(insert_assign_sql, (teacher_id, class_id, subject_id))
                except mysql.connector.errors.IntegrityError as e:
                    messagebox.showerror("Lỗi", f"Tên đăng nhập đã tồn tại hoặc dữ liệu không hợp lệ: {e}", parent=add_win)
                    return
                except Error as e:
                    messagebox.showerror("Lỗi", f"Lỗi database: {e}", parent=add_win)
                    return

            if teacher_id:
                tree.insert(parent="", index=tk.END, values=(user, name, email, phone))
                messagebox.showinfo(
                    "Thành công",
                    f"Đã thêm giáo viên và phân công {subject_info.split(' - ')[1]} cho {class_info.split(' - ')[1]}!",
                    parent=add_win,
                )
                add_win.destroy()
            else:
                messagebox.showerror("Lỗi", "Không thể tạo giáo viên!", parent=add_win)
            return

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
    tk.Button(action_frame, text="Thêm giáo viên", width=15, command=add_teacher).pack(side=tk.LEFT, padx=5)
    tk.Button(action_frame, text="Xóa giáo viên", width=15, command=delete_teacher).pack(side=tk.LEFT, padx=5)

    window.protocol("WM_DELETE_WINDOW", window.destroy)


def open_student_management():
    window = tk.Toplevel()
    window.title("Quản lý học sinh")
    window.geometry("650x500")

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

    columns = ("Mã HS", "Họ và tên", "Lớp")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

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
        add_win = tk.Toplevel(window)
        add_win.title("Thêm học sinh")
        add_win.geometry("380x520")
        add_win.grab_set()

        tk.Label(add_win, text="Thêm học sinh mới", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(add_win, text="Mã học sinh:").pack(pady=(10, 2))
        entry_code = tk.Entry(add_win, width=30)
        entry_code.pack()

        tk.Label(add_win, text="Họ và tên:").pack(pady=(10, 2))
        entry_name = tk.Entry(add_win, width=30)
        entry_name.pack()

        tk.Label(add_win, text="Ngày sinh (YYYY-MM-DD):").pack(pady=(10, 2))
        entry_dob = tk.Entry(add_win, width=30)
        entry_dob.pack()

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

        tk.Label(add_win, text="Số điện thoại phụ huynh:").pack(pady=(10, 2))
        entry_phone = tk.Entry(add_win, width=30)
        entry_phone.pack()

        # Checkbox tuỳ chọn: có tự động điểm danh "Có mặt" cho hôm nay hay không
        attendance_today_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            add_win,
            text="Điểm danh 'Có mặt' cho hôm nay",
            variable=attendance_today_var,
        ).pack(pady=(8, 0))

        def save_student():
            code = entry_code.get().strip()
            name = entry_name.get().strip()
            dob = entry_dob.get().strip()
            gender = combo_gender.get()
            class_info = combo_class.get()
            phone = entry_phone.get().strip()

            if not all([code, name, dob, gender, class_info, phone]):
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ thông tin!", parent=add_win)
                return

            # Lấy class_id từ class_info
            class_id = int(class_info.split(" - ")[0])

            # Tạo user trước (mật khẩu mặc định được hash bằng bcrypt)
            username = code.lower()
            default_pwd = "123456"
            pwd_hashed = bcrypt.hashpw(default_pwd.encode("utf-8"), bcrypt.gensalt())
            user_query = "INSERT INTO users (full_name, username, password, role_id) VALUES (%s, %s, %s, %s)"
            execute_query(user_query, (name, username, pwd_hashed, 2))  # role_id=2 là học sinh

            # Lấy user_id vừa tạo
            user_id_query = "SELECT user_id FROM users WHERE username = %s"
            user_result = execute_query(user_id_query, (username,), fetch=True)

            if user_result:
                user_id = user_result[0][0]

                # Thêm student record (chỉ INSERT vào bảng students, KHÔNG tạo attendance)
                student_query = "INSERT INTO students (user_id, student_code, date_of_birth, gender, parent_phone, class_id, enrollment_date, status) VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Đang học')"
                execute_query(student_query, (user_id, code, dob, gender, phone, class_id))

                # Chỉ tạo bản ghi attendance nếu người dùng tick chọn
                if attendance_today_var.get():
                    student_id_row = execute_query(
                        "SELECT student_id FROM students WHERE user_id = %s", (user_id,), fetch=True
                    )
                    if student_id_row:
                        student_id = student_id_row[0][0]
                        execute_query(
                            "INSERT INTO attendance (student_id, class_id, attendance_date, status, recorded_by) VALUES (%s, %s, CURDATE(), 'Có mặt', %s)",
                            (student_id, class_id, user_id),
                        )

                messagebox.showinfo("Thành công", "Đã thêm học sinh thành công!", parent=add_win)
                add_win.destroy()
                # Reload danh sách
                window.destroy()
                open_student_management()
            else:
                messagebox.showerror("Lỗi", "Không thể tạo học sinh!", parent=add_win)

        button_frame = tk.Frame(add_win)
        button_frame.pack(pady=15)
        tk.Button(button_frame, text="Thêm", command=save_student, width=12, bg="#d4edda", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hủy", command=add_win.destroy, width=12, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    tk.Button(action_frame, text="Thêm học sinh", width=15, command=add_student).pack(side=tk.LEFT, padx=5)

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

    tk.Button(action_frame, text="Xoá học sinh", width=15, bg="#f8d7da", command=delete_student).pack(side=tk.LEFT, padx=5)

def open_class_management():
    window = tk.Toplevel()
    window.title("Quản lý lớp học")
    window.geometry("650x420")

    tk.Label(window, text="QUẢN LÝ LỚP HỌC", font=("Arial", 16, "bold")).pack(pady=12)

    tk.Label(
        window,
        text="(Mẹo: nhấn đúp vào một lớp để xem danh sách học sinh)",
        font=("Arial", 9, "italic"),
        fg="gray",
    ).pack()

    columns = ("Mã lớp", "Tên lớp", "GVCN")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

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
        add_win = tk.Toplevel(window)
        add_win.title("Thêm lớp học")
        add_win.geometry("350x300")
        add_win.grab_set()

        tk.Label(add_win, text="Thêm lớp học mới", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(add_win, text="Tên lớp:").pack(pady=(10, 2))
        entry_name = tk.Entry(add_win, width=30)
        entry_name.pack()

        tk.Label(add_win, text="Khối lớp:").pack(pady=(10, 2))
        combo_grade = ttk.Combobox(add_win, state="readonly", width=27)
        combo_grade.pack()

        # Load khối lớp
        grade_query = "SELECT grade_id, grade_name FROM grade_levels"
        grade_results = execute_query(grade_query, fetch=True)
        grade_list = [(f"{g[0]} - {g[1]}") for g in grade_results] if grade_results else []
        combo_grade['values'] = grade_list

        tk.Label(add_win, text="Năm học (VD: 2026-2027):").pack(pady=(10, 2))
        entry_year = tk.Entry(add_win, width=30)
        entry_year.pack()

        tk.Label(add_win, text="Sức chứa tối đa:").pack(pady=(10, 2))
        entry_max = tk.Entry(add_win, width=30)
        entry_max.pack()

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
    tk.Button(action_frame, text="Thêm lớp", width=15, command=add_class).pack(side=tk.LEFT, padx=5)

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

    tk.Button(action_frame, text="Xoá học sinh", width=15, bg="#f8d7da", command=delete_student).pack(side=tk.LEFT, padx=5)

def open_teacher_assignment():
    window = tk.Toplevel()
    window.title("Phân công giáo viên")
    window.geometry("650x420")

    tk.Label(window, text="PHÂN CÔNG GIÁO VIÊN", font=("Arial", 16, "bold")).pack(pady=12)

    columns = ("Lớp", "Môn học", "Giáo viên")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

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
    window = tk.Toplevel()
    window.title("Báo cáo tổng hợp")
    window.geometry("700x420")
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

    columns = ("Tiêu chí", "Giá trị")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=8)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=320)
    tree.pack(pady=10, padx=20, fill="x")

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
    detail_win = tk.Toplevel()
    detail_win.title(f"Danh sách học sinh - Lớp {class_name}")
    detail_win.geometry("820x460")

    tk.Label(detail_win, text=f"DANH SÁCH HỌC SINH LỚP {class_name}", font=("Arial", 14, "bold")).pack(pady=10)

    columns = ("Họ và tên", "Ngày sinh", "Mã học sinh", "Giới tính", "Trạng thái")
    detail_tree = ttk.Treeview(detail_win, columns=columns, show="headings", height=14)
    widths = {"Họ và tên": 200, "Ngày sinh": 110, "Mã học sinh": 110, "Giới tính": 80, "Trạng thái": 130}
    for col in columns:
        detail_tree.heading(col, text=col)
        detail_tree.column(col, width=widths[col], anchor="center")
    detail_tree.pack(pady=10, padx=20, fill="both", expand=True)

    sql = """
    SELECT u.full_name,
           DATE_FORMAT(s.date_of_birth, '%d/%m/%Y') AS dob,
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
    students = execute_query(sql, (class_id,), fetch=True)

    if students:
        for row in students:
            detail_tree.insert("", tk.END, values=row)
    else:
        detail_tree.insert("", tk.END, values=("Lớp chưa có học sinh", "", "", "", ""))

    tk.Button(detail_win, text="Đóng", width=12, command=detail_win.destroy).pack(pady=10)


def open_teacher_class_list():
    window = tk.Toplevel()
    window.title("Danh sách lớp")
    window.geometry("650x420")

    tk.Label(window, text="DANH SÁCH LỚP", font=("Arial", 16, "bold")).pack(pady=12)

    columns = ("Mã lớp", "Tên lớp", "Số HS")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=180)
    tree.pack(pady=10, padx=20, fill="x")

    # Lấy danh sách lớp từ database
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

def open_teacher_attendance():
    window = tk.Toplevel()
    window.title("Điểm danh")
    window.geometry("700x450")

    tk.Label(window, text="ĐIỂM DANH HỌC SINH", font=("Arial", 16, "bold")).pack(pady=12)

    # Lấy danh sách học sinh từ database (mặc định lấy lớp đầu tiên)
    query = """
    SELECT s.student_id, u.full_name, c.class_id
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    JOIN classes c ON s.class_id = c.class_id
    LIMIT 10
    """
    students_data = execute_query(query, fetch=True)

    status_vars = []
    form_frame = tk.Frame(window)
    form_frame.pack(padx=20, pady=10, fill="x")

    if students_data:
        for index, (student_id, name, class_id) in enumerate(students_data):
            tk.Label(form_frame, text=name, anchor="w", width=25).grid(row=index, column=0, sticky="w", pady=4)
            status_var = tk.StringVar(value="Có mặt")
            status_vars.append((student_id, class_id, status_var))
            ttk.Combobox(form_frame, textvariable=status_var, values=["Có mặt", "Vắng mặt", "Muộn", "Có phép"], state="readonly", width=18).grid(row=index, column=1, padx=10)

    def save_teacher_attendance():
        for student_id, class_id, status_var in status_vars:
            status = status_var.get()
            query = """
            INSERT INTO attendance (student_id, class_id, attendance_date, status, recorded_by)
            VALUES (%s, %s, CURDATE(), %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            execute_query(query, (student_id, class_id, status, current_user["user_id"]))

        messagebox.showinfo("Thông báo", "Điểm danh của giáo viên đã được lưu!", parent=window)

    tk.Button(window, text="Lưu điểm danh", bg="lightgreen", font=("Arial", 12, "bold"), command=save_teacher_attendance).pack(pady=12)

def open_teacher_export_report():
    window = tk.Toplevel()
    window.title("Xuất báo cáo")
    window.geometry("520x280")
    tk.Label(window, text="XUẤT BÁO CÁO", font=("Arial", 16, "bold")).pack(pady=12)

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
    window = tk.Toplevel()
    window.title("Teacher Dashboard")
    window.geometry("900x600")

    tk.Label(window, text="GIÁO VIÊN - ĐIỂM DANH HỌC SINH", font=("Arial", 18, "bold")).pack(pady=10)

    menu_frame = tk.Frame(window)
    menu_frame.pack(pady=10)

    tk.Button(menu_frame, text="Danh sách lớp", width=20, command=open_teacher_class_list).grid(row=0, column=0, padx=5)
    tk.Button(menu_frame, text="Điểm danh", width=20, command=open_teacher_attendance).grid(row=0, column=1, padx=5)
    tk.Button(menu_frame, text="Xuất báo cáo", width=20, command=open_teacher_export_report).grid(row=0, column=2, padx=5)

    columns = ("Mã HS", "Họ tên", "Trạng thái")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=12)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)

    tree.pack(pady=20)

    # Lấy danh sách học sinh từ database
    query = """
    SELECT s.student_code, u.full_name, COALESCE(a.status, 'Chưa điểm danh')
    FROM students s
    JOIN users u ON s.user_id = u.user_id
    LEFT JOIN attendance a ON s.student_id = a.student_id AND DATE(a.attendance_date) = CURDATE()
    LIMIT 20
    """
    students = execute_query(query, fetch=True)

    if students:
        for s in students:
            tree.insert("", tk.END, values=s)

    tk.Button(window, text="Đăng xuất", width=20, bg="#f8d7da", command=lambda: common_logout(window)).pack(pady=10)

    window.protocol("WM_DELETE_WINDOW", window.destroy)

# ===================== STUDENT =====================

def open_self_attendance():
    window = tk.Toplevel()
    window.title("Tự điểm danh")
    window.geometry("520x320")

    tk.Label(window, text="TỰ ĐIỂM DANH", font=("Arial", 16, "bold")).pack(pady=12)

    # Lấy thông tin học sinh
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
        tk.Label(window, text=f"Học sinh: {full_name}").pack(anchor="w", padx=20)
        tk.Label(window, text=f"Lớp: {class_name}").pack(anchor="w", padx=20, pady=(0, 15))

        tk.Label(window, text="Trạng thái điểm danh:").pack(anchor="w", padx=20)
        status_var = tk.StringVar(value="Có mặt")
        ttk.Combobox(window, textvariable=status_var, values=["Có mặt", "Vắng mặt", "Muộn", "Có phép"], state="readonly", width=30).pack(padx=20, pady=10)

        def save_self_attendance():
            status = status_var.get()
            query = """
            INSERT INTO attendance (student_id, class_id, attendance_date, status, recorded_by)
            VALUES (%s, %s, CURDATE(), %s, %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status)
            """
            result = execute_query(query, (student_id, class_id, status, current_user["user_id"]))

            if result:
                messagebox.showinfo("Thông báo", f"Bạn đã điểm danh: {status}", parent=window)
                window.destroy()
            else:
                messagebox.showerror("Lỗi", "Điểm danh thất bại!", parent=window)

        tk.Button(window, text="Gửi điểm danh", width=18, bg="lightgreen", font=("Arial", 12, "bold"), command=save_self_attendance).pack(pady=14)

def open_student_dashboard():
    window = tk.Toplevel()
    window.title("Student Dashboard")
    window.geometry("700x520")

    tk.Label(window, text="THÔNG TIN ĐIỂM DANH", font=("Arial", 18, "bold")).pack(pady=15)

    info_frame = tk.Frame(window)
    info_frame.pack(pady=10)

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

    columns = ("Ngày", "Trạng thái")
    tree = ttk.Treeview(window, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=250)

    tree.pack(pady=20)

    # Lấy lịch sử điểm danh từ database
    query = """
    SELECT a.attendance_date, a.status
    FROM attendance a
    JOIN students s ON a.student_id = s.student_id
    WHERE s.user_id = %s
    ORDER BY a.attendance_date DESC
    LIMIT 20
    """
    history = execute_query(query, (current_user["user_id"],), fetch=True)

    if history:
        for item in history:
            tree.insert("", tk.END, values=item)

    tk.Button(window, text="Tự điểm danh", width=20, command=open_self_attendance).pack(pady=10)

    tk.Button(window, text="Đăng xuất", width=20, bg="#f8d7da", command=lambda: common_logout(window)).pack(pady=5)

    window.protocol("WM_DELETE_WINDOW", window.destroy)

# ===================== CỬA SỔ ĐĂNG NHẬP =====================

login_window = tk.Tk()
login_window.title("Hệ thống điểm danh học sinh")
login_window.geometry("450x400")

tk.Label(login_window, text="HỆ THỐNG ĐIỂM DANH HỌC SINH", font=("Arial", 16, "bold")).pack(pady=20)

tk.Label(login_window, text="Tên đăng nhập").pack()
entry_username = tk.Entry(login_window, width=30)
entry_username.pack(pady=5)

tk.Label(login_window, text="Mật khẩu").pack()
entry_password = tk.Entry(login_window, width=30, show="*")
entry_password.pack(pady=5)

tk.Label(login_window, text="Vai trò").pack(pady=(10, 0))
role_var = tk.StringVar()
ttk.Combobox(
    login_window,
    textvariable=role_var,
    values=["Quản trị viên", "Giáo viên", "Học sinh"],
    state="readonly",
    width=27
).pack()

tk.Button(login_window, text="Đăng nhập", width=20, bg="lightblue", font=("Arial", 11), command=login).pack(pady=12)

login_window.mainloop()
