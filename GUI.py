import tkinter as tk
from tkinter import ttk, messagebox

# ===================== ĐĂNG KÝ =====================

def open_register():
    reg_window = tk.Toplevel(login_window)
    reg_window.title("Đăng ký tài khoản")
    reg_window.geometry("420x500")
    reg_window.grab_set()

    tk.Label(reg_window, text="ĐĂNG KÝ TÀI KHOẢN", font=("Arial", 15, "bold")).pack(pady=15)

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

    lbl_error = tk.Label(reg_window, text="", fg="red", font=("Arial", 10), wraplength=340, justify="left")
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
    tk.Button(btn_frame, text="Đăng ký", width=16, bg="lightgreen", font=("Arial", 11, "bold"), command=do_register).grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Huỷ", width=10, font=("Arial", 11), command=reg_window.destroy).grid(row=0, column=1, padx=6)

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

    login_window.withdraw()

    if role == "Quản trị viên":
        open_admin_dashboard()
    elif role == "Giáo viên":
        open_teacher_dashboard()
    elif role == "Học sinh":
        open_student_dashboard()

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

    accounts = [
        ("admin", "Nguyễn Văn AD", "Quản trị viên"),
        ("gv01", "Trần Thị B", "Giáo viên"),
        ("hs01", "Lê Văn C", "Học sinh"),
    ]
    for account in accounts:
        tree.insert("", tk.END, values=account)

    def delete_account():
        selected_items = tree.selection()
        if not selected_items:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tài khoản để xóa!")
            return


        confirm = messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa tài khoản này?")
        if confirm:
            for item in selected_items:
                tree.delete(item)

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

        tk.Label(add_win, text="Vai trò:").pack(pady=(10, 2))

        combo_role = ttk.Combobox(add_win, values=["Quản trị viên", "Giáo viên", "Học sinh"], state="readonly",
                                  width=27)
        combo_role.pack()
        combo_role.current(1)

        def save_new_account():
            user = entry_user.get().strip()
            name = entry_name.get().strip()
            role = combo_role.get()


            if not user or not name:
                messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ Tên đăng nhập và Họ tên!")
                return


            tree.insert(parent="", index=tk.END, values=(user, name, role))
            messagebox.showinfo("Thành công", "Đã thêm tài khoản thành công!")
            add_win.destroy()

        tk.Button(add_win, text="Lưu thông tin", command=save_new_account, width=15, bg="#d4edda").pack(pady=20)

    action_frame = tk.Frame(window)
    action_frame.pack(pady=10)
    tk.Button(action_frame, text="Thêm tài khoản", width=15, command=add_account).pack(side=tk.LEFT, padx=10)
    tk.Button(action_frame, text="Xóa tài khoản", width=15, command=delete_account).pack(side=tk.LEFT, padx=10)


def open_student_management():
    window = tk.Toplevel()
    window.title("Quản lý học sinh")
    window.geometry("650x500")

    tk.Label(window, text="QUẢN LÝ HỌC SINH", font=("Arial", 16, "bold")).pack(pady=12)

    students = [
        ("HS001", "Nguyễn Văn A", "12A1"),
        ("HS002", "Trần Văn B", "12A2"),
        ("HS003", "Lê Thị C", "11B1"),
    ]

    search_frame = tk.Frame(window)
    search_frame.pack(pady=5, padx=20, fill="x")

    tk.Label(search_frame, text="Nhập từ khóa:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

    entry_keyword = tk.Entry(search_frame, width=22, font=("Arial", 10))
    entry_keyword.pack(side=tk.LEFT, padx=5)

    def search_student():
        keyword = entry_keyword.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        for student in students:
            if keyword in student[0].lower() or keyword in student[1].lower():
                tree.insert(parent="", index=tk.END, values=student)

    def filter_class():
        keyword = entry_keyword.get().strip().lower()
        for item in tree.get_children():
            tree.delete(item)
        for student in students:
            if keyword in student[2].lower():
                tree.insert(parent="", index=tk.END, values=student)

    def reset_table():
        entry_keyword.delete(0, tk.END)
        for item in tree.get_children():
            tree.delete(item)
        for student in students:
            tree.insert(parent="", index=tk.END, values=student)

    tk.Button(search_frame, text="Tìm kiếm", command=search_student, width=10).pack(side=tk.LEFT, padx=4)
    tk.Button(search_frame, text="Lọc theo Lớp", command=filter_class, width=12).pack(side=tk.LEFT, padx=4)
    tk.Button(search_frame, text="Đặt lại", command=reset_table, width=10, bg="#f8d7da").pack(side=tk.LEFT, padx=4)

    columns = ("Mã HS", "Họ và tên", "Lớp")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

    for student in students:
        tree.insert(parent="", index=tk.END, values=student)

def open_class_management():
    window = tk.Toplevel()
    window.title("Quản lý lớp học")
    window.geometry("650x420")

    tk.Label(window, text="QUẢN LÝ LỚP HỌC", font=("Arial", 16, "bold")).pack(pady=12)

    columns = ("Mã lớp", "Tên lớp", "GVCN")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=10)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=200)
    tree.pack(pady=10, padx=20, fill="x")

    classes = [
        ("12A1", "12A1", "Nguyễn Văn A"),
        ("12A2", "12A2", "Trần Thị B"),
        ("11B1", "11B1", "Phạm Văn C"),
    ]
    for classroom in classes:
        tree.insert("", tk.END, values=classroom)

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

    assignments = [
        ("12A1", "Toán", "Nguyễn Văn A"),
        ("12A2", "Văn", "Trần Thị B"),
        ("11B1", "Anh", "Phạm Văn C"),
    ]
    for item in assignments:
        tree.insert("", tk.END, values=item)

def open_admin_report():
    window = tk.Toplevel()
    window.title("Báo cáo tổng hợp")
    window.geometry("700x420")

    tk.Label(window, text="BÁO CÁO TỔNG HỢP", font=("Arial", 16, "bold")).pack(pady=12)

    summary_frame = tk.Frame(window)
    summary_frame.pack(pady=10, padx=20, fill="x")
    tk.Label(summary_frame, text="Tổng số học sinh: 120", anchor="w").pack(fill="x")
    tk.Label(summary_frame, text="Tổng số giáo viên: 18", anchor="w").pack(fill="x")
    tk.Label(summary_frame, text="Tổng số lớp: 12", anchor="w").pack(fill="x")

    columns = ("Tiêu chí", "Giá trị")
    tree = ttk.Treeview(window, columns=columns, show="headings", height=8)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=320)
    tree.pack(pady=10, padx=20, fill="x")

    report_items = [
        ("Tỷ lệ chuyên cần", "95%"),
        ("Số buổi vắng", "22"),
        ("Số lớp đã điểm danh", "12"),
    ]
    for item in report_items:
        tree.insert("", tk.END, values=item)

def open_admin_dashboard():
    window = tk.Toplevel()
    window.title("Admin Dashboard")
    window.geometry("700x520")
    tk.Label(window, text="ADMIN DASHBOARD", font=("Arial", 18, "bold")).pack(pady=20)

    frame = tk.Frame(window)
    frame.pack()

    tk.Button(frame, text="Quản lý tài khoản", width=30, height=2, command=open_account_management).pack(pady=5)
    tk.Button(frame, text="Quản lý học sinh", width=30, height=2, command=open_student_management).pack(pady=5)
    tk.Button(frame, text="Quản lý lớp học", width=30, height=2, command=open_class_management).pack(pady=5)
    tk.Button(frame, text="Phân công giáo viên", width=30, height=2, command=open_teacher_assignment).pack(pady=5)
    tk.Button(frame, text="Xem báo cáo tổng hợp", width=30, height=2, command=open_admin_report).pack(pady=5)

    # Đồng bộ đóng ứng dụng khi tắt Dashboard
    window.protocol("WM_DELETE_WINDOW", login_window.quit)

# ===================== TEACHER =====================

def save_attendance():
    messagebox.showinfo("Thông báo", "Đã lưu điểm danh thành công!")

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

    classes = [
        ("12A1", "12A1", "35"),
        ("12A2", "12A2", "33"),
        ("11B1", "11B1", "32"),
    ]
    for classroom in classes:
        tree.insert("", tk.END, values=classroom)

def open_teacher_attendance():
    window = tk.Toplevel()
    window.title("Điểm danh")
    window.geometry("700x450")

    tk.Label(window, text="ĐIỂM DANH HỌC SINH", font=("Arial", 16, "bold")).pack(pady=12)

    student_names = ["Nguyễn Văn A", "Trần Văn B", "Lê Văn C", "Phạm Văn D"]
    status_vars = []
    form_frame = tk.Frame(window)
    form_frame.pack(padx=20, pady=10, fill="x")

    for index, name in enumerate(student_names):
        tk.Label(form_frame, text=name, anchor="w", width=25).grid(row=index, column=0, sticky="w", pady=4)
        status_var = tk.StringVar(value="Có mặt")
        status_vars.append(status_var)
        ttk.Combobox(form_frame, textvariable=status_var, values=["Có mặt", "Vắng", "Muộn"], state="readonly", width=18).grid(row=index, column=1, padx=10)

    def save_teacher_attendance():
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
        messagebox.showinfo("Thông báo", f"Đã xuất {choice} thành công!", parent=window)

    tk.Button(window, text="Xuất báo cáo", width=18, bg="lightblue", font=("Arial", 12, "bold"), command=export_report).pack(pady=14)

def open_teacher_dashboard():
    window = tk.Toplevel() # Đổi sang Toplevel()
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

    students = [
        ("HS001", "Nguyễn Văn A", "Có mặt"),
        ("HS002", "Trần Văn B", "Vắng"),
        ("HS003", "Lê Văn C", "Có mặt"),
        ("HS004", "Phạm Văn D", "Có mặt"),
    ]

    for s in students:
        tree.insert("", tk.END, values=s)

    tk.Button(window, text="Lưu điểm danh", bg="lightgreen", font=("Arial", 12, "bold"), command=save_attendance).pack(pady=10)

    window.protocol("WM_DELETE_WINDOW", login_window.quit)

# ===================== STUDENT =====================

def open_self_attendance():
    window = tk.Toplevel()
    window.title("Tự điểm danh")
    window.geometry("520x320")

    tk.Label(window, text="TỰ ĐIỂM DANH", font=("Arial", 16, "bold")).pack(pady=12)

    tk.Label(window, text="Học sinh: Nguyễn Văn A").pack(anchor="w", padx=20)
    tk.Label(window, text="Lớp: 12A1").pack(anchor="w", padx=20, pady=(0, 15))

    tk.Label(window, text="Trạng thái điểm danh:").pack(anchor="w", padx=20)
    status_var = tk.StringVar(value="Có mặt")
    ttk.Combobox(window, textvariable=status_var, values=["Có mặt", "Vắng", "Muộn"], state="readonly", width=30).pack(padx=20, pady=10)

    def save_self_attendance():messagebox.showinfo("Thông báo", f"Bạn đã điểm danh: {status_var.get()}", parent=window)

    tk.Button(window, text="Gửi điểm danh", width=18, bg="lightgreen", font=("Arial", 12, "bold"), command=save_self_attendance).pack(pady=14)

def open_student_dashboard():
    window = tk.Toplevel() # Đổi sang Toplevel()
    window.title("Student Dashboard")
    window.geometry("700x520")

    tk.Label(window, text="THÔNG TIN ĐIỂM DANH", font=("Arial", 18, "bold")).pack(pady=15)

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

    tk.Button(window, text="Tự điểm danh", width=20, command=open_self_attendance).pack(pady=10)

    window.protocol("WM_DELETE_WINDOW", login_window.quit)

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
tk.Button(login_window, text="Đăng ký tài khoản", width=20, font=("Arial", 11), command=open_register).pack(pady=(0, 15))

login_window.mainloop()