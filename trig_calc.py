import math
import ast
import operator as op
import tkinter as tk
from tkinter import messagebox

# =========================
# 数学工具（默认角度制：deg）
# =========================
def sin_d(x): return math.sin(math.radians(x))
def cos_d(x): return math.cos(math.radians(x))
def tan_d(x): return math.tan(math.radians(x))

def asin_d(x): return math.degrees(math.asin(x))
def acos_d(x): return math.degrees(math.acos(x))
def atan_d(x): return math.degrees(math.atan(x))

def safe_float(s: str):
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"数值格式错误：{s}")

def fmt(x: float):
    # 统一格式化显示：去掉多余尾零
    if x is None:
        return ""
    if not math.isfinite(x):
        return "NaN"
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if s else "0"


# ======================================
# 安全表达式计算：支持 sin/cos/tg(度)
# 示例：sin(10)+cos(20)*2 ；tg 表示 tan
# ======================================
_ALLOWED_FUNCS = {
    "sin": sin_d,
    "cos": cos_d,
    "tan": tan_d,
    "tg": tan_d,       # 正切 tg
    "asin": asin_d,
    "acos": acos_d,
    "atan": atan_d,
    "sqrt": math.sqrt,
    "abs": abs,
    "pi": math.pi,
    "e": math.e,
}

_ALLOWED_BINOP = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARY = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

def safe_eval(expr: str):
    expr = (expr or "").strip()
    if not expr:
        raise ValueError("请输入三角函数表达式，例如：sin(10) 或 tg(45)+cos(30)")

    node = ast.parse(expr, mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return float(n.value)
            raise ValueError("只允许数字常量")
        if isinstance(n, ast.Name):
            if n.id in _ALLOWED_FUNCS and isinstance(_ALLOWED_FUNCS[n.id], (int, float)):
                return float(_ALLOWED_FUNCS[n.id])
            # 允许 pi/e 这类常量名
            if n.id in ("pi", "e"):
                return float(_ALLOWED_FUNCS[n.id])
            raise ValueError(f"不允许的名称：{n.id}")
        if isinstance(n, ast.BinOp):
            if type(n.op) not in _ALLOWED_BINOP:
                raise ValueError("不允许的运算符")
            return _ALLOWED_BINOP[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp):
            if type(n.op) not in _ALLOWED_UNARY:
                raise ValueError("不允许的一元运算")
            return _ALLOWED_UNARY[type(n.op)](_eval(n.operand))
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name):
                raise ValueError("只允许调用函数名，例如 sin(30)")
            fn = n.func.id
            if fn not in _ALLOWED_FUNCS or not callable(_ALLOWED_FUNCS[fn]):
                raise ValueError(f"不允许的函数：{fn}")
            args = [_eval(a) for a in n.args]
            return float(_ALLOWED_FUNCS[fn](*args))
        raise ValueError("表达式包含不允许的结构")

    return _eval(node)


# =========================
# GUI
# =========================
class TrigCalculatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("角度计算器")
        self.root.resizable(False, False)

        # 主背景
        self.bg = "#c9c9c9"
        self.root.configure(bg=self.bg)

        # ===== 顶部三块：反正弦/反正切/反余弦 =====
        top = tk.Frame(root, bg=self.bg)
        top.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self._build_asin_panel(top).grid(row=0, column=0, padx=6)
        self._build_atan_panel(top).grid(row=0, column=1, padx=6)
        self._build_acos_panel(top).grid(row=0, column=2, padx=6)

        # ===== 注释 + 右侧示意图 =====
        mid = tk.Frame(root, bg=self.bg)
        mid.grid(row=1, column=0, padx=8, sticky="w")

        note = tk.Frame(mid, bg=self.bg)
        note.grid(row=0, column=0, sticky="w")

        tk.Label(note, text="注：正弦值等于角对边除以斜边；\n"
                            "    余弦值等于角邻边除以斜边；\n"
                            "    正切值等于角对边除以邻边。",
                 bg=self.bg, justify="left").grid(row=0, column=0, sticky="w")

        tri = tk.Frame(mid, bg=self.bg)
        tri.grid(row=0, column=1, padx=20, sticky="e")
        self._draw_triangle(tri)

        # ===== 分隔蓝条 =====
        self._blue_bar(root, row=2)

        # ===== 函数计算 =====
        func = tk.Frame(root, bg=self.bg)
        func.grid(row=3, column=0, padx=8, pady=6, sticky="w")

        tk.Label(func, text="三角函数示例：sin(10)，正切用 tg 表示", bg=self.bg)\
            .grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 4))

        tk.Label(func, text="输入三角函数", bg=self.bg).grid(row=1, column=0, sticky="w")
        self.var_expr = tk.StringVar()
        tk.Entry(func, textvariable=self.var_expr, width=30).grid(row=1, column=1, padx=(6, 10))

        tk.Button(func, text="函数计算", width=10, command=self.on_eval_expr)\
            .grid(row=1, column=2, padx=(0, 10))

        tk.Label(func, text="函数计算结果", bg=self.bg).grid(row=1, column=3, sticky="w")
        self.var_expr_out = tk.StringVar()
        tk.Entry(func, textvariable=self.var_expr_out, width=24, state="readonly")\
            .grid(row=1, column=4, padx=(6, 0))

        # ===== 分隔蓝条 =====
        self._blue_bar(root, row=4)

        # ===== 底部：已知数据 -> 边长计算 -> 计算结果 =====
        bottom = tk.Frame(root, bg=self.bg)
        bottom.grid(row=5, column=0, padx=8, pady=10, sticky="w")

        left = tk.LabelFrame(bottom, text="已知数据", bg=self.bg)
        left.grid(row=0, column=0, padx=(0, 14), pady=4)

        self.var_k_angle = tk.StringVar()
        self.var_k_opp = tk.StringVar()
        self.var_k_hyp = tk.StringVar()
        self.var_k_adj = tk.StringVar()

        self._kv_row(left, 0, "角度", self.var_k_angle)
        self._kv_row(left, 1, "对边长度", self.var_k_opp)
        self._kv_row(left, 2, "斜边长度", self.var_k_hyp)
        self._kv_row(left, 3, "邻边长度", self.var_k_adj)

        mid_btn = tk.Frame(bottom, bg=self.bg)
        mid_btn.grid(row=0, column=1, padx=(0, 14))
        tk.Button(mid_btn, text="边长计算", width=10, command=self.on_calc_sides)\
            .grid(row=0, column=0, pady=40)

        right = tk.LabelFrame(bottom, text="计算结果", bg=self.bg)
        right.grid(row=0, column=2, padx=(0, 0), pady=4)

        self.var_r_opp = tk.StringVar()
        self.var_r_hyp = tk.StringVar()
        self.var_r_adj = tk.StringVar()


        self._kv_row(right, 0, "对边长度", self.var_r_opp, readonly=True)
        self._kv_row(right, 1, "斜边长度", self.var_r_hyp, readonly=True)
        self._kv_row(right, 2, "邻边长度", self.var_r_adj, readonly=True)

        # 初始清空
        self.clear_outputs()

    def _blue_bar(self, parent, row: int):
        bar = tk.Frame(parent, bg="#1f66ff", height=4, width=720)
        bar.grid(row=row, column=0, sticky="we", padx=6, pady=4)

    def _kv_row(self, parent, r, label, var, readonly=False):
        tk.Label(parent, text=label, bg=self.bg, width=10, anchor="w").grid(row=r, column=0, padx=6, pady=6)
        e = tk.Entry(parent, textvariable=var, width=22)
        e.grid(row=r, column=1, padx=6, pady=6)
        if readonly:
            e.configure(state="readonly")

    def _draw_triangle(self, parent):
        c = tk.Canvas(parent, width=220, height=110, bg=self.bg, highlightthickness=0)
        c.pack()
        # 三角形
        x1, y1 = 20, 85
        x2, y2 = 180, 85
        x3, y3 = 180, 25
        c.create_line(x1, y1, x2, y2, width=3)
        c.create_line(x2, y2, x3, y3, width=3)
        c.create_line(x1, y1, x3, y3, width=3)

        c.create_text(110, 92, text="邻边", anchor="n")
        c.create_text(190, 55, text="对边", anchor="w")
        c.create_text(110, 40, text="斜边", anchor="s")
        c.create_text(30, 80, text="角", anchor="e")

    def clear_outputs(self):
        self.var_asin_angle.set("")
        self.var_atan_angle.set("")
        self.var_acos_angle.set("")
        self.var_expr_out.set("")
        self.var_r_opp.set("")
        self.var_r_hyp.set("")
        self.var_r_adj.set("")

    # ===== 顶部三个面板 =====
    def _build_asin_panel(self, parent):
        f = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_asin_opp = tk.StringVar()
        self.var_asin_hyp = tk.StringVar()
        self.var_asin_angle = tk.StringVar()

        tk.Label(f, text="对边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_asin_opp, width=16).grid(row=0, column=1, padx=6)

        tk.Label(f, text="斜边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_asin_hyp, width=16).grid(row=1, column=1, padx=6)

        tk.Label(f, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_asin_angle, width=16, state="readonly")\
            .grid(row=2, column=1, padx=6)

        tk.Button(f, text="求反正弦角度", width=18, command=self.on_asin)\
            .grid(row=3, column=0, columnspan=2, pady=(6, 2))
        return f

    def _build_atan_panel(self, parent):
        f = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_atan_opp = tk.StringVar()
        self.var_atan_adj = tk.StringVar()
        self.var_atan_angle = tk.StringVar()

        tk.Label(f, text="对边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_atan_opp, width=16).grid(row=0, column=1, padx=6)

        tk.Label(f, text="邻边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_atan_adj, width=16).grid(row=1, column=1, padx=6)

        tk.Label(f, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_atan_angle, width=16, state="readonly")\
            .grid(row=2, column=1, padx=6)

        tk.Button(f, text="求反正切角度", width=18, command=self.on_atan)\
            .grid(row=3, column=0, columnspan=2, pady=(6, 2))
        return f

    def _build_acos_panel(self, parent):
        f = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_acos_adj = tk.StringVar()
        self.var_acos_hyp = tk.StringVar()
        self.var_acos_angle = tk.StringVar()

        tk.Label(f, text="邻边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_acos_adj, width=16).grid(row=0, column=1, padx=6)

        tk.Label(f, text="斜边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_acos_hyp, width=16).grid(row=1, column=1, padx=6)

        tk.Label(f, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(f, textvariable=self.var_acos_angle, width=16, state="readonly")\
            .grid(row=2, column=1, padx=6)

        tk.Button(f, text="求反余弦角度", width=18, command=self.on_acos)\
            .grid(row=3, column=0, columnspan=2, pady=(6, 2))
        return f

    # ===== 事件处理 =====
    def on_asin(self):
        try:
            opp = safe_float(self.var_asin_opp.get())
            hyp = safe_float(self.var_asin_hyp.get())
            if opp is None or hyp is None:
                raise ValueError("请输入：对边长度 与 斜边长度")
            if hyp == 0:
                raise ValueError("斜边长度不能为 0")
            ratio = opp / hyp
            if ratio < -1 or ratio > 1:
                raise ValueError("对边/斜边 必须在 [-1, 1] 范围内")
            angle = asin_d(ratio)
            self.var_asin_angle.set(fmt(angle))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_atan(self):
        try:
            opp = safe_float(self.var_atan_opp.get())
            adj = safe_float(self.var_atan_adj.get())
            if opp is None or adj is None:
                raise ValueError("请输入：对边长度 与 邻边长度")
            if adj == 0:
                raise ValueError("邻边长度不能为 0（否则正切无定义）")
            angle = atan_d(opp / adj)
            self.var_atan_angle.set(fmt(angle))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_acos(self):
        try:
            adj = safe_float(self.var_acos_adj.get())
            hyp = safe_float(self.var_acos_hyp.get())
            if adj is None or hyp is None:
                raise ValueError("请输入：邻边长度 与 斜边长度")
            if hyp == 0:
                raise ValueError("斜边长度不能为 0")
            ratio = adj / hyp
            if ratio < -1 or ratio > 1:
                raise ValueError("邻边/斜边 必须在 [-1, 1] 范围内")
            angle = acos_d(ratio)
            self.var_acos_angle.set(fmt(angle))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_eval_expr(self):
        try:
            val = safe_eval(self.var_expr.get())
            self.var_expr_out.set(fmt(val))
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_calc_sides(self):
        """
        支持两种用法：
        1) 输入角度 +（对边/斜边/邻边 任意一个） => 算出其余两边
        2) 不输入角度，但输入任意两边 => 算出第三边 + 自动回填角度
        """
        try:
            angle = safe_float(self.var_k_angle.get())
            opp = safe_float(self.var_k_opp.get())
            hyp = safe_float(self.var_k_hyp.get())
            adj = safe_float(self.var_k_adj.get())

            # 情况2：无角度，给两边
            if angle is None:
                provided = [opp is not None, hyp is not None, adj is not None]
                if sum(provided) < 2:
                    raise ValueError("请输入：角度+任意一边，或不输入角度但输入任意两边")
                # opp & hyp
                if opp is not None and hyp is not None:
                    if hyp <= 0:
                        raise ValueError("斜边必须 > 0")
                    if abs(opp) > hyp:
                        raise ValueError("对边不能大于斜边")
                    adj = math.sqrt(max(hyp*hyp - opp*opp, 0.0))
                    angle = asin_d(opp / hyp)
                # adj & hyp
                elif adj is not None and hyp is not None:
                    if hyp <= 0:
                        raise ValueError("斜边必须 > 0")
                    if abs(adj) > hyp:
                        raise ValueError("邻边不能大于斜边")
                    opp = math.sqrt(max(hyp*hyp - adj*adj, 0.0))
                    angle = acos_d(adj / hyp)
                # opp & adj
                elif opp is not None and adj is not None:
                    hyp = math.sqrt(opp*opp + adj*adj)
                    if adj == 0:
                        angle = 90.0
                    else:
                        angle = atan_d(opp / adj)

                self.var_k_angle.set(fmt(angle))

            # 情况1：有角度
            if angle is None:
                raise ValueError("请输入角度（度）")

            # 归一化角度范围（可选）
            # if angle <= 0 or angle >= 90:  # 如果你只允许锐角可打开
            #     raise ValueError("角度建议在 (0, 90) 度内")

            sinv = sin_d(angle)
            cosv = cos_d(angle)
            tanv = tan_d(angle)

            # 根据给定的那一边推导
            if hyp is not None:
                if hyp <= 0:
                    raise ValueError("斜边必须 > 0")
                opp2 = hyp * sinv
                adj2 = hyp * cosv
                opp, adj = opp2, adj2
            elif opp is not None:
                if sinv == 0:
                    raise ValueError("角度的 sin 为 0，无法由对边推导斜边")
                hyp2 = opp / sinv
                if tanv == 0:
                    raise ValueError("角度的 tan 为 0，无法由对边推导邻边")
                adj2 = opp / tanv
                hyp, adj = hyp2, adj2
            elif adj is not None:
                if cosv == 0:
                    raise ValueError("角度的 cos 为 0，无法由邻边推导斜边")
                hyp2 = adj / cosv
                opp2 = adj * tanv
                hyp, opp = hyp2, opp2
            else:
                raise ValueError("请输入：角度 +（对边/斜边/邻边 任意一个）")

            # 输出
            self.var_r_opp.set(fmt(opp))
            self.var_r_hyp.set(fmt(hyp))
            self.var_r_adj.set(fmt(adj))

        except Exception as e:
            messagebox.showerror("错误", str(e))


def main():
    root = tk.Tk()
    app = TrigCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
