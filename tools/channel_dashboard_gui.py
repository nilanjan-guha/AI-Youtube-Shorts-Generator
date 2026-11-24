"""ByteWave AI - YouTube Channel Analytics & Growth Diagnostic Desktop App.

Features:
- Modern dark-mode Desktop GUI (Tkinter + Canvas charts).
- Live Channel Stats: Subscribers, Total Views, Video Count.
- YPP Monetization Tracker (1K Subs / 10M Shorts Views progress bars).
- Video-by-Video Performance Breakdown:
    * Total Views, Likes, Comments per video
    * Pinpoints which video is going viral vs underperforming
    * Actionable AI recommendations on HOW to increase views and CTR
- Live Refresh & Auto Scan.
"""

import os
import sys
import os

# Allow imports from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pipeline import get_authenticated_service

TARGET_SUBS = 1000
TARGET_VIEWS = 10_000_000  # 10M for Shorts Monetization

# Color Scheme: Modern Dark YouTube Studio Palette
BG_DARK = "#0f0f12"
CARD_BG = "#1a1a24"
CARD_BORDER = "#2b2b3d"
ACCENT_RED = "#ff0033"
ACCENT_GREEN = "#00e676"
ACCENT_GOLD = "#ffd700"
ACCENT_BLUE = "#3d84ff"
TEXT_WHITE = "#ffffff"
TEXT_MUTED = "#9e9eb4"


class YouTubeStudioDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ByteWave AI — YouTube Channel Intelligence & Growth Studio")
        self.root.geometry("1100x780")
        self.root.minsize(980, 680)
        self.root.configure(bg=BG_DARK)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            background="#161622",
            foreground=TEXT_WHITE,
            fieldbackground="#161622",
            rowheight=32,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#232336",
            foreground=TEXT_WHITE,
            font=("Segoe UI", 10, "bold"),
            borderwidth=1,
            relief="flat",
        )
        self.style.map("Treeview", background=[("selected", "#3d84ff")])

        self._build_header()
        self._build_kpi_cards()
        self._build_monetization_bars()
        self._build_video_table_and_ai_panel()

        # Kick off background scan on startup
        self.start_scan_thread()

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg=BG_DARK, pady=12, padx=20)
        header_frame.pack(fill=tk.X)

        title_label = tk.Label(
            header_frame,
            text="🚀 YouTube Channel Growth & Monetization Studio",
            font=("Segoe UI", 18, "bold"),
            bg=BG_DARK,
            fg=TEXT_WHITE,
        )
        title_label.pack(side=tk.LEFT)

        self.btn_refresh = tk.Button(
            header_frame,
            text="🔄 Scan & Refresh Channel",
            font=("Segoe UI", 10, "bold"),
            bg=ACCENT_RED,
            fg=TEXT_WHITE,
            activebackground="#cc0029",
            activeforeground=TEXT_WHITE,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.start_scan_thread,
        )
        self.btn_refresh.pack(side=tk.RIGHT)

        self.status_lbl = tk.Label(
            header_frame,
            text="Initializing...",
            font=("Segoe UI", 9),
            bg=BG_DARK,
            fg=TEXT_MUTED,
            padx=10,
        )
        self.status_lbl.pack(side=tk.RIGHT)

    def _build_kpi_cards(self):
        cards_frame = tk.Frame(self.root, bg=BG_DARK, padx=20, pady=5)
        cards_frame.pack(fill=tk.X)

        for col in range(4):
            cards_frame.grid_columnconfigure(col, weight=1, uniform="card")

        self.card_subs = self._create_card(cards_frame, 0, "SUBSCRIBERS", "--", ACCENT_RED)
        self.card_views = self._create_card(cards_frame, 1, "TOTAL VIEWS", "--", ACCENT_BLUE)
        self.card_vids = self._create_card(cards_frame, 2, "VIDEOS UPLOADED", "--", ACCENT_GOLD)
        self.card_avg = self._create_card(cards_frame, 3, "AVG VIEWS / VIDEO", "--", ACCENT_GREEN)

    def _create_card(self, parent, col, title, initial_val, accent_color):
        card = tk.Frame(parent, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=12)
        card.grid(row=0, column=col, sticky="nsew", padx=6)

        t_lbl = tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=TEXT_MUTED)
        t_lbl.pack(anchor="w")

        v_lbl = tk.Label(card, text=initial_val, font=("Segoe UI", 20, "bold"), bg=CARD_BG, fg=accent_color)
        v_lbl.pack(anchor="w", pady=(4, 0))
        return v_lbl

    def _build_monetization_bars(self):
        progress_box = tk.Frame(self.root, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=20, pady=12)
        progress_box.pack(fill=tk.X, padx=26, pady=10)

        title = tk.Label(
            progress_box,
            text="🎯 YouTube Partner Program (YPP) Monetization Progress",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG,
            fg=TEXT_WHITE,
        )
        title.pack(anchor="w")

        # Subs progress
        self.subs_lbl_info = tk.Label(progress_box, text="Subscribers Goal (1,000 Subs): 0%", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_MUTED)
        self.subs_lbl_info.pack(anchor="w", pady=(6, 2))

        self.canvas_subs = tk.Canvas(progress_box, height=14, bg="#12121c", highlightthickness=0)
        self.canvas_subs.pack(fill=tk.X)

        # Views progress
        self.views_lbl_info = tk.Label(progress_box, text="Shorts Views Goal (10,000,000 Views): 0%", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_MUTED)
        self.views_lbl_info.pack(anchor="w", pady=(8, 2))

        self.canvas_views = tk.Canvas(progress_box, height=14, bg="#12121c", highlightthickness=0)
        self.canvas_views.pack(fill=tk.X)

    def _draw_progress_bar(self, canvas: tk.Canvas, percent: float, color: str):
        canvas.delete("all")
        w = canvas.winfo_width()
        if w <= 1:
            w = 1000
        fill_w = max(4, int(w * (min(100.0, percent) / 100.0)))
        canvas.create_rectangle(0, 0, fill_w, 14, fill=color, outline="")

    def _build_video_table_and_ai_panel(self):
        main_split = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=BG_DARK, sashwidth=6, bd=0)
        main_split.pack(fill=tk.BOTH, expand=True, padx=26, pady=(0, 16))

        # Left Side: Video performance list
        left_frame = tk.Frame(main_split, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1)
        main_split.add(left_frame, minsize=550)

        lbl_tbl = tk.Label(left_frame, text="📊 Individual Video Performance & Viral Scan", font=("Segoe UI", 11, "bold"), bg=CARD_BG, fg=TEXT_WHITE, padx=12, pady=10)
        lbl_tbl.pack(anchor="w")

        cols = ("Rank", "Title", "Views", "Likes", "Comments", "Status")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("Rank", text="#")
        self.tree.column("Rank", width=40, anchor="center")

        self.tree.heading("Title", text="Video Title")
        self.tree.column("Title", width=250, anchor="w")

        self.tree.heading("Views", text="Views")
        self.tree.column("Views", width=70, anchor="center")

        self.tree.heading("Likes", text="Likes")
        self.tree.column("Likes", width=60, anchor="center")

        self.tree.heading("Comments", text="Comments")
        self.tree.column("Comments", width=75, anchor="center")

        self.tree.heading("Status", text="Performance")
        self.tree.column("Status", width=100, anchor="center")

        scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 10))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))

        # Right Side: AI Growth Diagnostics & Recommendations
        right_frame = tk.Frame(main_split, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1, padx=16, pady=12)
        main_split.add(right_frame, minsize=380)

        lbl_ai = tk.Label(
            right_frame,
            text="💡 AI Growth Diagnostic & How to Increase Views",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG,
            fg=ACCENT_GOLD,
        )
        lbl_ai.pack(anchor="w", pady=(0, 8))

        self.ai_text = tk.Text(
            right_frame,
            bg="#13131c",
            fg=TEXT_WHITE,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            bd=0,
            padx=12,
            pady=12,
            relief="flat",
        )
        self.ai_text.pack(fill=tk.BOTH, expand=True)

    def start_scan_thread(self):
        self.btn_refresh.config(state=tk.DISABLED, text="Scanning...")
        self.status_lbl.config(text="Connecting to YouTube Data API...", fg=ACCENT_GOLD)
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            yt = get_authenticated_service()
            if not yt:
                self.root.after(0, lambda: self._show_error("Could not authenticate YouTube. Check client_secret.json / token.json."))
                return

            ch_resp = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()
            if not ch_resp.get("items"):
                self.root.after(0, lambda: self._show_error("No YouTube channel found for this authenticated Google account."))
                return

            channel = ch_resp["items"][0]
            ch_title = channel["snippet"]["title"]
            stats = channel["statistics"]

            subs = int(stats.get("subscriberCount", 0))
            views = int(stats.get("viewCount", 0))
            vids = int(stats.get("videoCount", 0))
            avg_views = (views / vids) if vids > 0 else 0

            # Fetch up to 50 uploads
            uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            pl_resp = yt.playlistItems().list(
                playlistId=uploads_playlist,
                part="snippet,contentDetails",
                maxResults=50,
            ).execute()

            video_items = pl_resp.get("items", [])
            vid_ids = [item["contentDetails"]["videoId"] for item in video_items if "contentDetails" in item]

            detailed_videos = []
            if vid_ids:
                vids_resp = yt.videos().list(
                    id=",".join(vid_ids),
                    part="snippet,statistics,contentDetails",
                ).execute()

                for v in vids_resp.get("items", []):
                    v_title = v["snippet"]["title"]
                    v_stats = v.get("statistics", {})
                    v_views = int(v_stats.get("viewCount", 0))
                    v_likes = int(v_stats.get("likeCount", 0))
                    v_comments = int(v_stats.get("commentCount", 0))

                    detailed_videos.append({
                        "id": v["id"],
                        "title": v_title,
                        "views": v_views,
                        "likes": v_likes,
                        "comments": v_comments,
                    })

            detailed_videos.sort(key=lambda x: x["views"], reverse=True)

            # Update UI on main thread
            self.root.after(
                0,
                lambda: self._update_gui(
                    ch_title, subs, views, vids, avg_views, detailed_videos
                ),
            )

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._show_error(f"Error fetching channel: {err_msg}"))

    def _update_gui(self, ch_title, subs, views, vids, avg_views, videos):
        self.btn_refresh.config(state=tk.NORMAL, text="🔄 Scan & Refresh Channel")
        self.status_lbl.config(
            text=f"Last updated: {datetime.now().strftime('%H:%M:%S')} ({ch_title})",
            fg=ACCENT_GREEN,
        )

        # Update KPI cards
        self.card_subs.config(text=f"{subs:,}")
        self.card_views.config(text=f"{views:,}")
        self.card_vids.config(text=f"{vids:,}")
        self.card_avg.config(text=f"{avg_views:,.1f}")

        # Monetization Progress
        sub_pct = min(100.0, (subs / TARGET_SUBS) * 100)
        view_pct = min(100.0, (views / TARGET_VIEWS) * 100)

        self.subs_lbl_info.config(
            text=f"Subscribers: {subs:,} / {TARGET_SUBS:,} ({sub_pct:.1f}% to YPP Monetization)"
        )
        self.views_lbl_info.config(
            text=f"Views: {views:,} / {TARGET_VIEWS:,} ({view_pct:.3f}% to 10M Shorts YPP)"
        )

        self._draw_progress_bar(self.canvas_subs, sub_pct, ACCENT_RED)
        self._draw_progress_bar(self.canvas_views, view_pct, ACCENT_BLUE)

        # Update Treeview table
        for row in self.tree.get_children():
            self.tree.delete(row)

        for idx, vid in enumerate(videos, 1):
            if vid["views"] >= 1000:
                status = "🔥 Viral"
            elif vid["views"] >= 200:
                status = "📈 Trending"
            elif vid["views"] >= 50:
                status = "👍 Steady"
            else:
                status = "⏳ Warming Up"

            self.tree.insert(
                "",
                "end",
                values=(
                    idx,
                    vid["title"],
                    f"{vid['views']:,}",
                    f"{vid['likes']:,}",
                    f"{vid['comments']:,}",
                    status,
                ),
            )

        # Generate intelligent growth diagnosis
        self._generate_growth_diagnosis(subs, views, vids, avg_views, videos)

    def _generate_growth_diagnosis(self, subs, views, vids, avg_views, videos):
        self.ai_text.delete("1.0", tk.END)

        diagnosis = []
        diagnosis.append("📋 CHANNEL HEALTH & ALGORITHM DIAGNOSTIC:\n")

        if vids == 0:
            diagnosis.append("• No videos detected on channel yet.\n")
            diagnosis.append("Action: Run `daily_runner.py` to publish your first batch of 3-4 viral shorts.\n\n")
        else:
            top_video = videos[0] if videos else None
            if top_video:
                diagnosis.append(f"🏆 Top Performing Video: '{top_video['title'][:45]}...'\n")
                diagnosis.append(f"   -> Views: {top_video['views']:,} | Likes: {top_video['likes']:,}\n\n")

            diagnosis.append(f"📊 Engagement Velocity:\n")
            diagnosis.append(f"   • Average Views: {avg_views:.1f} per video\n")

            if avg_views < 100:
                diagnosis.append("   ⚠️ Observation: Shorts are in the initial YouTube testing phase.\n\n")
            else:
                diagnosis.append("   ✅ Healthy traction. The algorithm is feeding your audience seed pool.\n\n")

        diagnosis.append("⚡ HOW TO INCREASE VIEWS & HIT 10M FASTER:\n")
        diagnosis.append("1. Upload Timing (Peak Shorts Feed Traffic):\n")
        diagnosis.append("   • Morning slot: 11:30 AM – 1:30 PM\n")
        diagnosis.append("   • Evening Prime: 6:00 PM – 9:30 PM (Highest viral surge)\n\n")
        diagnosis.append("2. Spacing Strategy:\n")
        diagnosis.append("   • Never upload 3 videos at the same minute.\n")
        diagnosis.append("   • Space each short by 2 to 3 hours so YouTube's algorithm doesn't throttle impression share.\n\n")
        diagnosis.append("3. High-CTR Hooks:\n")
        diagnosis.append("   • Use suspenseful first 2 seconds.\n")
        diagnosis.append("   • Ensure pinned provocative comments are active (already handled by auto_pilot.py).\n\n")
        diagnosis.append("4. Daily Cadence:\n")
        diagnosis.append("   • Keep `daily_runner.py` scheduled consistently. Channels posting 3-4 shorts daily hit 1,000 subscribers 5x faster.\n")

        self.ai_text.insert(tk.END, "".join(diagnosis))

    def _show_error(self, msg):
        self.btn_refresh.config(state=tk.NORMAL, text="🔄 Scan & Refresh Channel")
        self.status_lbl.config(text="Scan failed.", fg=ACCENT_RED)
        messagebox.showerror("YouTube Studio Error", msg)


def main():
    root = tk.Tk()
    app = YouTubeStudioDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

