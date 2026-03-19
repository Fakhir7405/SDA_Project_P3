import tkinter as tk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from functools import reduce
import time

# Colour Palette
BG_DARK      = "#0d1117"
BG_CARD      = "#161b22"
BG_HEADER    = "#010409"
BORDER       = "#30363d"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED   = "#8b949e"
TEXT_GREEN   = "#3fb950"
TEXT_BLUE    = "#58a6ff"
TEXT_PURPLE  = "#bc8cff"
TEXT_ORANGE  = "#d29922"
ACCENT_GREEN = "#238636"
ACCENT_BLUE  = "#1f6feb"
ACCENT_RED   = "#da3633"
ACCENT_YELLOW= "#9e6a03"


class DashboardGUI:
   
   # Dark theme dashboard.
   

    def __init__(self, raw_q, verified_q, processed_q, max_size,
                 raw_count, verified_count, processed_count, config):

        self.raw_q           = raw_q
        self.verified_q      = verified_q
        self.processed_q     = processed_q
        self.max_size        = max_size
        self.raw_count       = raw_count
        self.verified_count  = verified_count
        self.processed_count = processed_count

        vis        = config.get("visualizations", {})
        tel_cfg    = vis.get("telemetry", {})
        charts_cfg = vis.get("data_charts", [])

        self.show_raw       = tel_cfg.get("show_raw_stream",          True)
        self.show_verified  = tel_cfg.get("show_intermediate_stream", True)
        self.show_processed = tel_cfg.get("show_processed_stream",    True)

        self.title_values  = "Live Sensor Values (Authentic Only)"
        self.xlabel_values = "time_period"
        self.ylabel_values = "metric_value"
        self.title_avg     = "Live Sensor Running Average"
        self.xlabel_avg    = "time_period"
        self.ylabel_avg    = "computed_metric"

      

        val_charts = list(filter(
            lambda c: c.get("type") == "real_time_line_graph_values", charts_cfg))
        avg_charts = list(filter(
            lambda c: c.get("type") == "real_time_line_graph_average", charts_cfg))

        if val_charts:
            self.title_values  = val_charts[0].get("title",  self.title_values)
            self.xlabel_values = val_charts[0].get("x_axis", self.xlabel_values)
            self.ylabel_values = val_charts[0].get("y_axis", self.ylabel_values)

        if avg_charts:
            self.title_avg  = avg_charts[0].get("title",  self.title_avg)
            self.xlabel_avg = avg_charts[0].get("x_axis", self.xlabel_avg)
            self.ylabel_avg = avg_charts[0].get("y_axis", self.ylabel_avg)

        self.x_ticks      = []
        self.values       = []
        self.avgs         = []
        self.MAX_POINTS   = 60
        self._telemetry_state = {}
        self._start_time  = time.time()

        #Root window
        self.root = tk.Tk()
        self.root.title("Real-Time Pipeline Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG_DARK)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.resizable(True, True)

        self._build_header()
        self._build_stat_bar()
        self._build_main_area()

    #Header

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_HEADER, height=50)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=BG_HEADER)
        left.pack(side="left", padx=20)

        tk.Label(left, text="⬡", fg=TEXT_BLUE, bg=BG_HEADER,
                 font=("Consolas", 18, "bold")).pack(side="left", padx=(0, 8))
        tk.Label(left, text="Pipeline", fg=TEXT_PRIMARY, bg=BG_HEADER,
                 font=("Consolas", 14, "bold")).pack(side="left")
        tk.Label(left, text=" Monitor", fg=TEXT_BLUE, bg=BG_HEADER,
                 font=("Consolas", 14)).pack(side="left")

        right = tk.Frame(header, bg=BG_HEADER)
        right.pack(side="right", padx=20)

        badge = tk.Frame(right, bg="#1a2f1a")
        badge.pack(side="right", padx=(10, 0))
        tk.Label(badge, text=" ● LIVE ", fg=TEXT_GREEN, bg="#1a2f1a",
                 font=("Consolas", 9, "bold")).pack(padx=4, pady=3)

        self.lbl_clock = tk.Label(right, text="00:00:00",
                                  fg=TEXT_MUTED, bg=BG_HEADER,
                                  font=("Consolas", 11))
        self.lbl_clock.pack(side="right", padx=(0, 8))

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    # Stat Bar

    def _build_stat_bar(self):
        bar = tk.Frame(self.root, bg=BG_DARK)
        bar.pack(fill="x", padx=16, pady=(10, 0))

        stats = [
            ("Total Ingested",  "0",  TEXT_PURPLE, "stat_ingested"),
            ("Total Verified",  "0",  TEXT_GREEN,  "stat_verified"),
            ("Total Processed", "0",  TEXT_BLUE,   "stat_processed"),
            ("Drop Rate",       "0%", TEXT_ORANGE, "stat_droprate"),
        ]


        def build_stat_card(item):
            label, value, color, attr = item
            card = tk.Frame(bar, bg=BG_CARD,
                            highlightbackground=BORDER,
                            highlightthickness=1)
            card.pack(side="left", expand=True, fill="x", padx=(0, 8))
            tk.Label(card, text=label, fg=TEXT_MUTED, bg=BG_CARD,
                     font=("Consolas", 9)).pack(anchor="w", padx=10, pady=(6, 0))
            val_lbl = tk.Label(card, text=value, fg=color, bg=BG_CARD,
                               font=("Consolas", 20, "bold"))
            val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
            setattr(self, attr, val_lbl)

        list(map(build_stat_card, stats))

    # Main Area

    def _build_main_area(self):
        outer = tk.Frame(self.root, bg=BG_DARK)
        outer.pack(fill="both", expand=True, padx=16, pady=10)

        top_row = tk.Frame(outer, bg=BG_DARK)
        top_row.pack(fill="x", expand=False)

        charts_col = tk.Frame(top_row, bg=BG_DARK)
        charts_col.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self._build_chart(charts_col,
                          title=self.title_values,
                          subtitle=f"y: {self.ylabel_values}  |  x: {self.xlabel_values}",
                          line_color="#3fb950",
                          fig_attr="fig1", ax_attr="ax1", line_attr="line1")

        self._build_chart(charts_col,
                          title=self.title_avg,
                          subtitle=f"y: {self.ylabel_avg}  |  x: {self.xlabel_avg}",
                          line_color="#58a6ff",
                          fig_attr="fig2", ax_attr="ax2", line_attr="line2")

        tel_col = tk.Frame(top_row, bg=BG_DARK, width=280)
        tel_col.pack(side="right", fill="y")
        tel_col.pack_propagate(False)
        self._build_telemetry_panel(tel_col)

    # Chart

    def _build_chart(self, parent, title, subtitle, line_color,
                     fig_attr, ax_attr, line_attr):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        hdr = tk.Frame(card, bg=BG_CARD)
        hdr.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(hdr, text=title, fg=TEXT_PRIMARY, bg=BG_CARD,
                 font=("Consolas", 10, "bold")).pack(side="left")
        tk.Label(hdr, text=subtitle, fg=TEXT_MUTED, bg=BG_CARD,
                 font=("Consolas", 8)).pack(side="right")

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(6, 0))

        fig = Figure(figsize=(7, 2.4), dpi=96, facecolor=BG_CARD)
        ax  = fig.add_subplot(111)
        self._style_axes(ax)
        line, = ax.plot([], [], color=line_color, linewidth=1.8)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill="x", padx=4, pady=(2, 6))
        canvas.draw()

        setattr(self, fig_attr,  fig)
        setattr(self, ax_attr,   ax)
        setattr(self, line_attr, line)

    #Telemetry Panel 

    def _build_telemetry_panel(self, parent):
        tk.Label(parent, text="Pipeline Telemetry",
                 fg=TEXT_PRIMARY, bg=BG_DARK,
                 font=("Consolas", 12, "bold")).pack(anchor="w", pady=(0, 8))

        self.raw_bar  = self._build_queue_card(
            parent, "Raw Queue", "input → core", TEXT_PURPLE) if self.show_raw else None
        self.ver_bar  = self._build_queue_card(
            parent, "Verified Queue", "core → aggregator", TEXT_GREEN) if self.show_verified else None
        self.proc_bar = self._build_queue_card(
            parent, "Processed Queue", "aggregator → GUI", TEXT_BLUE) if self.show_processed else None

        leg = tk.Frame(parent, bg=BG_CARD,
                       highlightbackground=BORDER, highlightthickness=1)
        leg.pack(fill="x")
        tk.Label(leg, text="Backpressure Legend",
                 fg=TEXT_MUTED, bg=BG_CARD,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        tk.Frame(leg, bg=BORDER, height=1).pack(fill="x")

      
        legend_items = [
            ("●", "Low     < 30%", TEXT_GREEN),
            ("●", "Medium  < 70%", TEXT_ORANGE),
            ("●", "High   >= 70%", "#f85149"),
        ]

        def build_legend_row(item):
            dot, label, color = item
            row = tk.Frame(leg, bg=BG_CARD)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=dot, fg=color, bg=BG_CARD,
                     font=("Consolas", 10)).pack(side="left", padx=(0, 6))
            tk.Label(row, text=label, fg=TEXT_MUTED, bg=BG_CARD,
                     font=("Consolas", 9)).pack(side="left")

        list(map(build_legend_row, legend_items))
        tk.Frame(leg, bg=BG_CARD, height=4).pack()

    # Queue Card

    def _build_queue_card(self, parent, title, subtitle, accent):
        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        top = tk.Frame(card, bg=BG_CARD)
        top.pack(fill="x", padx=10, pady=(8, 2))
        tk.Label(top, text=title, fg=TEXT_PRIMARY, bg=BG_CARD,
                 font=("Consolas", 10, "bold")).pack(side="left")
        pct = tk.Label(top, text="0%", fg=accent, bg=BG_CARD,
                       font=("Consolas", 10, "bold"))
        pct.pack(side="right")

        tk.Label(card, text=subtitle, fg=TEXT_MUTED, bg=BG_CARD,
                 font=("Consolas", 8)).pack(anchor="w", padx=10)

        track = tk.Canvas(card, height=8, bg="#21262d", highlightthickness=0)
        track.pack(fill="x", padx=10, pady=(4, 10))
        bar = track.create_rectangle(0, 0, 0, 8, fill=accent, outline="")

        return (track, bar, pct, accent)

    # Observer

    def update(self, state):
        #To update latest telemetry data.
        self._telemetry_state = state

    #Matplotlib

    def _style_axes(self, ax):
        ax.set_facecolor(BG_DARK)
        ax.tick_params(colors=TEXT_MUTED, labelsize=7)
        ax.spines["bottom"].set_color(BORDER)
        ax.spines["left"].set_color(BORDER)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color="#1e293b", linewidth=0.6, linestyle="--", alpha=0.8)

    def _redraw_chart(self, fig, ax, line, x_data, y_data):
        if len(y_data) < 2:
            return
        line.set_xdata(x_data)
        line.set_ydata(y_data)
        ax.relim()
        ax.autoscale_view()
        fig.tight_layout(pad=0.4)
        try:
            fig.canvas.draw_idle()
        except Exception:
            pass

    #Queue bar

    def _update_queue_bar(self, bar, value):
        if bar is None:
            return
        track, rect, pct, accent = bar
        ratio  = value / self.max_size if self.max_size > 0 else 0
        w      = track.winfo_width() or 240
        fill_w = max(0, int(ratio * w))
        color  = "#238636" if ratio < 0.3 else ("#9e6a03" if ratio < 0.7 else "#da3633")
        track.coords(rect, 0, 0, fill_w, 8)
        track.itemconfig(rect, fill=color)
        pct.config(text=f"{int(ratio*100)}%", fg=color)

    # Drain processed queue

    def _drain_processed_queue(self):
        # This function takes up to 10 items from the processed queue and add their values to the dashboard lists.
# It keeps the lists from getting too long by removing the old items.
        def drain_one(remaining):
            if remaining <= 0:
                return
            try:
                data = self.processed_q.get_nowait()
                val  = data.get("metric_value",    0.0)
                avg  = data.get("computed_metric", 0.0)
                t    = data.get("time_period",     len(self.x_ticks))

                self.x_ticks.append(t)
                self.values.append(val)
                self.avgs.append(avg)

                if len(self.x_ticks) > self.MAX_POINTS:
                    self.x_ticks.pop(0)
                    self.values.pop(0)
                    self.avgs.pop(0)

                drain_one(remaining - 1)
            except Exception:
                pass

        drain_one(10)

    #Stats + clock

    def _apply_telemetry(self):
        if not self._telemetry_state:
            return
        s = self._telemetry_state
        self._update_queue_bar(self.raw_bar,  s.get("raw_size",       0))
        self._update_queue_bar(self.ver_bar,  s.get("verified_size",  0))
        self._update_queue_bar(self.proc_bar, s.get("processed_size", 0))

    def _refresh_stats(self):
        ingested  = self.raw_count.value
        verified  = self.verified_count.value
        processed = self.processed_count.value
        drop_rate = round((ingested - verified) / ingested * 100, 1) if ingested > 0 else 0
        self.stat_ingested.config( text=str(ingested))
        self.stat_verified.config( text=str(verified))
        self.stat_processed.config(text=str(processed))
        self.stat_droprate.config( text=f"{drop_rate}%")

    def _refresh_clock(self):
        e = int(time.time() - self._start_time)
        t = f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"
        self.lbl_clock.config(text=t)

    # Update cycle

    def _update_cycle(self):
        self._apply_telemetry()
        self._drain_processed_queue()
        self._refresh_stats()
        self._refresh_clock()
        self._redraw_chart(self.fig1, self.ax1, self.line1, self.x_ticks, self.values)
        self._redraw_chart(self.fig2, self.ax2, self.line2, self.x_ticks, self.avgs)
        self.root.after(200, self._update_cycle)

    def _on_close(self):
        try:
            self.root.quit()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self._update_cycle()
        self.root.mainloop()