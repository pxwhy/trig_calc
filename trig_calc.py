"""
实现逻辑说明：
1. 程序启动后默认展示风向时钟计算器主界面，不再直接展示三角函数界面。
2. 主界面左上角提供一个隐藏图标按钮，短时间内连续点击 3 下会弹出三角函数计算窗口，
   连续点击 4 下会切换主界面中的风向角度区域显示状态。
3. 主界面提供基础科学计算、四则运算与时钟夹角计算，":" 用于输入 HH:MM 时间并计算时针分针夹角。
4. 风向角度区域基于当前结果计算相对方位角，并在主界面顶部展示风向或时钟换算结果。
"""

import ast
import math
import operator as op
import re
import tkinter as tk
from tkinter import messagebox


def sin_d(x):
    return math.sin(math.radians(x))


def cos_d(x):
    return math.cos(math.radians(x))


def tan_d(x):
    return math.tan(math.radians(x))


def asin_d(x):
    return math.degrees(math.asin(x))


def acos_d(x):
    return math.degrees(math.acos(x))


def atan_d(x):
    return math.degrees(math.atan(x))


def safe_float(text: str):
    text = (text or "").strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"数值格式错误：{text}") from exc


def fmt(value: float):
    if value is None:
        return ""
    if not math.isfinite(value):
        return "NaN"
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return text if text else "0"


def fmt_angle(value: float):
    if value is None:
        return ""
    if not math.isfinite(value):
        return "NaN"
    return f"{value:.1f}"


def normalize_angle(angle: float):
    angle %= 360.0
    if angle < 0:
        angle += 360.0
    return angle


def parse_clock_time(text: str):
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{1,2})\s*", text or "")
    if match is None:
        raise ValueError("时间格式应为 HH:MM，例如 10:30")

    hours = int(match.group(1))
    minutes = int(match.group(2))
    if hours < 0 or hours > 23:
        raise ValueError("小时必须在 0 到 23 之间")
    if minutes < 0 or minutes > 59:
        raise ValueError("分钟必须在 0 到 59 之间")
    return hours, minutes


def calc_clock_angle(text: str):
    hours, minutes = parse_clock_time(text)
    hour_angle = normalize_angle((hours % 12) * 30 + minutes * 0.5)
    minute_angle = normalize_angle(minutes * 6)
    diff = abs(hour_angle - minute_angle)
    included_angle = min(diff, 360 - diff)
    return hour_angle, minute_angle, included_angle


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


def _build_allowed_names(angle_mode: str):
    if angle_mode == "rad":
        sin_func = math.sin
        cos_func = math.cos
        tan_func = math.tan
    else:
        sin_func = sin_d
        cos_func = cos_d
        tan_func = tan_d

    return {
        "sin": sin_func,
        "cos": cos_func,
        "tan": tan_func,
        "tg": tan_func,
        "asin": asin_d,
        "acos": acos_d,
        "atan": atan_d,
        "sqrt": math.sqrt,
        "abs": abs,
        "log": math.log10,
        "ln": math.log,
        "inv": lambda x: 1 / x,
        "pi": math.pi,
        "e": math.e,
    }


def safe_eval(expr: str, angle_mode: str = "deg"):
    expr = (expr or "").strip()
    if not expr:
        raise ValueError("请输入表达式")

    allowed_names = _build_allowed_names(angle_mode)
    node = ast.parse(expr, mode="eval")

    def _eval(current):
        if isinstance(current, ast.Expression):
            return _eval(current.body)
        if isinstance(current, ast.Constant):
            if isinstance(current.value, (int, float)):
                return float(current.value)
            raise ValueError("只允许数字常量")
        if isinstance(current, ast.Name):
            if current.id in ("pi", "e"):
                return float(allowed_names[current.id])
            raise ValueError(f"不允许的名称：{current.id}")
        if isinstance(current, ast.BinOp):
            handler = _ALLOWED_BINOP.get(type(current.op))
            if handler is None:
                raise ValueError("不允许的运算符")
            return handler(_eval(current.left), _eval(current.right))
        if isinstance(current, ast.UnaryOp):
            handler = _ALLOWED_UNARY.get(type(current.op))
            if handler is None:
                raise ValueError("不允许的一元运算")
            return handler(_eval(current.operand))
        if isinstance(current, ast.Call):
            if not isinstance(current.func, ast.Name):
                raise ValueError("只允许调用函数名，例如 sin(30)")
            fn_name = current.func.id
            func = allowed_names.get(fn_name)
            if func is None or not callable(func):
                raise ValueError(f"不允许的函数：{fn_name}")
            args = [_eval(arg) for arg in current.args]
            return float(func(*args))
        raise ValueError("表达式包含不允许的结构")

    return _eval(node)


class TrigCalculatorDialog:
    def __init__(self, root: tk.Tk, on_close):
        self._on_close = on_close
        self.window = tk.Toplevel(root)
        self.window.title("角度计算器")
        self.window.resizable(False, False)
        self.window.configure(bg="#c9c9c9")
        self.bg = "#c9c9c9"
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.window, bg=self.bg)
        top.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self._build_asin_panel(top).grid(row=0, column=0, padx=6)
        self._build_atan_panel(top).grid(row=0, column=1, padx=6)
        self._build_acos_panel(top).grid(row=0, column=2, padx=6)

        mid = tk.Frame(self.window, bg=self.bg)
        mid.grid(row=1, column=0, padx=8, sticky="w")

        note = tk.Frame(mid, bg=self.bg)
        note.grid(row=0, column=0, sticky="w")
        tk.Label(
            note,
            text=(
                "注：正弦值等于角对边除以斜边；\n"
                "    余弦值等于角邻边除以斜边；\n"
                "    正切值等于角对边除以邻边。"
            ),
            bg=self.bg,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        tri = tk.Frame(mid, bg=self.bg)
        tri.grid(row=0, column=1, padx=20, sticky="e")
        self._draw_triangle(tri)

        self._blue_bar(self.window, row=2)

        func = tk.Frame(self.window, bg=self.bg)
        func.grid(row=3, column=0, padx=8, pady=6, sticky="w")

        tk.Label(
            func,
            text="三角函数示例：sin(10)，正切用 tg 表示",
            bg=self.bg,
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 4))

        tk.Label(func, text="输入三角函数", bg=self.bg).grid(row=1, column=0, sticky="w")
        self.var_expr = tk.StringVar()
        tk.Entry(func, textvariable=self.var_expr, width=30).grid(row=1, column=1, padx=(6, 10))

        tk.Button(func, text="函数计算", width=10, command=self.on_eval_expr).grid(
            row=1, column=2, padx=(0, 10)
        )

        tk.Label(func, text="函数计算结果", bg=self.bg).grid(row=1, column=3, sticky="w")
        self.var_expr_out = tk.StringVar()
        tk.Entry(func, textvariable=self.var_expr_out, width=24, state="readonly").grid(
            row=1, column=4, padx=(6, 0)
        )

        self._blue_bar(self.window, row=4)

        bottom = tk.Frame(self.window, bg=self.bg)
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
        tk.Button(mid_btn, text="边长计算", width=10, command=self.on_calc_sides).grid(
            row=0, column=0, pady=40
        )

        right = tk.LabelFrame(bottom, text="计算结果", bg=self.bg)
        right.grid(row=0, column=2, pady=4)

        self.var_r_opp = tk.StringVar()
        self.var_r_hyp = tk.StringVar()
        self.var_r_adj = tk.StringVar()

        self._kv_row(right, 0, "对边长度", self.var_r_opp, readonly=True)
        self._kv_row(right, 1, "斜边长度", self.var_r_hyp, readonly=True)
        self._kv_row(right, 2, "邻边长度", self.var_r_adj, readonly=True)

        self.clear_outputs()

    def focus(self):
        try:
            self.window.focus_set()
        except tk.TclError:
            return

    def close(self):
        self.window.destroy()
        self._on_close()

    def _blue_bar(self, parent, row: int):
        bar = tk.Frame(parent, bg="#1f66ff", height=4, width=720)
        bar.grid(row=row, column=0, sticky="we", padx=6, pady=4)

    def _kv_row(self, parent, row_index, label, var, readonly=False):
        tk.Label(parent, text=label, bg=self.bg, width=10, anchor="w").grid(
            row=row_index, column=0, padx=6, pady=6
        )
        entry = tk.Entry(parent, textvariable=var, width=22)
        entry.grid(row=row_index, column=1, padx=6, pady=6)
        if readonly:
            entry.configure(state="readonly")

    def _draw_triangle(self, parent):
        canvas = tk.Canvas(parent, width=220, height=110, bg=self.bg, highlightthickness=0)
        canvas.pack()
        x1, y1 = 20, 85
        x2, y2 = 180, 85
        x3, y3 = 180, 25
        canvas.create_line(x1, y1, x2, y2, width=3)
        canvas.create_line(x2, y2, x3, y3, width=3)
        canvas.create_line(x1, y1, x3, y3, width=3)

        canvas.create_text(110, 92, text="邻边", anchor="n")
        canvas.create_text(190, 55, text="对边", anchor="w")
        canvas.create_text(110, 40, text="斜边", anchor="s")
        canvas.create_text(30, 80, text="角", anchor="e")

    def clear_outputs(self):
        self.var_asin_angle.set("")
        self.var_atan_angle.set("")
        self.var_acos_angle.set("")
        self.var_expr_out.set("")
        self.var_r_opp.set("")
        self.var_r_hyp.set("")
        self.var_r_adj.set("")

    def _build_asin_panel(self, parent):
        frame = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_asin_opp = tk.StringVar()
        self.var_asin_hyp = tk.StringVar()
        self.var_asin_angle = tk.StringVar()

        tk.Label(frame, text="对边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_asin_opp, width=16).grid(row=0, column=1, padx=6)

        tk.Label(frame, text="斜边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_asin_hyp, width=16).grid(row=1, column=1, padx=6)

        tk.Label(frame, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_asin_angle, width=16, state="readonly").grid(
            row=2, column=1, padx=6
        )

        tk.Button(frame, text="求反正弦角度", width=18, command=self.on_asin).grid(
            row=3, column=0, columnspan=2, pady=(6, 2)
        )
        return frame

    def _build_atan_panel(self, parent):
        frame = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_atan_opp = tk.StringVar()
        self.var_atan_adj = tk.StringVar()
        self.var_atan_angle = tk.StringVar()

        tk.Label(frame, text="对边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_atan_opp, width=16).grid(row=0, column=1, padx=6)

        tk.Label(frame, text="邻边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_atan_adj, width=16).grid(row=1, column=1, padx=6)

        tk.Label(frame, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_atan_angle, width=16, state="readonly").grid(
            row=2, column=1, padx=6
        )

        tk.Button(frame, text="求反正切角度", width=18, command=self.on_atan).grid(
            row=3, column=0, columnspan=2, pady=(6, 2)
        )
        return frame

    def _build_acos_panel(self, parent):
        frame = tk.LabelFrame(parent, bg=self.bg, padx=8, pady=6)
        self.var_acos_adj = tk.StringVar()
        self.var_acos_hyp = tk.StringVar()
        self.var_acos_angle = tk.StringVar()

        tk.Label(frame, text="邻边长度", bg=self.bg).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_acos_adj, width=16).grid(row=0, column=1, padx=6)

        tk.Label(frame, text="斜边长度", bg=self.bg).grid(row=1, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_acos_hyp, width=16).grid(row=1, column=1, padx=6)

        tk.Label(frame, text="计算角度", bg=self.bg).grid(row=2, column=0, sticky="w", pady=4)
        tk.Entry(frame, textvariable=self.var_acos_angle, width=16, state="readonly").grid(
            row=2, column=1, padx=6
        )

        tk.Button(frame, text="求反余弦角度", width=18, command=self.on_acos).grid(
            row=3, column=0, columnspan=2, pady=(6, 2)
        )
        return frame

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
            self.var_asin_angle.set(fmt(asin_d(ratio)))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def on_atan(self):
        try:
            opp = safe_float(self.var_atan_opp.get())
            adj = safe_float(self.var_atan_adj.get())
            if opp is None or adj is None:
                raise ValueError("请输入：对边长度 与 邻边长度")
            if adj == 0:
                raise ValueError("邻边长度不能为 0（否则正切无定义）")
            self.var_atan_angle.set(fmt(atan_d(opp / adj)))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

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
            self.var_acos_angle.set(fmt(acos_d(ratio)))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def on_eval_expr(self):
        try:
            self.var_expr_out.set(fmt(safe_eval(self.var_expr.get(), angle_mode="deg")))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))

    def on_calc_sides(self):
        try:
            angle = safe_float(self.var_k_angle.get())
            opp = safe_float(self.var_k_opp.get())
            hyp = safe_float(self.var_k_hyp.get())
            adj = safe_float(self.var_k_adj.get())

            if angle is None:
                provided = [opp is not None, hyp is not None, adj is not None]
                if sum(provided) < 2:
                    raise ValueError("请输入：角度+任意一边，或不输入角度但输入任意两边")

                if opp is not None and hyp is not None:
                    if hyp <= 0:
                        raise ValueError("斜边必须 > 0")
                    if abs(opp) > hyp:
                        raise ValueError("对边不能大于斜边")
                    adj = math.sqrt(max(hyp * hyp - opp * opp, 0.0))
                    angle = asin_d(opp / hyp)
                elif adj is not None and hyp is not None:
                    if hyp <= 0:
                        raise ValueError("斜边必须 > 0")
                    if abs(adj) > hyp:
                        raise ValueError("邻边不能大于斜边")
                    opp = math.sqrt(max(hyp * hyp - adj * adj, 0.0))
                    angle = acos_d(adj / hyp)
                elif opp is not None and adj is not None:
                    hyp = math.sqrt(opp * opp + adj * adj)
                    angle = 90.0 if adj == 0 else atan_d(opp / adj)

                self.var_k_angle.set(fmt(angle))

            if angle is None:
                raise ValueError("请输入角度（度）")

            sin_value = sin_d(angle)
            cos_value = cos_d(angle)
            tan_value = tan_d(angle)

            if hyp is not None:
                if hyp <= 0:
                    raise ValueError("斜边必须 > 0")
                opp = hyp * sin_value
                adj = hyp * cos_value
            elif opp is not None:
                if sin_value == 0:
                    raise ValueError("角度的 sin 为 0，无法由对边推导斜边")
                hyp = opp / sin_value
                if tan_value == 0:
                    raise ValueError("角度的 tan 为 0，无法由对边推导邻边")
                adj = opp / tan_value
            elif adj is not None:
                if cos_value == 0:
                    raise ValueError("角度的 cos 为 0，无法由邻边推导斜边")
                hyp = adj / cos_value
                opp = adj * tan_value
            else:
                raise ValueError("请输入：角度 +（对边/斜边/邻边 任意一个）")

            self.var_r_opp.set(fmt(opp))
            self.var_r_hyp.set(fmt(hyp))
            self.var_r_adj.set(fmt(adj))
        except Exception as exc:
            messagebox.showerror("错误", str(exc))


class WindClockCalculatorApp:
    SECRET_DELAY_MS = 400

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("风向时钟计算器")
        self.root.resizable(False, False)
        self.bg = "#e9e9e9"
        self.root.configure(bg=self.bg)

        self.angle_mode = "deg"
        self.expression = ""
        self.last_result = 0.0
        self.just_evaluated = False
        self.secret_clicks = 0
        self.secret_job = None
        self.trig_dialog = None

        self.var_expression = tk.StringVar(value="")
        self.var_display = tk.StringVar(value="0")
        self.var_wind_info = tk.StringVar(value="")
        self.var_clock_hint = tk.StringVar(value="基准: 12点方向=0°，顺时针递增")
        self.var_mode = tk.StringVar(value="模式: DEG")
        self.result_label = None

        self.wind_offsets = {
            "顺风": 180.0,
            "逆风": 0.0,
            "正左": 90.0,
            "正右": -90.0,
            "右前": -45.0,
            "左前": 45.0,
            "右后": -135.0,
            "左后": 135.0,
        }

        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.bg)
        header.grid(row=0, column=0, sticky="we", padx=8, pady=(8, 4))
        header.columnconfigure(1, weight=1)

        self.secret_button = tk.Button(
            header,
            text="◉",
            width=3,
            height=1,
            bd=1,
            relief="flat",
            padx=6,
            pady=4,
            bg="#dcdcdc",
            activebackground="#d0d0d0",
            command=self.on_secret_click,
        )
        self.secret_button.grid(row=0, column=0, sticky="w", padx=(0, 6))

        title = tk.Label(header, text="风向时钟计算器", bg=self.bg, anchor="w")
        title.grid(row=0, column=1, sticky="w")

        display = tk.Frame(self.root, bg=self.bg)
        display.grid(row=1, column=0, sticky="we", padx=12, pady=(4, 8))
        display.columnconfigure(0, weight=1)

        tk.Label(display, textvariable=self.var_expression, bg=self.bg, anchor="e").grid(
            row=0, column=0, sticky="we"
        )
        self.result_label = tk.Label(
            display,
            textvariable=self.var_display,
            bg=self.bg,
            anchor="e",
            font=("Helvetica", 30),
            width=16,
        )
        self.result_label.grid(row=1, column=0, sticky="e", pady=(8, 4))
        tk.Label(display, textvariable=self.var_wind_info, bg=self.bg, anchor="e").grid(
            row=2, column=0, sticky="e"
        )
        tk.Label(display, textvariable=self.var_clock_hint, bg=self.bg, anchor="e").grid(
            row=3, column=0, sticky="e"
        )
        tk.Label(display, text="角度", bg=self.bg, anchor="e", font=("Helvetica", 12)).grid(
            row=4, column=0, sticky="e"
        )
        tk.Label(display, textvariable=self.var_mode, bg=self.bg, anchor="e").grid(
            row=5, column=0, sticky="e"
        )

        self._build_science_panel()
        self._build_calc_panel()
        self._build_wind_panel()
        self.wind_frame.grid_remove()

    def _build_science_panel(self):
        frame = tk.LabelFrame(self.root, text="科学计算", bg=self.bg)
        frame.grid(row=2, column=0, sticky="we", padx=8, pady=(4, 8))

        buttons = [
            ("sin", lambda: self.append_function("sin(")),
            ("cos", lambda: self.append_function("cos(")),
            ("tan", lambda: self.append_function("tan(")),
            ("sqrt", lambda: self.append_function("sqrt(")),
            ("x^2", lambda: self.append_power(2)),
            ("pi", lambda: self.append_token("pi")),
            ("log", lambda: self.append_function("log(")),
            ("ln", lambda: self.append_function("ln(")),
            ("x^3", lambda: self.append_power(3)),
            ("1/x", lambda: self.append_function("inv(")),
            ("e", lambda: self.append_token("e")),
            ("Rad", self.toggle_angle_mode),
        ]

        for index, (text, command) in enumerate(buttons):
            row_index = index // 6
            column_index = index % 6
            frame.grid_columnconfigure(column_index, weight=1, uniform="science")
            frame.grid_rowconfigure(row_index, weight=1)
            button = self._build_main_button(frame, text=text, command=command)
            button.grid(row=row_index, column=column_index, padx=4, pady=4, sticky="nsew")
            if text == "Rad":
                self.rad_button = button

    def _build_calc_panel(self):
        frame = tk.LabelFrame(self.root, text="计算", bg=self.bg)
        frame.grid(row=3, column=0, sticky="we", padx=8, pady=(0, 8))

        buttons = [
            ("C", self.clear_expression),
            ("⌫", self.backspace),
            (":", self.append_time_separator),
            ("/", lambda: self.append_operator("/")),
            ("7", lambda: self.append_digit("7")),
            ("8", lambda: self.append_digit("8")),
            ("9", lambda: self.append_digit("9")),
            ("*", lambda: self.append_operator("*")),
            ("4", lambda: self.append_digit("4")),
            ("5", lambda: self.append_digit("5")),
            ("6", lambda: self.append_digit("6")),
            ("-", lambda: self.append_operator("-")),
            ("1", lambda: self.append_digit("1")),
            ("2", lambda: self.append_digit("2")),
            ("3", lambda: self.append_digit("3")),
            ("+", lambda: self.append_operator("+")),
            ("0", lambda: self.append_digit("0")),
            (".", lambda: self.append_digit(".")),
            ("=", self.evaluate_expression),
            ("(", lambda: self.append_token("(")),
            (")", lambda: self.append_token(")")),
        ]

        for index, (text, command) in enumerate(buttons):
            row_index = index // 4
            column_index = index % 4
            if text in ("(", ")"):
                row_index = 4
                column_index = 3 + (0 if text == "(" else 1)
            frame.grid_columnconfigure(column_index, weight=1, uniform="calc")
            frame.grid_rowconfigure(row_index, weight=1)
            button = self._build_main_button(frame, text=text, command=command)
            button.grid(row=row_index, column=column_index, padx=4, pady=4, sticky="nsew")

    def _build_wind_panel(self):
        self.wind_frame = tk.LabelFrame(self.root, text="风向角度", bg=self.bg)
        self.wind_frame.grid(row=4, column=0, sticky="we", padx=8, pady=(0, 8))

        labels = ["顺风", "逆风", "正左", "正右", "右前", "左前", "右后", "左后"]
        for index, label in enumerate(labels):
            row_index = index // 4
            column_index = index % 4
            self.wind_frame.grid_columnconfigure(column_index, weight=1, uniform="wind")
            self.wind_frame.grid_rowconfigure(row_index, weight=1)
            self._build_main_button(
                self.wind_frame,
                text=label,
                command=lambda current=label: self.apply_wind_angle(current),
                width=12,
            ).grid(row=row_index, column=column_index, padx=4, pady=4, sticky="nsew")

    def _build_main_button(self, parent, text, command, width=9):
        return tk.Button(
            parent,
            text=text,
            width=width,
            height=2,
            padx=10,
            pady=8,
            relief="raised",
            bd=1,
            highlightthickness=0,
            command=command,
        )

    def on_secret_click(self):
        self.secret_clicks += 1
        if self.secret_job is not None:
            self.root.after_cancel(self.secret_job)
        self.secret_job = self.root.after(self.SECRET_DELAY_MS, self.flush_secret_clicks)

    def flush_secret_clicks(self):
        count = self.secret_clicks
        self.secret_clicks = 0
        self.secret_job = None

        if count == 3:
            self.open_trig_dialog()
        elif count >= 4:
            self.toggle_wind_panel()

    def open_trig_dialog(self):
        if self.trig_dialog is not None and self.trig_dialog.window.winfo_exists():
            self.trig_dialog.focus()
            return
        self.trig_dialog = TrigCalculatorDialog(self.root, on_close=self.on_trig_dialog_closed)
        self.trig_dialog.focus()

    def on_trig_dialog_closed(self):
        self.trig_dialog = None
        self.restore_main_focus()

    def restore_main_focus(self):
        def _restore():
            try:
                if self.secret_button is not None and self.secret_button.winfo_exists():
                    self.secret_button.focus_set()
                elif self.result_label is not None and self.result_label.winfo_exists():
                    self.result_label.focus_set()
            except tk.TclError:
                return

        self.root.after_idle(_restore)

    def toggle_wind_panel(self):
        if self.wind_frame.winfo_viewable():
            self.wind_frame.grid_remove()
        else:
            self.wind_frame.grid()

    def toggle_angle_mode(self):
        self.angle_mode = "rad" if self.angle_mode == "deg" else "deg"
        self.var_mode.set(f"模式: {self.angle_mode.upper()}")
        self.rad_button.configure(text="Deg" if self.angle_mode == "rad" else "Rad")

    def clear_expression(self):
        self.expression = ""
        self.just_evaluated = False
        self.var_expression.set("")
        self.var_display.set("0")
        self.var_wind_info.set("")
        self.var_clock_hint.set("基准: 12点方向=0°，顺时针递增")

    def backspace(self):
        if self.just_evaluated:
            self.clear_expression()
            return
        self.expression = self.expression[:-1]
        self.var_expression.set(self.expression)
        self.var_display.set(self.expression or "0")

    def append_digit(self, value: str):
        self.prepare_for_input(reset_on_evaluated=True)
        self.expression += value
        self.refresh_expression_display()

    def append_token(self, token: str):
        self.prepare_for_input(reset_on_evaluated=token not in "+-*/)")
        self.expression += token
        self.refresh_expression_display()

    def append_operator(self, operator_text: str):
        if self.just_evaluated:
            self.expression = fmt(self.last_result)
            self.just_evaluated = False
        if not self.expression:
            self.expression = fmt(self.last_result)
        self.expression += operator_text
        self.refresh_expression_display()

    def append_time_separator(self):
        self.prepare_for_input(reset_on_evaluated=True)
        if ":" in self.expression:
            return
        if not self.expression:
            self.expression = "0"
        self.expression += ":"
        self.refresh_expression_display()

    def append_function(self, func_text: str):
        self.prepare_for_input(reset_on_evaluated=True)
        self.expression += func_text
        self.refresh_expression_display()

    def append_power(self, power: int):
        if self.just_evaluated and not self.expression:
            self.expression = fmt(self.last_result)
            self.just_evaluated = False
        if not self.expression:
            self.expression = "0"
        self.expression += f"**{power}"
        self.refresh_expression_display()

    def prepare_for_input(self, reset_on_evaluated: bool):
        if self.just_evaluated and reset_on_evaluated:
            self.expression = ""
            self.var_wind_info.set("")
            self.var_clock_hint.set("基准: 12点方向=0°，顺时针递增")
        self.just_evaluated = False

    def refresh_expression_display(self):
        self.var_expression.set(self.expression)
        self.var_display.set(self.expression or "0")

    def evaluate_expression(self):
        target = self.expression or self.var_display.get()
        if ":" in target:
            self.evaluate_clock_angle(target)
            return

        try:
            result = safe_eval(target, angle_mode=self.angle_mode)
        except Exception as exc:
            messagebox.showerror("错误", str(exc))
            return

        self.last_result = result
        self.just_evaluated = True
        self.expression = ""
        self.var_expression.set(f"{target} =")
        self.var_display.set(fmt(result))
        self.var_wind_info.set("")
        self.var_clock_hint.set("基准: 12点方向=0°，顺时针递增")

    def evaluate_clock_angle(self, target: str):
        try:
            hour_angle, minute_angle, included_angle = calc_clock_angle(target)
        except Exception as exc:
            messagebox.showerror("错误", str(exc))
            return

        self.last_result = included_angle
        self.just_evaluated = True
        self.expression = ""
        self.var_expression.set("")
        self.var_display.set(target.strip())
        self.var_wind_info.set(
            f"时针:{fmt_angle(hour_angle)}°  分针:{fmt_angle(minute_angle)}°  夹角:{fmt_angle(included_angle)}°"
        )
        self.var_clock_hint.set("文档规则: 12点方向=0°，按顺时针计算")

    def resolve_current_value(self):
        if self.just_evaluated and not self.expression:
            return self.last_result
        target = self.expression or self.var_display.get()
        return safe_eval(target, angle_mode=self.angle_mode)

    def apply_wind_angle(self, label: str):
        try:
            base_angle = normalize_angle(self.resolve_current_value())
        except Exception as exc:
            messagebox.showerror("错误", f"当前结果不能作为角度使用：{exc}")
            return

        result = normalize_angle(base_angle + self.wind_offsets[label])
        self.last_result = result
        self.just_evaluated = True
        self.expression = ""
        self.var_expression.set("")
        self.var_display.set(fmt(result))
        self.var_wind_info.set(f"风向:{fmt_angle(base_angle)}°  {label}:{fmt_angle(result)}°")
        self.var_clock_hint.set("基准: 12点方向=0°，顺时针递增")


def main():
    root = tk.Tk()
    WindClockCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
