import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os, re

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

# ===================== HELPERS =====================

def validate_email(e): return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', e))
def validate_phone(p): return p.isdigit() and 9 <= len(p) <= 11

REQUIRED_TABLES = ["users","roles","students","classes","subjects","attendance","grades","teaching_assignments","grade_levels","self_attendance_configs"]
current_user = None

# ===================== DATABASE =====================

class DB:
    cfg = {
        "user": os.environ.get("DB_USER","root"), "password": os.environ.get("DB_PASSWORD","123456"),
        "host": os.environ.get("DB_HOST","localhost"), "port": int(os.environ.get("DB_PORT","3306")),
        "database": os.environ.get("DB_NAME","student_management"),
    }
    def __enter__(self):
        try: self.conn = mysql.connector.connect(**self.cfg)
        except Error as e: messagebox.showerror("Lỗi kết nối", str(e)); return None
        self.cur = self.conn.cursor(); return self
    def __exit__(self, et, e, tb):
        try:
            (self.conn.commit() if et is None else self.conn.rollback())
        finally:
            self.cur.close(); self.conn.close()
        return False
    def run(self, q, p=None, fetch=False):
        self.cur.execute(q, p) if p else self.cur.execute(q)
        return self.cur.fetchall() if fetch else self.cur.rowcount
    def many(self, q, ps): self.cur.executemany(q, ps); return self.cur.rowcount

def qry(q, p=None, fetch=False, many=False):
    with DB() as db:
        if db:
            try: return db.many(q,p) if many else db.run(q,p,fetch)
            except Error as e: messagebox.showerror("Lỗi DB", str(e))
    return None

def check_schema():
    dbname = os.environ.get("DB_NAME","student_management")
    with DB() as db:
        if not db: return False
        ph = ",".join(["%s"]*len(REQUIRED_TABLES))
        db.cur.execute(f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME IN ({ph})", (dbname,*REQUIRED_TABLES))
        missing = set(REQUIRED_TABLES) - {r[0] for r in db.cur.fetchall()}
    if missing:
        messagebox.showerror("Thiếu bảng", "Thiếu: "+", ".join(sorted(missing))+"\nChạy setup_database.py trước!")
        return False
    return True

# ===================== UI UTILITIES =====================

def win(title, geo, grab=False):
    w = tk.Toplevel(); w.title(title); w.geometry(geo)
    if grab: w.grab_set()
    return w

def lbl_entry(parent, text, show=None):
    tk.Label(parent, text=text).pack(pady=(5,0))
    e = tk.Entry(parent, width=30, show=show); e.pack(pady=5); return e

def treeview(parent, cols, widths):
    t = ttk.Treeview(parent, columns=cols, show="headings", height=10)
    for c in cols: t.heading(c, text=c); t.column(c, width=widths.get(c,150), anchor="center")
    t.pack(pady=10, padx=20, fill="x"); return t

def btn(parent, text, cmd, bg=None, w=15):
    return tk.Button(parent, text=text, command=cmd, width=w, bg=bg)

def btn_row(parent, items):
    f = tk.Frame(parent); f.pack(pady=10)
    for text, cmd, kw in items:
        tk.Button(f, text=text, command=cmd, width=15, **kw).pack(side=tk.LEFT, padx=5)
    return f

def logout(window):
    global current_user; current_user = None
    window.destroy(); login_window.deiconify()
    entry_username.delete(0, tk.END); entry_password.delete(0, tk.END); role_var.set("")

# ===================== LOGIN =====================

def login():
    global current_user
    username, password, role = entry_username.get().strip(), entry_password.get().strip(), role_var.get()
    errs = (["• Nhập tên đăng nhập!"] if not username else []) + \
           (["• Nhập mật khẩu!"] if not password else []) + \
           (["• Chọn vai trò!"] if not role else [])
    if errs: messagebox.showwarning("Thông báo", "\n".join(errs)); return
    role_map = {"Quản lý":3,"Giáo viên":1,"Học sinh":2}
    res = qry("SELECT user_id,full_name,password FROM users WHERE username=%s AND role_id=%s", (username, role_map[role]), fetch=True)
    ok = res and (res[0][2].decode() if isinstance(res[0][2],bytes) else str(res[0][2] or "")) == password
    if ok:
        current_user = {"user_id":res[0][0],"full_name":res[0][1],"role_id":role_map[role]}
        login_window.withdraw()
        {"Quản lý":open_admin_dashboard,"Giáo viên":open_teacher_dashboard,"Học sinh":open_student_dashboard}[role]()
    else:
        messagebox.showerror("Lỗi","Tên đăng nhập, mật khẩu hoặc vai trò không đúng!")

# ===================== ADMIN =====================

def open_account_management():
    w = win("Quản lý tài khoản","650x420")
    tk.Label(w,text="QUẢN LÝ TÀI KHOẢN",font=("Arial",16,"bold")).pack(pady=12)
    cols = ("Tên đăng nhập","Mật khẩu","Họ và tên","Vai trò")
    tree = treeview(w, cols, {"Tên đăng nhập":120,"Mật khẩu":200,"Họ và tên":150,"Vai trò":100})
    rows = qry("SELECT u.username,u.password,u.full_name,r.role_name FROM users u JOIN roles r ON u.role_id=r.role_id", fetch=True)
    if rows:
        for r in rows: tree.insert("",tk.END,values=r)

    def delete():
        for item in tree.selection():
            un = tree.item(item,'values')[0]
            res = qry("SELECT user_id FROM users WHERE username=%s",(un,),fetch=True)
            if res:
                uid = res[0][0]
                for q in ["DELETE FROM attendance WHERE student_id IN (SELECT student_id FROM students WHERE user_id=%s)",
                          "DELETE FROM grades WHERE student_id IN (SELECT student_id FROM students WHERE user_id=%s)",
                          "DELETE FROM students WHERE user_id=%s","DELETE FROM teaching_assignments WHERE teacher_id=%s",
                          "UPDATE classes SET homeroom_teacher_id=NULL WHERE homeroom_teacher_id=%s","DELETE FROM users WHERE user_id=%s"]:
                    qry(q,(uid,))
                tree.delete(item)

    def add():
        aw = win("Thêm tài khoản","380x320",True)
        tk.Label(aw,text="THÊM TÀI KHOẢN MỚI",font=("Arial",12,"bold")).pack(pady=10)
        e_fn=lbl_entry(aw,"Họ và tên:"); e_un=lbl_entry(aw,"Tên đăng nhập:"); e_pw=lbl_entry(aw,"Mật khẩu:",show="*")
        rc = ttk.Combobox(aw,values=["Quản lý","Giáo viên","Học sinh"],state="readonly",width=27); rc.pack(pady=5)
        def save():
            fn,un,pw,role = e_fn.get().strip(),e_un.get().strip(),e_pw.get().strip(),rc.get()
            if not all([fn,un,pw,role]): messagebox.showwarning("Thông báo","Điền đầy đủ!",parent=aw); return
            rm={"Giáo viên":1,"Học sinh":2,"Quản lý":3}
            try:
                qry("INSERT INTO users(full_name,username,password,role_id) VALUES(%s,%s,%s,%s)",(fn,un,pw,rm[role]))
                tree.insert("",tk.END,values=(un,pw,fn,role)); aw.destroy()
            except Exception as e: messagebox.showerror("Lỗi",str(e),parent=aw)
        tk.Button(aw,text="Thêm",width=15,bg="#d4edda",command=save).pack(pady=20)

    btn_row(w,[("Thêm tài khoản",add,{}),("Xóa tài khoản",delete,{"bg":"#f8d7da"})])

def open_teacher_management():
    w = win("Quản lý giáo viên","650x450")
    tk.Label(w,text="QUẢN LÝ GIÁO VIÊN",font=("Arial",16,"bold")).pack(pady=12)
    sf=tk.Frame(w); sf.pack(pady=5,padx=20,fill="x")
    tk.Label(sf,text="Từ khóa:").pack(side=tk.LEFT,padx=5)
    ek=tk.Entry(sf,width=22); ek.pack(side=tk.LEFT,padx=5)
    cols=("Tên đăng nhập","Họ và tên","Email","SĐT")
    tree=treeview(w,cols,{"Tên đăng nhập":120,"Họ và tên":150})

    def load(kw=""):
        for i in tree.get_children(): tree.delete(i)
        sql="SELECT u.username,u.full_name,COALESCE(u.email,'N/A'),COALESCE(u.phone,'N/A') FROM users u WHERE u.role_id=1"
        p=None
        if kw.strip(): sql+=" AND (u.full_name LIKE %s OR u.username LIKE %s)"; p=(f"%{kw}%",f"%{kw}%")
        rows=qry(sql,p,fetch=True)
        if rows:
            for r in rows: tree.insert("",tk.END,values=r)

    tk.Button(sf,text="Tìm",command=lambda:load(ek.get()),width=8).pack(side=tk.LEFT,padx=4)
    tk.Button(sf,text="Đặt lại",command=lambda:(ek.delete(0,tk.END),load()),width=8,bg="#f8d7da").pack(side=tk.LEFT,padx=4)
    ek.bind("<Return>",lambda e:load(ek.get())); load()

    def add():
        aw=win("Thêm giáo viên","380x520",True)
        tk.Label(aw,text="Thêm giáo viên mới",font=("Arial",12,"bold")).pack(pady=10)
        eu=lbl_entry(aw,"Tên đăng nhập:"); en=lbl_entry(aw,"Họ và tên:"); ep=lbl_entry(aw,"Mật khẩu:",show="*")
        ee=lbl_entry(aw,"Email:"); ephone=lbl_entry(aw,"Số điện thoại:")
        tk.Label(aw,text="Lớp phân công:").pack(pady=(10,2))
        cc=ttk.Combobox(aw,state="readonly",width=27); cc.pack()
        cr=qry("SELECT class_id,class_name FROM classes ORDER BY class_name",fetch=True) or []
        cc["values"]=[f"{c[0]} - {c[1]}" for c in cr]
        tk.Label(aw,text="Môn phân công:").pack(pady=(10,2))
        cs=ttk.Combobox(aw,state="readonly",width=27); cs.pack()
        sr=qry("SELECT subject_id,subject_name FROM subjects ORDER BY subject_name",fetch=True) or []
        cs["values"]=[f"{s[0]} - {s[1]}" for s in sr]

        def save():
            user,name,pwd,email,phone,ci,si = eu.get().strip(),en.get().strip(),ep.get().strip(),ee.get().strip(),ephone.get().strip(),cc.get(),cs.get()
            if not all([user,name,pwd,ci,si]): messagebox.showerror("Lỗi","Điền đầy đủ!",parent=aw); return
            if email and not validate_email(email): messagebox.showerror("Lỗi","Email không hợp lệ!",parent=aw); return
            if phone and not validate_phone(phone): messagebox.showerror("Lỗi","SĐT không hợp lệ!",parent=aw); return
            cid,sid=int(ci.split(" - ")[0]),int(si.split(" - ")[0]); sname=si.split(" - ",1)[1]
            try:
                with DB() as db:
                    if not db: return
                    db.run("INSERT INTO users(full_name,username,password,role_id,email,phone) VALUES(%s,%s,%s,%s,%s,%s)",(name,user,pwd,1,email,phone))
                    row=db.run("SELECT user_id FROM users WHERE username=%s",(user,),fetch=True)
                    if not row: raise Exception("Không thể tạo user.")
                    tid=row[0][0]; db.run("INSERT INTO teaching_assignments(teacher_id,class_id,subject_id) VALUES(%s,%s,%s)",(tid,cid,sid))
                    if sname=="Giáo viên chủ nhiệm": db.run("UPDATE classes SET homeroom_teacher_id=%s WHERE class_id=%s",(tid,cid))
                tree.insert("",tk.END,values=(user,name,email,phone)); aw.destroy()
            except Exception as e: messagebox.showerror("Lỗi",str(e),parent=aw)

        f=tk.Frame(aw); f.pack(pady=15)
        tk.Button(f,text="Thêm",command=save,width=12,bg="#d4edda").pack(side=tk.LEFT,padx=5)
        tk.Button(f,text="Hủy",command=aw.destroy,width=12).pack(side=tk.LEFT,padx=5)

    def delete():
        sel=tree.selection()
        if not sel: messagebox.showwarning("Cảnh báo","Chọn giáo viên!"); return
        if not messagebox.askyesno("Xác nhận","Xóa giáo viên này?"): return
        for item in sel:
            un=tree.item(item,'values')[0]
            res=qry("SELECT user_id FROM users WHERE username=%s",(un,),fetch=True)
            if not res: continue
            uid=res[0][0]
            qry("DELETE FROM teaching_assignments WHERE teacher_id=%s",(uid,))
            qry("UPDATE classes SET homeroom_teacher_id=NULL WHERE homeroom_teacher_id=%s",(uid,))
            qry("DELETE FROM users WHERE user_id=%s",(uid,))
            tree.delete(item)

    btn_row(w,[("Thêm giáo viên",add,{}),("Xóa giáo viên",delete,{"bg":"#f8d7da"})])

def open_student_management():
    w=win("Quản lý học sinh","650x500")
    tk.Label(w,text="QUẢN LÝ HỌC SINH",font=("Arial",16,"bold")).pack(pady=12)
    sf=tk.Frame(w); sf.pack(pady=5,padx=20,fill="x")
    tk.Label(sf,text="Từ khóa:").pack(side=tk.LEFT,padx=5)
    ek=tk.Entry(sf,width=22); ek.pack(side=tk.LEFT,padx=5)
    cols=("Mã HS","Họ và tên","Lớp")
    tree=treeview(w,cols,{"Mã HS":150})

    SQL="SELECT s.student_id,s.student_code,u.full_name,c.class_name FROM students s JOIN users u ON s.user_id=u.user_id JOIN classes c ON s.class_id=c.class_id"
    students=qry(SQL,fetch=True) or []

    def populate(data):
        for i in tree.get_children(): tree.delete(i)
        for r in (data or []): tree.insert("",tk.END,values=r[1:])

    def search(kw=""):
        kw=kw.strip().lower()
        populate([s for s in students if kw in s[2].lower() or kw in s[1].lower()])

    def flt_class(kw=""):
        kw=kw.strip().lower()
        populate([s for s in students if kw in s[3].lower()])

    tk.Button(sf,text="Tìm",command=lambda:search(ek.get()),width=8).pack(side=tk.LEFT,padx=4)
    tk.Button(sf,text="Lọc lớp",command=lambda:flt_class(ek.get()),width=8).pack(side=tk.LEFT,padx=4)
    tk.Button(sf,text="Đặt lại",command=lambda:(ek.delete(0,tk.END),populate(students)),width=8,bg="#f8d7da").pack(side=tk.LEFT,padx=4)
    ek.bind("<Return>",lambda e:search(ek.get())); populate(students)

    def add():
        aw=win("Thêm học sinh","380x550",True)
        tk.Label(aw,text="Thêm học sinh mới",font=("Arial",12,"bold")).pack(pady=10)
        ec=lbl_entry(aw,"Mã học sinh:"); en=lbl_entry(aw,"Họ và tên:"); eu=lbl_entry(aw,"Tên đăng nhập:")
        epw=lbl_entry(aw,"Mật khẩu:",show="*"); ed=lbl_entry(aw,"Ngày sinh (YYYY-MM-DD):")
        tk.Label(aw,text="Giới tính:").pack(pady=(5,2))
        cg=ttk.Combobox(aw,values=["Nam","Nữ","Khác"],state="readonly",width=27); cg.pack()
        tk.Label(aw,text="Lớp:").pack(pady=(5,2))
        ccl=ttk.Combobox(aw,state="readonly",width=27); ccl.pack()
        cr=qry("SELECT class_id,class_name FROM classes",fetch=True) or []
        ccl["values"]=[f"{c[0]} - {c[1]}" for c in cr]
        ephone=lbl_entry(aw,"SĐT phụ huynh:")

        def save():
            code,name,user,pwd,dob,gender,ci,phone = ec.get().strip(),en.get().strip(),eu.get().strip(),epw.get().strip(),ed.get().strip(),cg.get(),ccl.get(),ephone.get().strip()
            if not all([code,name,user,pwd,dob,gender,ci,phone]): messagebox.showerror("Lỗi","Điền đầy đủ!",parent=aw); return
            if not validate_phone(phone): messagebox.showerror("Lỗi","SĐT không hợp lệ!",parent=aw); return
            try: datetime.strptime(dob,'%Y-%m-%d')
            except: messagebox.showerror("Lỗi","Ngày sinh không hợp lệ!",parent=aw); return
            if qry("SELECT 1 FROM students WHERE student_code=%s",(code,),fetch=True): messagebox.showerror("Lỗi",f"Mã HS '{code}' đã tồn tại!",parent=aw); return
            if qry("SELECT 1 FROM users WHERE username=%s",(user,),fetch=True): messagebox.showerror("Lỗi",f"Tên '{user}' đã tồn tại!",parent=aw); return
            cid=int(ci.split(" - ")[0])
            try:
                with DB() as db:
                    if not db: return
                    db.run("INSERT INTO users(full_name,username,password,role_id) VALUES(%s,%s,%s,%s)",(name,user,pwd,2))
                    uid=db.run("SELECT user_id FROM users WHERE username=%s",(user,),fetch=True)[0][0]
                    db.run("INSERT INTO students(user_id,student_code,date_of_birth,gender,parent_phone,class_id,enrollment_date,status) VALUES(%s,%s,%s,%s,%s,%s,CURDATE(),'Đang học')",(uid,code,dob,gender,phone,cid))
                messagebox.showinfo("Thành công","Đã thêm học sinh!",parent=aw)
                aw.destroy(); w.destroy(); open_student_management()
            except Exception as e: messagebox.showerror("Lỗi",str(e),parent=aw)

        f=tk.Frame(aw); f.pack(pady=15)
        tk.Button(f,text="Thêm",command=save,width=12,bg="#d4edda").pack(side=tk.LEFT,padx=5)
        tk.Button(f,text="Hủy",command=aw.destroy,width=12).pack(side=tk.LEFT,padx=5)

    def delete():
        sel=tree.selection()
        if not sel: messagebox.showwarning("Cảnh báo","Chọn học sinh!",parent=w); return
        if not messagebox.askyesno("Xác nhận","Xóa học sinh và toàn bộ điểm danh liên quan?",parent=w): return
        for item in sel:
            code=tree.item(item,'values')[0]
            info=qry("SELECT s.student_id,s.user_id FROM students s WHERE s.student_code=%s",(code,),fetch=True)
            if not info: continue
            sid,uid=info[0]
            qry("DELETE FROM attendance WHERE student_id=%s",(sid,))
            qry("DELETE FROM grades WHERE student_id=%s",(sid,))
            qry("DELETE FROM students WHERE student_id=%s",(sid,))
            qry("DELETE FROM users WHERE user_id=%s",(uid,))
            tree.delete(item)
        messagebox.showinfo("Thành công","Đã xóa!",parent=w)

    btn_row(w,[("Thêm học sinh",add,{}),("Xóa học sinh",delete,{"bg":"#f8d7da"})])

def open_class_management():
    w=win("Quản lý lớp học","650x420")
    tk.Label(w,text="QUẢN LÝ LỚP HỌC",font=("Arial",16,"bold")).pack(pady=12)
    tk.Label(w,text="(Nhấn đúp để xem danh sách học sinh)",font=("Arial",9,"italic"),fg="gray").pack()
    tree=treeview(w,("Mã lớp","Tên lớp","GVCN"),{})
    rows=qry("SELECT c.class_id,c.class_name,COALESCE(u.full_name,'Chưa gán') FROM classes c LEFT JOIN users u ON c.homeroom_teacher_id=u.user_id",fetch=True)
    if rows:
        for r in rows: tree.insert("",tk.END,values=r)

    def view_students(e=None):
        sel=tree.selection()
        if not sel: return
        v=tree.item(sel[0],'values'); open_class_student_list(v[0],v[1])

    tree.bind("<Double-1>",view_students)
    tk.Button(w,text="Xem danh sách học sinh",command=view_students,bg="#d4edda").pack(pady=8)

    def add():
        aw=win("Thêm lớp","350x320",True)
        tk.Label(aw,text="Thêm lớp học mới",font=("Arial",12,"bold")).pack(pady=10)
        en=lbl_entry(aw,"Tên lớp:")
        tk.Label(aw,text="Khối lớp:").pack(pady=(5,2))
        cg=ttk.Combobox(aw,state="readonly",width=27); cg.pack()
        gr=qry("SELECT grade_id,grade_name FROM grade_levels",fetch=True) or []
        cg["values"]=[f"{g[0]} - {g[1]}" for g in gr]
        ey=lbl_entry(aw,"Năm học (VD: 2026-2027):"); em=lbl_entry(aw,"Sức chứa tối đa:")

        def save():
            name,gi,year,mx=en.get().strip(),cg.get(),ey.get().strip(),em.get().strip()
            if not all([name,gi,year,mx]): messagebox.showerror("Lỗi","Điền đầy đủ!",parent=aw); return
            try:
                qry("INSERT INTO classes(class_name,grade_id,max_students,school_year) VALUES(%s,%s,%s,%s)",(name,int(gi.split(" - ")[0]),int(mx),year))
                aw.destroy(); w.destroy(); open_class_management()
            except ValueError: messagebox.showerror("Lỗi","Sức chứa phải là số!",parent=aw)

        f=tk.Frame(aw); f.pack(pady=15)
        tk.Button(f,text="Thêm",command=save,width=12,bg="#d4edda").pack(side=tk.LEFT,padx=5)
        tk.Button(f,text="Hủy",command=aw.destroy,width=12).pack(side=tk.LEFT,padx=5)

    def delete():
        sel=tree.selection()
        if not sel: messagebox.showwarning("Cảnh báo","Chọn lớp!",parent=w); return
        if not messagebox.askyesno("Xác nhận xóa","CẢNH BÁO: Xóa lớp sẽ xóa toàn bộ học sinh, điểm danh và phân công liên quan. Tiếp tục?",icon='warning',parent=w): return
        for item in sel:
            v=tree.item(item,'values'); cid,cname=v[0],v[1]
            s_rows=qry("SELECT student_id,user_id FROM students WHERE class_id=%s",(cid,),fetch=True) or []
            sids=[s[0] for s in s_rows]; uids=[s[1] for s in s_rows]
            try:
                with DB() as db:
                    if not db: continue
                    if sids:
                        ph=",".join(["%s"]*len(sids))
                        db.run(f"DELETE FROM attendance WHERE student_id IN ({ph})",sids)
                        db.run(f"DELETE FROM grades WHERE student_id IN ({ph})",sids)
                    db.run("DELETE FROM teaching_assignments WHERE class_id=%s",(cid,))
                    db.run("DELETE FROM self_attendance_configs WHERE class_id=%s",(cid,))
                    db.run("DELETE FROM students WHERE class_id=%s",(cid,))
                    if uids: db.run(f"DELETE FROM users WHERE user_id IN ({','.join(['%s']*len(uids))})",uids)
                    db.run("DELETE FROM classes WHERE class_id=%s",(cid,))
                tree.delete(item); messagebox.showinfo("Thành công",f"Đã xóa lớp '{cname}'!",parent=w)
            except Exception as e: messagebox.showerror("Lỗi",str(e),parent=w)

    btn_row(w,[("Thêm lớp",add,{}),("Xóa lớp",delete,{"bg":"#f8d7da"})])

def open_teacher_assignment():
    w=win("Phân công giáo viên","650x420")
    tk.Label(w,text="PHÂN CÔNG GIÁO VIÊN",font=("Arial",16,"bold")).pack(pady=12)
    tree=treeview(w,("Lớp","Môn học","Giáo viên"),{})
    rows=qry("SELECT c.class_name,s.subject_name,u.full_name FROM teaching_assignments ta JOIN classes c ON ta.class_id=c.class_id JOIN subjects s ON ta.subject_id=s.subject_id JOIN users u ON ta.teacher_id=u.user_id",fetch=True)
    if rows:
        for r in rows: tree.insert("",tk.END,values=r)

def open_admin_report():
    w=win("Báo cáo tổng hợp","700x420")
    tk.Label(w,text="BÁO CÁO TỔNG HỢP",font=("Arial",16,"bold")).pack(pady=12)
    ts=qry("SELECT COUNT(*) FROM students",fetch=True)[0][0]
    tt=qry("SELECT COUNT(*) FROM users WHERE role_id=1",fetch=True)[0][0]
    tc=qry("SELECT COUNT(*) FROM classes",fetch=True)[0][0]
    f=tk.Frame(w); f.pack(pady=10,padx=20,fill="x")
    for txt in [f"Tổng học sinh: {ts}",f"Tổng giáo viên: {tt}",f"Tổng lớp: {tc}"]:
        tk.Label(f,text=txt,anchor="w").pack(fill="x")
    tree=treeview(w,("Tiêu chí","Giá trị"),{"Tiêu chí":300,"Giá trị":300})
    att=qry("SELECT COUNT(*),SUM(status='Có mặt'),SUM(status='Vắng mặt') FROM attendance WHERE DATE(attendance_date)=CURDATE()",fetch=True)
    total,present,absent=(att[0] if att else (0,0,0))
    for item in [(f"Tỷ lệ chuyên cần",f"{round((present or 0)/(total or 1)*100,1)}%"),(f"Số buổi vắng",f"{absent or 0}"),(f"Số lớp",f"{tc}")]:
        tree.insert("",tk.END,values=item)

def open_admin_dashboard():
    w=tk.Toplevel(); w.title("Trung tâm quản lý"); w.geometry("700x520")
    tk.Label(w,text="TRUNG TÂM QUẢN LÝ",font=("Arial",18,"bold")).pack(pady=20)
    f=tk.Frame(w); f.pack()
    for text,cmd in [("Quản lý tài khoản",open_account_management),("Quản lý giáo viên",open_teacher_management),
                     ("Quản lý học sinh",open_student_management),("Quản lý lớp học",open_class_management),
                     ("Phân công giáo viên",open_teacher_assignment),("Xem báo cáo tổng hợp",open_admin_report)]:
        tk.Button(f,text=text,width=30,height=2,command=cmd).pack(pady=5)
    tk.Button(f,text="Đăng xuất",width=30,height=2,bg="#f8d7da",command=lambda:logout(w)).pack(pady=15)
    w.protocol("WM_DELETE_WINDOW",w.destroy)

# ===================== TEACHER =====================

def open_class_student_list(class_id, class_name):
    dw=win(f"Lớp {class_name}","820x460")
    tk.Label(dw,text=f"DANH SÁCH HỌC SINH LỚP {class_name}",font=("Arial",14,"bold")).pack(pady=10)
    cols=("Họ và tên","Ngày sinh","Mã học sinh","Giới tính","Trạng thái")
    tree=treeview(dw,cols,{"Họ và tên":200,"Ngày sinh":110,"Mã học sinh":110,"Giới tính":80,"Trạng thái":130})
    rows=qry("SELECT u.full_name,DATE_FORMAT(s.date_of_birth,%s),s.student_code,COALESCE(s.gender,'N/A'),COALESCE(a.status,'Chưa điểm danh') FROM students s JOIN users u ON s.user_id=u.user_id LEFT JOIN attendance a ON a.student_id=s.student_id AND DATE(a.attendance_date)=CURDATE() WHERE s.class_id=%s ORDER BY u.full_name",('%d/%m/%Y',class_id),fetch=True)
    if rows:
        for r in rows: tree.insert("",tk.END,values=r)
    else: tree.insert("",tk.END,values=("Lớp chưa có học sinh","","","",""))
    tk.Button(dw,text="Đóng",width=12,command=dw.destroy).pack(pady=10)

def open_teacher_class_list(on_selected):
    w=win("Danh sách lớp","650x420")
    tk.Label(w,text="DANH SÁCH LỚP",font=("Arial",16,"bold")).pack(pady=12)
    tree=treeview(w,("Mã lớp","Tên lớp","Số HS"),{"Mã lớp":80,"Tên lớp":200,"Số HS":80})
    rows=qry("SELECT c.class_id,c.class_name,COUNT(s.student_id) FROM classes c LEFT JOIN students s ON c.class_id=s.class_id GROUP BY c.class_id,c.class_name",fetch=True)
    if rows:
        for r in rows: tree.insert("",tk.END,values=r)
    def confirm():
        sel=tree.selection()
        if not sel: messagebox.showwarning("Thông báo","Chọn một lớp!"); return
        v=tree.item(sel[0],'values'); on_selected(v[0],v[1]); w.destroy()
    tk.Button(w,text="Chọn lớp này",command=confirm,bg="#d4edda",width=20,font=("Arial",10,"bold")).pack(pady=10)

def open_teacher_attendance(class_id, class_name, callback):
    w=win(f"Điểm danh - {class_name}","600x500")
    tk.Label(w,text=f"ĐIỂM DANH: {class_name}",font=("Arial",14,"bold"),fg="blue").pack(pady=10)
    cont=tk.Frame(w); cont.pack(fill="both",expand=True,padx=10,pady=5)
    canvas=tk.Canvas(cont); sb=ttk.Scrollbar(cont,orient="vertical",command=canvas.yview)
    sf=tk.Frame(canvas); sf.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0,0),window=sf,anchor="nw"); canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
    rows=qry("SELECT s.student_id,u.full_name,s.class_id FROM students s JOIN users u ON s.user_id=u.user_id WHERE s.class_id=%s ORDER BY u.full_name",(class_id,),fetch=True)
    opts=["Chưa điểm danh","Có mặt","Vắng mặt","Muộn","Có phép"]; svars=[]
    if rows:
        for i,(sid,name,cid) in enumerate(rows):
            tk.Label(sf,text=f"{i+1}. {name}",anchor="w",width=30).grid(row=i,column=0,sticky="w",pady=5,padx=5)
            sv=tk.StringVar(value=opts[0]); svars.append((sid,cid,sv))
            ttk.Combobox(sf,textvariable=sv,values=opts,state="readonly",width=15).grid(row=i,column=1,padx=5)

    def save():
        upd=[]; dl=[]
        for sid,cid,sv in svars:
            s=sv.get()
            (dl if s=="Chưa điểm danh" else upd).append((sid,cid,s,current_user["user_id"]) if s!="Chưa điểm danh" else sid)
        try:
            with DB() as db:
                if not db: return
                if upd: db.many("INSERT INTO attendance(student_id,class_id,attendance_date,status,recorded_by) VALUES(%s,%s,CURDATE(),%s,%s) ON DUPLICATE KEY UPDATE status=VALUES(status),recorded_by=VALUES(recorded_by)",upd)
                if dl: db.run(f"DELETE FROM attendance WHERE student_id IN ({','.join(['%s']*len(dl))}) AND attendance_date=CURDATE()",dl)
            messagebox.showinfo("Thành công",f"Đã lưu điểm danh {class_name}",parent=w)
            if callback: callback(); w.destroy()
        except Exception as e: messagebox.showerror("Lỗi",str(e),parent=w)

    tk.Button(w,text="Lưu điểm danh",bg="lightgreen",font=("Arial",12,"bold"),command=save).pack(pady=12)

def open_teacher_self_config(class_id, class_name):
    w=win(f"Cấu hình tự điểm danh - {class_name}","380x300",True)
    tk.Label(w,text=f"MỞ TỰ ĐIỂM DANH: {class_name}",font=("Arial",12,"bold")).pack(pady=10)
    ed=lbl_entry(w,"Ngày (YYYY-MM-DD):"); ed.insert(0,datetime.now().strftime('%Y-%m-%d'))
    es=lbl_entry(w,"Giờ bắt đầu (HH:MM:SS):"); es.insert(0,"07:00:00")
    ee=lbl_entry(w,"Giờ kết thúc (HH:MM:SS):"); ee.insert(0,"17:00:00")
    def save():
        d,s,e=ed.get().strip(),es.get().strip(),ee.get().strip()
        try: [datetime.strptime(x,f) for x,f in [(d,'%Y-%m-%d'),(s,'%H:%M:%S'),(e,'%H:%M:%S')]]
        except: messagebox.showerror("Lỗi","Định dạng ngày/giờ không hợp lệ!",parent=w); return
        qry("INSERT INTO self_attendance_configs(class_id,auth_date,start_time,end_time) VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE start_time=VALUES(start_time),end_time=VALUES(end_time)",(class_id,d,s,e))
        messagebox.showinfo("Thành công",f"Đã mở tự điểm danh cho {class_name}!",parent=w); w.destroy()
    tk.Button(w,text="Lưu cấu hình",bg="#fff3cd",font=("Arial",10,"bold"),command=save).pack(pady=20)

def open_teacher_dashboard():
    w=win("Teacher Dashboard","900x650")
    hlbl=tk.Label(w,text="GIÁO VIÊN - QUẢN LÝ ĐIỂM DANH",font=("Arial",18,"bold")); hlbl.pack(pady=10)
    sel={"id":None,"name":""}
    mf=tk.Frame(w); mf.pack(pady=10)
    tree=treeview(w,("Mã HS","Họ tên","Trạng thái"),{})

    def refresh():
        if not sel["id"]: return
        for i in tree.get_children(): tree.delete(i)
        rows=qry("SELECT s.student_code,u.full_name,COALESCE(a.status,'Chưa điểm danh') FROM students s JOIN users u ON s.user_id=u.user_id LEFT JOIN attendance a ON s.student_id=a.student_id AND DATE(a.attendance_date)=CURDATE() WHERE s.class_id=%s ORDER BY u.full_name",(sel["id"],),fetch=True)
        if rows:
            for r in rows: tree.insert("",tk.END,values=r)

    def on_picked(cid,cname):
        sel["id"]=cid; sel["name"]=cname; hlbl.config(text=f"LỚP ĐANG CHỌN: {cname}")
        btn_att.config(state="normal",bg="#d4edda"); btn_cfg.config(state="normal",bg="#fff3cd"); refresh()

    tk.Button(mf,text="Chọn lớp",width=20,command=lambda:open_teacher_class_list(on_picked)).grid(row=0,column=0,padx=5)
    tk.Button(mf,text="Xuất báo cáo",width=20,command=lambda:messagebox.showinfo("Thông báo","Chức năng xuất báo cáo!")).grid(row=0,column=1,padx=5)
    btn_att=tk.Button(mf,text="Điểm danh",width=20,state="disabled",command=lambda:open_teacher_attendance(sel["id"],sel["name"],refresh)); btn_att.grid(row=0,column=2,padx=5)
    btn_cfg=tk.Button(mf,text="Cài đặt tự điểm danh",width=20,state="disabled",command=lambda:open_teacher_self_config(sel["id"],sel["name"])); btn_cfg.grid(row=0,column=3,padx=5)
    tk.Button(w,text="Đăng xuất",width=20,bg="#f8d7da",command=lambda:logout(w)).pack(pady=10)
    w.protocol("WM_DELETE_WINDOW",w.destroy)

# ===================== STUDENT =====================

def open_self_attendance(auth_date, start_time, end_time, callback):
    w=win("Tự điểm danh","520x340",True)
    tk.Label(w,text="TỰ ĐIỂM DANH",font=("Arial",16,"bold")).pack(pady=12)
    info=qry("SELECT u.full_name,c.class_name,s.student_id,s.class_id FROM students s JOIN users u ON s.user_id=u.user_id JOIN classes c ON s.class_id=c.class_id WHERE u.user_id=%s",(current_user["user_id"],),fetch=True)
    if not info: return
    fname,cname,sid,cid=info[0]
    tk.Label(w,text=f"Học sinh: {fname}",font=("Arial",10)).pack(anchor="w",padx=20)
    tk.Label(w,text=f"Lớp: {cname}").pack(anchor="w",padx=20)
    tk.Label(w,text=f"Khung giờ: {auth_date} ({start_time} - {end_time})",fg="blue").pack(anchor="w",padx=20,pady=(5,15))
    sv=tk.StringVar()
    ttk.Combobox(w,textvariable=sv,values=["Có mặt","Vắng mặt","Muộn","Có phép"],state="readonly",width=30).pack(padx=20,pady=10)
    def save():
        s=sv.get()
        if not s: messagebox.showwarning("Thông báo","Chọn trạng thái!",parent=w); return
        r=qry("INSERT INTO attendance(student_id,class_id,attendance_date,status,recorded_by) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE status=VALUES(status)",(sid,cid,auth_date,s,current_user["user_id"]))
        if r: messagebox.showinfo("Thông báo",f"Đã điểm danh: {s}",parent=w); callback(); w.destroy()
        else: messagebox.showerror("Lỗi","Điểm danh thất bại!",parent=w)
    tk.Button(w,text="Gửi điểm danh",width=18,bg="lightgreen",font=("Arial",12,"bold"),command=save).pack(pady=14)

def open_student_dashboard():
    w=win("Student Dashboard","700x520")
    tk.Label(w,text="THÔNG TIN ĐIỂM DANH",font=("Arial",18,"bold")).pack(pady=15)
    if not current_user or "user_id" not in current_user:
        messagebox.showerror("Lỗi","Thông tin người dùng không hợp lệ.",parent=w); w.destroy(); return
    info=qry("SELECT s.student_code,u.full_name,c.class_name FROM students s JOIN users u ON s.user_id=u.user_id JOIN classes c ON s.class_id=c.class_id WHERE u.user_id=%s",(current_user["user_id"],),fetch=True)
    f=tk.Frame(w); f.pack(pady=10)
    if info:
        code,name,cname=info[0]
        for t in [f"Mã HS: {code}",f"Họ tên: {name}",f"Lớp: {cname}"]: tk.Label(f,text=t).pack(anchor="w")
    else: messagebox.showwarning("Thông báo","Không tìm thấy thông tin học sinh.",parent=w)
    tree=treeview(w,("Ngày","Bắt đầu","Kết thúc","Trạng thái"),{"Ngày":100,"Bắt đầu":100,"Kết thúc":100,"Trạng thái":120})

    def load():
        for i in tree.get_children(): tree.delete(i)
        slots=qry("SELECT DATE_FORMAT(conf.auth_date,%s),TIME_FORMAT(conf.start_time,%s),TIME_FORMAT(conf.end_time,%s),CASE WHEN att.status IS NOT NULL THEN att.status WHEN NOW() BETWEEN CONCAT(conf.auth_date,' ',conf.start_time) AND CONCAT(conf.auth_date,' ',conf.end_time) THEN 'Đang mở' ELSE 'Vắng mặt' END FROM self_attendance_configs conf JOIN students s ON s.class_id=conf.class_id LEFT JOIN attendance att ON att.student_id=s.student_id AND att.attendance_date=conf.auth_date WHERE s.user_id=%s ORDER BY conf.auth_date DESC,conf.start_time DESC",('%Y-%m-%d','%H:%i:%s','%H:%i:%s',current_user["user_id"]),fetch=True)
        if slots:
            for r in slots: tree.insert("",tk.END,values=r)

    load()

    def do_self_att():
        sel=tree.selection()
        if not sel: messagebox.showwarning("Thông báo","Chọn khung giờ cần điểm danh!"); return
        ad,s,e,_=tree.item(sel[0],'values')
        now=datetime.now(); cd=now.strftime('%Y-%m-%d'); ct=now.strftime('%H:%M:%S')
        if str(ad)==cd and str(s)<=ct<=str(e): open_self_attendance(ad,s,e,load)
        else: messagebox.showwarning("Ngoài khung giờ",f"Chỉ điểm danh được:\nNgày: {ad}\nGiờ: {s} - {e}\n\nHiện tại: {cd} {ct}")

    tk.Button(w,text="Tự điểm danh",width=20,bg="#d4edda",font=("Arial",10,"bold"),command=do_self_att).pack(pady=10)
    tk.Button(w,text="Đăng xuất",width=20,bg="#f8d7da",command=lambda:logout(w)).pack(pady=5)
    w.protocol("WM_DELETE_WINDOW",w.destroy)

# ===================== LOGIN WINDOW =====================

login_window=tk.Tk(); login_window.title("Hệ thống điểm danh học sinh"); login_window.geometry("450x400")
tk.Label(login_window,text="HỆ THỐNG ĐIỂM DANH HỌC SINH",font=("Arial",16,"bold")).pack(pady=20)
entry_username=lbl_entry(login_window,"Tên đăng nhập")
entry_password=lbl_entry(login_window,"Mật khẩu",show="*")
tk.Label(login_window,text="Vai trò").pack(pady=(10,0))
role_var=tk.StringVar()
ttk.Combobox(login_window,textvariable=role_var,values=["Quản lý","Giáo viên","Học sinh"],state="readonly",width=27).pack()
tk.Button(login_window,text="Đăng nhập",width=20,bg="lightblue",font=("Arial",11),command=login).pack(pady=12)

if check_schema(): login_window.mainloop()
else: login_window.destroy()