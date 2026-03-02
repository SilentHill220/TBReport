"""
Table to Image Renderer - Premium Black Gold Card Design
Renders task report as a luxurious black-gold card for DingTalk.
"""
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class TableImageRenderer:
    """Render task report as a premium black-gold card."""
    
    # Luxurious black-gold color scheme
    COLORS = {
        'bg': '#0a0a0a',           # Deep black
        'card': '#121212',          # Rich black
        'gold': '#d4af37',          # Classic gold
        'gold_light': '#f4d03f',    # Bright gold
        'gold_dark': '#b8860b',     # Dark gold
        'border': '#c9a227',        # Gold border
        'text': '#ffffff',          # White text
        'text_gold': '#d4af37',     # Gold text
        'muted': '#888888',         # Muted gray
        'row_alt': '#1a1a1a',       # Alternating row
        'accent_red': '#ff6b6b',    # Urgent red
        'accent_orange': '#ffa500', # Warning orange
    }
    
    def __init__(self, output_dir: str = "./data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def render_task_report(
        self, 
        summary: Dict, 
        user_roles: Dict[str, str] = None,
        dashboard_url: str = None,
        switches: Dict[str, bool] = None
    ) -> Tuple[Optional[str], List[Dict]]:
        """Render task summary as a premium black-gold card."""
        if not HAS_MATPLOTLIB:
            print("matplotlib not installed. Run: pip install matplotlib")
            return None, []
        
        user_roles = user_roles or {}
        switches = switches or {}
        
        all_tasks = self._collect_tasks(summary, user_roles)
        
        if not all_tasks:
            print("No tasks to render")
            return None, all_tasks
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"report_{timestamp}.png")
        
        try:
            self._render_premium_card(summary, all_tasks, output_path)
            print(f"Report image generated: {output_path}")
            return output_path, all_tasks
        except Exception as e:
            print(f"Failed to render image: {e}")
            import traceback
            traceback.print_exc()
            return None, all_tasks
    
    def _collect_tasks(self, summary: Dict, user_roles: Dict[str, str]) -> List[Dict]:
        """Collect active tasks."""
        urgent, dev, design = [], [], []
        
        for user, data in summary.get('by_user', {}).items():
            role = user_roles.get(user, '其他')
            for t in data.get('tasks', []):
                status = t.get('status', '')
                priority = t.get('priority', '')
                
                is_urgent = priority in ['紧急', '非常紧急', 'Urgent', 'Very Urgent']
                is_active = status in ['进行中', 'In Progress', 'Doing']
                is_done = status in ['已完成', '关闭', '已关闭', 'Done', 'Closed']
                is_overdue = t.get('is_overdue', False)
                
                if is_done or (not is_active and not is_overdue and not is_urgent):
                    continue
                
                task = {
                    'executor': user,
                    'title': t.get('title', '')[:24] + ('...' if len(t.get('title', '')) > 24 else ''),
                    'due': (t.get('due', '') or '')[:10],
                    'is_urgent': is_urgent,
                    'is_overdue': is_overdue,
                    'task_id': t.get('id'),
                }
                
                if is_urgent:
                    urgent.append(task)
                elif role in ['客户端', '服务端']:
                    dev.append(task)
                else:
                    design.append(task)
        
        return urgent + dev + design
    
    def _render_premium_card(self, summary: Dict, tasks: List[Dict], output_path: str):
        """Render premium black-gold card."""
        num_tasks = len(tasks)
        fig_width = 5.5
        fig_height = max(2.8, 1.4 + num_tasks * 0.38)
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        fig.patch.set_facecolor(self.COLORS['bg'])
        ax.set_facecolor(self.COLORS['card'])
        ax.set_xlim(0, 10)
        ax.set_ylim(0, num_tasks + 2.8)
        ax.axis('off')
        
        # Premium card with gold border
        outer_border = FancyBboxPatch((0.15, 0.15), 9.7, num_tasks + 2.5,
                                       boxstyle="round,pad=0.02,rounding_size=0.15",
                                       facecolor='none',
                                       edgecolor=self.COLORS['gold'],
                                       linewidth=2.5)
        ax.add_patch(outer_border)
        
        # Inner card
        inner_card = FancyBboxPatch((0.25, 0.25), 9.5, num_tasks + 2.3,
                                     boxstyle="round,pad=0.02,rounding_size=0.12",
                                     facecolor=self.COLORS['card'],
                                     edgecolor=self.COLORS['gold_dark'],
                                     linewidth=1)
        ax.add_patch(inner_card)
        
        # Premium title with decorative elements
        date_str = summary.get('updated_at', '')[:10]
        y_title = num_tasks + 2.1
        
        # Decorative lines
        ax.plot([1.5, 3.8], [y_title, y_title], color=self.COLORS['gold'], linewidth=1, alpha=0.6)
        ax.plot([6.2, 8.5], [y_title, y_title], color=self.COLORS['gold'], linewidth=1, alpha=0.6)
        
        # Title
        ax.text(5, y_title, "TASK REPORT", 
                ha='center', va='center', fontsize=14, fontweight='bold',
                color=self.COLORS['gold_light'], fontfamily='Arial',
                style='italic')
        
        # Subtitle with date
        ax.text(5, y_title - 0.4, date_str,
                ha='center', va='center', fontsize=9,
                color=self.COLORS['muted'], fontfamily='Microsoft YaHei')
        
        # Gold header bar
        y_header = num_tasks + 1.15
        header_bar = Rectangle((0.5, y_header - 0.22), 9.0, 0.44,
                                facecolor=self.COLORS['gold_dark'],
                                edgecolor='none', alpha=0.25)
        ax.add_patch(header_bar)
        
        # Column headers
        col_x = [0.7, 1.8, 5.2]
        headers = ['NO.', 'OWNER', 'TASK']
        
        for x, h in zip(col_x, headers):
            ax.text(x, y_header, h, ha='left', va='center',
                    fontsize=9, fontweight='bold', color=self.COLORS['gold'],
                    fontfamily='Arial')
        
        # Task rows
        for i, task in enumerate(tasks):
            y = num_tasks - i + 0.45
            
            # Alternating row background with subtle gold tint
            if i % 2 == 1:
                row_bg = Rectangle((0.5, y - 0.28), 9.0, 0.56,
                                    facecolor=self.COLORS['row_alt'], 
                                    edgecolor='none', alpha=0.8)
                ax.add_patch(row_bg)
            
            # Row number with gold accent
            ax.text(col_x[0], y, f"{i + 1:02d}", ha='left', va='center',
                    fontsize=9, color=self.COLORS['gold_dark'], 
                    fontweight='bold', fontfamily='Arial')
            
            # Executor with status color
            if task['is_urgent']:
                name_color = self.COLORS['accent_red']
                name_prefix = "! "
            elif task['is_overdue']:
                name_color = self.COLORS['accent_orange']
                name_prefix = "! "
            else:
                name_color = self.COLORS['gold_light']
                name_prefix = ""
            
            ax.text(col_x[1], y, name_prefix + task['executor'][:4], ha='left', va='center',
                    fontsize=10, fontweight='bold', color=name_color, 
                    fontfamily='Microsoft YaHei')
            
            # Task title
            ax.text(col_x[2], y, task['title'], ha='left', va='center',
                    fontsize=9, color=self.COLORS['text'], 
                    fontfamily='Microsoft YaHei', alpha=0.9)
        
        # Footer with gold accent
        ax.plot([2, 8], [0.55, 0.55], color=self.COLORS['gold'], linewidth=0.5, alpha=0.4)
        ax.text(5, 0.35, f"{len(tasks)} TASKS IN PROGRESS",
                ha='center', va='center', fontsize=8,
                color=self.COLORS['gold_dark'], fontfamily='Arial',
                style='italic')
        
        plt.tight_layout(pad=0.2)
        plt.savefig(output_path, dpi=180, facecolor=fig.get_facecolor(),
                    edgecolor='none', bbox_inches='tight', pad_inches=0.08)
        plt.close(fig)


def render_and_upload(
    summary: Dict,
    user_roles: Dict[str, str],
    imgbb_api_key: str,
    dashboard_url: str = None,
    switches: Dict[str, bool] = None,
    output_dir: str = "./data"
) -> Tuple[Optional[str], List[Dict]]:
    """Render and upload to ImgBB."""
    from dingtalk_sender import ImgBBUploader
    
    renderer = TableImageRenderer(output_dir)
    image_path, task_list = renderer.render_task_report(summary, user_roles, dashboard_url, switches)
    
    if not image_path:
        return None, task_list
    
    uploader = ImgBBUploader(imgbb_api_key)
    url = uploader.upload_image(image_path, name=f"report_{datetime.now().strftime('%Y%m%d')}")
    
    return url, task_list
