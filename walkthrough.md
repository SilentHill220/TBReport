# Debugging UI Data Display Workflows

## Goal
Fix the issue where "Personal Achievement" data on the dashboard was incomplete. Specifically, the user expected to see ~11 historical contributions for "韩嵩洋", but only saw 6 or 7, and the stats were inconsistent with the list.

## Diagnostics

1.  **Frontend Truncation:**
    *   Found `dashboard.html` was explicitly slicing the history list: `doneT.slice(-10)`.
    *   **Fix:** Removed `.slice(-10)` to allow full history display.

2.  **Frontend Data Source:**
    *   Found `dashboard.html` was calculating "Completed Tasks" stats and the "Battle History" list from `uData.tasks` (Current Assignments).
    *   This ignored historical credits (tasks completed by the user but now assigned to someone else, e.g., QA).
    *   **Fix:** Updated `dashboard.html` to source "Battle History" and Stats directly from the global `recent_wins` list, filtered by user.

3.  **Backend Filtering:**
    *   Even after frontend fixes, `summary.json` only contained 6 wins for "韩嵩洋".
    *   Found `task_analyzer.py` had a logic to **filter out wins older than 7 days** and limit the total list to 200 items.
    *   This caused valid, older achievements (like "怪物攻击前统一添加闪白效果") to be dropped.
    *   **Fix:** Removed the 7-day date filter and increased the total limit to 5000 items.

## Verification

### Data Count Check
Executed python script to count wins for "韩嵩洋" in `summary.json`:

**Before Fix:**
```
Count: 6
['场景地面扰动效果', '重构拆分环境天气效果'...]
```

**After Fix (Backend + Frontend):**
```
Count: 11
['场景地面扰动效果', '重构拆分环境天气效果', '优化英雄展示界面',
 '伤害受击爆点', '伤害类型属性变化', '爆点角度相关内容迁移至配表', 
 '命中怪物震屏', '热扭曲效果', '远程武器瞄准问题', '怪物血条去除', 
 '怪物攻击前统一添加闪白效果-前端效果实现']
```

### UI Verification
*   **List:** Now displays all 11 items.
*   **Stats:** "Completed Tasks" count now displays **11** (matching the list).
*   **Consistency:** The list and stats use the same source of truth (`recent_wins`).

## Files Modified
*   `h:\projects\TBData\templates\dashboard.html`: Updated rendering logic.
*   `h:\projects\TBData\task_analyzer.py`: Removed date filter and increased limits.
