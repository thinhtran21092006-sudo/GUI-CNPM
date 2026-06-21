import tkinter as tk
from tkinter import ttk, messagebox

# ===================== ĐĂNG KÝ =====================

def open_register():
    reg_window = tk.Toplevel(login_window)
    reg_window.title("Đăng ký tài khoản")
    reg_window.geometry("420x500")
    reg_window.grab_set()

    tk.Label(reg_window, text="ĐĂNG KÝ TÀI KHOẢN",
             font=("Arial", 15, "bold")).pack(pady=15)

    form_frame = tk.Frame(reg_window)
    form_frame.pack(padx=40, fill="x")

    tk.Label(form_frame, text="Họ và tên", anchor="w").pack(fill="x", pady=(8, 2))
    entry_name = tk.Entry(form_frame, width=35)
    entry_name.pack(fill="x")

    tk.Label(form_frame, text="Tên đăng nhập", anchor="w").pack(fill="x", pady=(8, 2))
    entry_user = tk.Entry(form_frame, width=35)
    entry_user.pack(fill="x")

    tk.Label(form_frame, text="Mật khẩu", anchor="w").pack(fill="x", pady=(8, 2))
    entry_pass = tk.Entry(form_frame, width=35, show="*")
    entry_pass.pack(fill="x")

    tk.Label(form_frame, text="Xác nhận mật khẩu", anchor="w").pack(fill="x", pady=(8, 2))
    entry_confirm = tk.Entry(form_frame, width=35, show="*")
    entry_confirm.pack(fill="x")

    tk.Label(form_frame, text="Vai trò", anchor="w").pack(fill="x", pady=(8, 2))
    reg_role_var = tk.StringVar()
    ttk.Combobox(
        form_frame,
        textvariable=reg_role_var,
        values=["Giáo viên", "Học sinh"],
        state="readonly",
        width=33
    ).pack(fill="x")

    lbl_error = tk.Label(reg_window, text="", fg="red",
                         font=("Arial", 10), wraplength=340, justify="left")
    lbl_error.pack(pady=(10, 0), padx=40)

    def do_register():
        name    = entry_name.get().strip()
        user    = entry_user.get().strip()
        pwd     = entry_pass.get().strip()
        confirm = entry_confirm.get().strip()
        role    = reg_role_var.get()

        errors = []
        if not name:
            errors.append("• Vui lòng nhập họ và tên")
        if not user:
            errors.append("• Vui lòng nhập tên đăng nhập")
        if not pwd:
            errors.append("• Vui lòng nhập mật khẩu")
        elif len(pwd) < 6:
            errors.append("• Mật khẩu phải có ít nhất 6 ký tự")
        if not confirm:
            errors.append("• Vui lòng xác nhận mật khẩu")
        elif pwd and confirm and pwd != confirm:
            errors.append("• Mật khẩu xác nhận không khớp")
        if not role:
            errors.append("• Vui lòng chọn vai trò")

        if errors:
            lbl_error.config(text="\n".join(errors))
            return

        lbl_error.config(text="")
        messagebox.showinfo(
            "Thành công",
            f"Đăng ký thành công!\n\nHọ tên:    {name}\nTài khoản: {user}\nVai trò:   {role}",
            parent=reg_window
        )
        reg_window.destroy()

    btn_frame = tk.Frame(reg_window)
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="Đăng ký", width=16,
              bg="lightgreen", font=("Arial", 11, "bold"),
              command=do_register).grid(row=0, column=0, padx=6)

    tk.Button(btn_frame, text="Huỷ", width=10,
              font=("Arial", 11),
              command=reg_window.destroy).grid(row=0, column=1, padx=6)


# ===================== ĐĂNG NHẬP =====================

def login():
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

    login_window.destroy()

    if role == "Quản trị viên":
        open_admin_dashboard()
    elif role == "Giáo viên":
        open_teacher_dashboard()
    elif role == "Học sinh":
        open_student_dashboard()


# ===================== ADMIN =====================

def open_admin_dashboard():
    window = tk.Tk()
    window.title("Admin Dashboard")
    window.geometry("700x500")

    tk.Label(window, text="ADMIN DASHBOARD",
             font=("Arial", 18, "bold")).pack(pady=20)

    frame = tk.Frame(window)
    frame.pack()

    buttons = [
        "Quản lý tài khoản",
        "Quản lý học sinh",
        "Quản lý lớp học",
        "Phân công giáo viên",
        "Xem báo cáo tổng hợp"
    ]

    for text in buttons:
        tk.Button(frame, text=text, width=30, height=2).pack(pady=5)

    window.mainloop()


# ===================== TEACHER =====================

def save_attendance():
    messagebox.showinfo("Thông báo", "Đã lưu điểm danh thành công!")

def open_teacher_dashboard():
    window = tk.Tk()
    window.title("Teacher Dashboard")
    window.geometry("900x600")

    tk.Label(window, text="GIÁO VIÊN - ĐIỂM DANH HỌC SINH",
             font=("Arial", 18, "bold")).pack(pady=10)

    menu_frame = tk.Frame(window)
    menu_frame.pack(pady=10)

    tk.Button(menu_frame, text="Danh sách lớp", width=20).grid(row=0, column=0, padx=5)
    tk.Button(menu_frame, text="Điểm danh", width=20).grid(row=0, column=1, padx=5)
    tk.Button(menu_frame, text="Thống kê", width=20).grid(row=0, column=2, padx=5)
    tk.Button(menu_frame, text="Xuất báo cáo", width=20).grid(row=0, column=3, padx=5)

    columns = ("Mã HS", "Họ tên", "Trạng thái")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=12)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)

    tree.pack(pady=20)

    students = [
        ("HS001", "Nguyễn Văn A", "Có mặt"),
        ("HS002", "Trần Văn B", "Vắng"),
        ("HS003", "Lê Văn C", "Có mặt"),
    ("HS004", "Phạm Văn D", "Có mặt"),
    ]

    for s in students:
        tree.insert("", tk.END, values=s)

    tk.Button(window, text="Lưu điểm danh",
              bg="lightgreen", font=("Arial", 12, "bold"),
              command=save_attendance).pack(pady=10)

    window.mainloop()


# ===================== STUDENT =====================

def open_student_dashboard():
    window = tk.Tk()
    window.title("Student Dashboard")
    window.geometry("700x500")

    tk.Label(window, text="THÔNG TIN ĐIỂM DANH",
             font=("Arial", 18, "bold")).pack(pady=15)

    info_frame = tk.Frame(window)
    info_frame.pack(pady=10)

    tk.Label(info_frame, text="Mã HS: HS001").pack(anchor="w")
    tk.Label(info_frame, text="Họ tên: Nguyễn Văn A").pack(anchor="w")
    tk.Label(info_frame, text="Lớp: 12A1").pack(anchor="w")

    columns = ("Ngày", "Trạng thái")
    tree = ttk.Treeview(window, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=250)

    tree.pack(pady=20)

    history = [
        ("01/06/2026", "Có mặt"),
        ("02/06/2026", "Có mặt"),
        ("03/06/2026", "Vắng"),
        ("04/06/2026", "Có mặt"),
    ]

    for item in history:
        tree.insert("", tk.END, values=item)

    tk.Button(window, text="Tự điểm danh", width=20).pack(pady=10)

    window.mainloop()


# ===================== CỬA SỔ ĐĂNG NHẬP =====================

login_window = tk.Tk()
login_window.title("Hệ thống điểm danh học sinh")
login_window.geometry("450x400")

tk.Label(login_window, text="HỆ THỐNG ĐIỂM DANH HỌC SINH",
         font=("Arial", 16, "bold")).pack(pady=20)

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

tk.Button(login_window, text="Đăng nhập", width=20,
          bg="lightblue", font=("Arial", 11),
          command=login).pack(pady=12)

tk.Button(login_window, text="Đăng ký tài khoản", width=20,
          font=("Arial", 11),
          command=open_register).pack(pady=(0, 15))

login_window.mainloop()