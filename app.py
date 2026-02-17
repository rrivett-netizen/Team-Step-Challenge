"""
Step Tracking Bot - Web App
A Streamlit web application for tracking daily steps with multi-user support
"""

import streamlit as st
import json
import os
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict


class StepTrackerDB:
    """Database handler for step tracking with multi-user support"""
    
    def __init__(self, data_file: str = "step_data.json"):
        self.data_file = data_file
        self.data = self.load_data()
    
    def load_data(self) -> Dict:
        """Load data from JSON file"""
        default = {
            "users": {},
            "challenge": {
                "active": False,
                "team_goal": 0,
                "start_date": None,
                "end_date": None
            },
            "weekly_goal": {"goal": 0, "week_start": None},
            "admin_message": ""
        }
        if os.path.exists(self.data_file):
            data = json.load(open(self.data_file, 'r'))
            if "challenge" not in data:
                data["challenge"] = default["challenge"]
            if "weekly_goal" not in data:
                data["weekly_goal"] = default["weekly_goal"]
            if "admin_message" not in data:
                data["admin_message"] = default["admin_message"]
            return data
        return default
    
    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, indent=2, fp=f)
    
    def get_user_data(self, username: str) -> Dict:
        """Get data for a specific user"""
        if username not in self.data["users"]:
            self.data["users"][username] = {
                "daily_goal": 10000,
                "history": {}
            }
            self.save_data()
        return self.data["users"][username]
    
    def set_goal(self, username: str, goal: int):
        """Set daily goal for user"""
        user_data = self.get_user_data(username)
        user_data["daily_goal"] = goal
        self.save_data()
    
    def log_steps(self, username: str, steps: int, log_date: str):
        """Log steps for user on specific date"""
        user_data = self.get_user_data(username)
        user_data["history"][log_date] = steps
        self.save_data()
    
    def get_all_usernames(self):
        """Get list of all usernames"""
        return list(self.data["users"].keys())

    def get_challenge(self) -> Dict:
        """Get current challenge settings"""
        c = self.data.get("challenge", {
            "active": False,
            "team_goal": 0,
            "start_date": None,
            "end_date": None,
            "target_end_date": None
        })
        if "target_end_date" not in c:
            c["target_end_date"] = None
        return c

    def set_challenge(self, team_goal: int, start_date: str, target_end_date: str = None):
        """Start a new challenge with team goal, start date, and optional target end date"""
        self.data["challenge"] = {
            "active": True,
            "team_goal": team_goal,
            "start_date": start_date,
            "end_date": None,
            "target_end_date": target_end_date
        }
        self.save_data()

    def end_challenge(self, end_date: str):
        """End the challenge (data stays; challenge marked inactive)"""
        c = self.data["challenge"]
        c["active"] = False
        c["end_date"] = end_date
        self.save_data()

    def get_team_steps_in_challenge(self) -> int:
        """Sum all team steps from challenge start to end (or today)."""
        c = self.get_challenge()
        start = c.get("start_date")
        end = c.get("end_date") or date.today().isoformat()
        if not start:
            return 0
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        total = 0
        for username in self.get_all_usernames():
            user_data = self.get_user_data(username)
            for log_date_str, steps in user_data.get("history", {}).items():
                try:
                    d = date.fromisoformat(log_date_str)
                    if start_d <= d <= end_d:
                        total += steps
                except ValueError:
                    pass
        return total

    def get_admin_message(self) -> str:
        """Get the admin announcement message"""
        return self.data.get("admin_message", "")

    def set_admin_message(self, text: str):
        """Set the admin announcement message"""
        self.data["admin_message"] = (text or "").strip()
        self.save_data()

    def get_weekly_goal(self) -> Dict:
        """Get current weekly team goal (goal number and week it applies to)."""
        return self.data.get("weekly_goal", {"goal": 0, "week_start": None})

    def set_weekly_goal(self, goal: int):
        """Set team goal for the current week (week = Monday–Sunday)."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        self.data["weekly_goal"] = {"goal": goal, "week_start": week_start.isoformat()}
        self.save_data()

    def get_team_steps_this_week(self) -> int:
        """Sum all team steps from Monday of current week through today."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        total = 0
        for username in self.get_all_usernames():
            user_data = self.get_user_data(username)
            for log_date_str, steps in user_data.get("history", {}).items():
                try:
                    d = date.fromisoformat(log_date_str)
                    if week_start <= d <= today:
                        total += steps
                except ValueError:
                    pass
        return total

    def get_all_steps_for_export(self):
        """Return list of all step entries for CSV/table: [{date, user, steps, daily_goal}, ...]"""
        rows = []
        for username in self.get_all_usernames():
            user_data = self.get_user_data(username)
            goal = user_data.get("daily_goal", 10000)
            for log_date_str, steps in user_data.get("history", {}).items():
                rows.append({
                    "Date": log_date_str,
                    "User": username,
                    "Steps": steps,
                    "Daily Goal": goal
                })
        return sorted(rows, key=lambda r: (r["Date"], r["User"]))

    def load_from_backup(self, data_dict: Dict):
        """Replace all data with backup (e.g. from uploaded JSON). Keeps data until you delete it."""
        if "users" in data_dict:
            self.data["users"] = data_dict["users"]
        if "challenge" in data_dict:
            self.data["challenge"] = data_dict["challenge"]
        if "weekly_goal" in data_dict:
            self.data["weekly_goal"] = data_dict["weekly_goal"]
        if "admin_message" in data_dict:
            self.data["admin_message"] = data_dict["admin_message"]
        self.save_data()


def init_session_state():
    """Initialize session state variables"""
    if 'db' not in st.session_state:
        st.session_state.db = StepTrackerDB()
    if 'username' not in st.session_state:
        st.session_state.username = None


def create_progress_chart(steps: int, goal: int):
    """Create a circular progress gauge"""
    percentage = min((steps / goal) * 100, 100) if goal > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=steps,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Today's Steps", 'font': {'size': 24}},
        delta={'reference': goal, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [None, goal * 1.2], 'tickformat': ','},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, goal * 0.5], 'color': "lightgray"},
                {'range': [goal * 0.5, goal], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': goal
            }
        }
    ))
    
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def create_history_chart(history: Dict, goal: int, days: int = 14):
    """Create a bar chart of step history"""
    if not history:
        return None
    
    # Get last N days
    sorted_dates = sorted(history.keys(), reverse=True)[:days]
    sorted_dates.reverse()  # Show oldest to newest
    
    df = pd.DataFrame({
        'Date': sorted_dates,
        'Steps': [history[d] for d in sorted_dates],
        'Goal': [goal] * len(sorted_dates)
    })
    
    fig = go.Figure()
    
    # Add bars for steps
    fig.add_trace(go.Bar(
        x=df['Date'],
        y=df['Steps'],
        name='Steps',
        marker_color=['green' if steps >= goal else 'lightblue' 
                      for steps in df['Steps']]
    ))
    
    # Add goal line
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Goal'],
        name='Goal',
        mode='lines',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title="Step History",
        xaxis_title="Date",
        yaxis_title="Steps",
        height=400,
        hovermode='x unified'
    )
    
    return fig


def create_team_leaderboard(db: StepTrackerDB, period: str = "today"):
    """Create team leaderboard"""
    leaderboard_data = []
    
    if period == "today":
        target_date = date.today().isoformat()
    else:  # week
        target_date = None
    
    for username in db.get_all_usernames():
        user_data = db.get_user_data(username)
        
        if period == "today":
            steps = user_data["history"].get(target_date, 0)
        else:  # week
            # Sum last 7 days
            steps = 0
            for i in range(7):
                check_date = (date.today() - timedelta(days=i)).isoformat()
                steps += user_data["history"].get(check_date, 0)
        
        goal = user_data["daily_goal"]
        if period == "week":
            goal = goal * 7
        
        leaderboard_data.append({
            'User': username,
            'Steps': steps,
            'Goal': goal,
            'Progress': f"{(steps/goal*100):.1f}%" if goal > 0 else "0%"
        })
    
    # Sort by steps
    leaderboard_data.sort(key=lambda x: x['Steps'], reverse=True)
    
    return pd.DataFrame(leaderboard_data)


def create_team_progress_chart(db: StepTrackerDB, days: int = 7):
    """Create team progress chart over time"""
    team_data = []
    
    for i in range(days - 1, -1, -1):
        check_date = (date.today() - timedelta(days=i)).isoformat()
        daily_total = 0
        
        for username in db.get_all_usernames():
            user_data = db.get_user_data(username)
            daily_total += user_data["history"].get(check_date, 0)
        
        team_data.append({
            'Date': check_date,
            'Total Steps': daily_total
        })
    
    df = pd.DataFrame(team_data)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df['Total Steps'],
        mode='lines+markers',
        name='Team Steps',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.2)'
    ))
    
    fig.update_layout(
        title=f"Team Progress - Last {days} Days",
        xaxis_title="Date",
        yaxis_title="Total Team Steps",
        height=350,
        hovermode='x unified'
    )
    
    return fig


def create_team_contribution_chart(db: StepTrackerDB, period: str = "week"):
    """Create pie chart showing each member's contribution"""
    contributions = []
    
    for username in db.get_all_usernames():
        user_data = db.get_user_data(username)
        
        if period == "today":
            steps = user_data["history"].get(date.today().isoformat(), 0)
        else:  # week
            steps = 0
            for i in range(7):
                check_date = (date.today() - timedelta(days=i)).isoformat()
                steps += user_data["history"].get(check_date, 0)
        
        contributions.append({
            'Member': username,
            'Steps': steps
        })
    
    df = pd.DataFrame(contributions)
    df = df[df['Steps'] > 0]  # Only show members with steps
    
    if df.empty:
        return None
    
    fig = px.pie(
        df,
        values='Steps',
        names='Member',
        title=f"Team Contribution - {'Today' if period == 'today' else 'This Week'}",
        hole=0.4
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=350)
    
    return fig


def get_team_statistics(db: StepTrackerDB):
    """Calculate comprehensive team statistics"""
    all_users = db.get_all_usernames()
    
    if not all_users:
        return None
    
    today = date.today().isoformat()
    
    # Initialize stats
    total_members = len(all_users)
    active_today = 0
    active_this_week = 0
    total_steps_all_time = 0
    total_steps_today = 0
    total_steps_week = 0
    goals_met_today = 0
    goals_met_week = 0
    streak_counts = []
    
    for username in all_users:
        user_data = db.get_user_data(username)
        
        # All-time total
        total_steps_all_time += sum(user_data["history"].values())
        
        # Today's stats
        today_steps = user_data["history"].get(today, 0)
        total_steps_today += today_steps
        if today_steps > 0:
            active_today += 1
        if today_steps >= user_data["daily_goal"]:
            goals_met_today += 1
        
        # Weekly stats
        week_steps = 0
        for i in range(7):
            check_date = (date.today() - timedelta(days=i)).isoformat()
            day_steps = user_data["history"].get(check_date, 0)
            week_steps += day_steps
            if day_steps > 0 and username not in [u for u in all_users if active_this_week]:
                active_this_week += 1
        
        total_steps_week += week_steps
        if week_steps >= user_data["daily_goal"] * 7:
            goals_met_week += 1
        
        # Calculate current streak
        streak = 0
        for i in range(30):
            check_date = (date.today() - timedelta(days=i)).isoformat()
            if user_data["history"].get(check_date, 0) >= user_data["daily_goal"]:
                streak += 1
            else:
                break
        streak_counts.append(streak)
    
    return {
        'total_members': total_members,
        'active_today': active_today,
        'active_this_week': active_this_week,
        'total_steps_all_time': total_steps_all_time,
        'total_steps_today': total_steps_today,
        'total_steps_week': total_steps_week,
        'avg_steps_per_member_today': total_steps_today // total_members if total_members > 0 else 0,
        'avg_steps_per_member_week': total_steps_week // total_members if total_members > 0 else 0,
        'goals_met_today': goals_met_today,
        'goals_met_week': goals_met_week,
        'longest_streak': max(streak_counts) if streak_counts else 0,
        'avg_streak': sum(streak_counts) // len(streak_counts) if streak_counts else 0
    }


def login_page():
    """Display login page"""
    st.title("👟 Team Step Tracker")
    st.markdown("### Welcome! Let's get moving together! 🏃‍♀️🏃‍♂️")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("#### Sign In")
        username = st.text_input("Enter your name:", key="login_input")
        
        if st.button("Start Tracking", use_container_width=True):
            if username.strip():
                st.session_state.username = username.strip()
                st.rerun()
            else:
                st.error("Please enter your name")
        
        st.markdown("---")
        st.info("💡 Just enter your name to get started. No password needed!")


def main_app():
    """Main application interface"""
    db = st.session_state.db
    username = st.session_state.username
    user_data = db.get_user_data(username)
    
    # Sidebar
    with st.sidebar:
        st.title(f"👋 Hi, {username}!")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.username = None
            st.rerun()
        
        st.markdown("---")
        
        # Goal setting
        st.markdown("### ⚙️ Settings")
        current_goal = user_data["daily_goal"]
        new_goal = st.number_input(
            "Daily Step Goal",
            min_value=1000,
            max_value=50000,
            value=current_goal,
            step=500
        )
        
        if new_goal != current_goal:
            db.set_goal(username, new_goal)
            st.success(f"Goal updated to {new_goal:,} steps!")
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Your Stats")
        
        # Calculate stats
        total_days = len(user_data["history"])
        if total_days > 0:
            total_steps = sum(user_data["history"].values())
            avg_steps = total_steps // total_days
            goals_met = sum(1 for s in user_data["history"].values() 
                          if s >= user_data["daily_goal"])
            
            st.metric("Total Days", total_days)
            st.metric("Total Steps", f"{total_steps:,}")
            st.metric("Average/Day", f"{avg_steps:,}")
            st.metric("Goals Met", f"{goals_met}/{total_days}")
        else:
            st.info("Start logging steps to see your stats!")
        
        # Admin Panel
        st.markdown("---")
        st.markdown("### 🔧 Admin Panel")
        
        with st.expander("💾 Backup & Restore", expanded=True):
            st.caption("Data is stored in the app until you delete it. Download a backup to keep a copy (e.g. save to Google Drive or your computer).")
            st.markdown("**Download backup** (full data, JSON — save this file to keep your data safe)")
            backup_json = json.dumps(db.data, indent=2)
            st.download_button(
                "⬇️ Download backup (JSON)",
                data=backup_json,
                file_name=f"step_tracker_backup_{date.today().isoformat()}.json",
                mime="application/json",
                key="download_backup"
            )
            st.markdown("---")
            st.markdown("**Restore from backup**")
            uploaded = st.file_uploader("Upload a backup JSON file", type=["json"], key="restore_upload")
            if uploaded:
                try:
                    restored = json.load(uploaded)
                    if "users" in restored:
                        if st.button("Restore this backup (replaces current data)", key="restore_btn"):
                            db.load_from_backup(restored)
                            st.success("Data restored. Refreshing...")
                            st.rerun()
                    else:
                        st.error("Invalid backup file: missing 'users'.")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
        
        with st.expander("⚠️ Manage Users"):
            all_users = db.get_all_usernames()
            
            # Add team member (name only)
            st.markdown("#### Add Team Member")
            new_member_name = st.text_input("Enter name to add to the team:", key="new_member_name", placeholder="e.g. Jordan")
            if st.button("➕ Add Member", key="add_member_btn"):
                name = (new_member_name or "").strip()
                if name:
                    db.get_user_data(name)  # creates user with default goal
                    st.success(f"✅ Added {name} to the team.")
                    st.rerun()
                else:
                    st.error("Please enter a name.")
            st.markdown("---")
            
            if all_users:
                st.markdown(f"**Total Users:** {len(all_users)}")
                
                # Delete specific user
                st.markdown("#### Remove Specific User")
                user_to_delete = st.selectbox("Select user to remove:", all_users, key="delete_user_select")
                
                if st.button("🗑️ Remove This User", key="delete_single"):
                    if user_to_delete in db.data["users"]:
                        del db.data["users"][user_to_delete]
                        db.save_data()
                        st.success(f"✅ Removed {user_to_delete}")
                        if user_to_delete == username:
                            st.session_state.username = None
                        st.rerun()
                
                # Clear all users
                st.markdown("---")
                st.markdown("#### Clear All Users")
                st.warning("⚠️ This will delete ALL users and their data!")
                
                confirm_clear = st.text_input("Type 'DELETE ALL' to confirm:", key="confirm_clear")
                
                if st.button("🗑️ Clear All Users", key="clear_all", type="secondary"):
                    if confirm_clear == "DELETE ALL":
                        db.data["users"] = {}
                        db.save_data()
                        st.success("✅ All users cleared!")
                        st.session_state.username = None
                        st.rerun()
                    else:
                        st.error("Please type 'DELETE ALL' to confirm")
            else:
                st.info("No users to manage")
        
        with st.expander("📢 Announcement"):
            msg = st.text_area(
                "Message for the team (shown at top of app):",
                value=db.get_admin_message(),
                height=100,
                placeholder="e.g. Great work this week! Let's aim for 120% of our goal.",
                key="admin_message_input"
            )
            if st.button("Save announcement", key="save_announcement"):
                db.set_admin_message(msg)
                st.success("Announcement saved.")
                st.rerun()
        
        with st.expander("🎯 Team Challenge"):
            c = db.get_challenge()
            if c["active"]:
                st.success("**Challenge is active**")
                st.markdown(f"**Team goal:** {c['team_goal']:,} steps")
                st.markdown(f"**Started:** {c['start_date']}")
                steps_in = db.get_team_steps_in_challenge()
                pct = (steps_in / c["team_goal"] * 100) if c["team_goal"] else 0
                st.markdown(f"**Progress:** {steps_in:,} / {c['team_goal']:,} ({pct:.1f}%)")
                if st.button("🏁 End Challenge", key="end_challenge"):
                    db.end_challenge(date.today().isoformat())
                    st.success("Challenge ended. All step data is kept.")
                    st.rerun()
            else:
                st.info("No active challenge. Set a team goal and start one.")
                team_goal = st.number_input(
                    "Team goal (total steps)",
                    min_value=10000,
                    max_value=100_000_000,
                    value=500000,
                    step=10000,
                    key="team_goal_input"
                )
                start_date = st.date_input("Challenge start date", value=date.today(), key="challenge_start")
                target_end = st.date_input("Target end date (optional)", value=None, key="challenge_target_end")
                if st.button("▶️ Start Challenge", key="start_challenge"):
                    db.set_challenge(
                        team_goal,
                        start_date.isoformat(),
                        target_end.isoformat() if target_end else None
                    )
                    st.success(f"Challenge started! Goal: {team_goal:,} steps.")
                    st.rerun()
        
        with st.expander("📅 Weekly Team Goal"):
            wg = db.get_weekly_goal()
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            st.caption(f"This week: {week_start} → {week_end}")
            current_goal = wg.get("goal") or 0
            weekly_goal_value = st.number_input(
                "Team steps goal for this week",
                min_value=0,
                max_value=10_000_000,
                value=current_goal if current_goal else 100000,
                step=5000,
                key="weekly_goal_input"
            )
            if st.button("✅ Set Weekly Goal", key="set_weekly_goal"):
                db.set_weekly_goal(weekly_goal_value)
                st.success(f"Weekly goal set to {weekly_goal_value:,} steps.")
                st.rerun()
            if current_goal:
                steps_this_week = db.get_team_steps_this_week()
                pct = (steps_this_week / current_goal * 100) if current_goal else 0
                st.metric("Steps this week", f"{steps_this_week:,}")
                st.progress(min(pct / 100, 1.0))
                st.caption(f"{pct:.1f}% of weekly goal")
    
    # Main content
    st.title("👟 Team Step Tracker")
    
    msg = db.get_admin_message()
    if msg:
        st.info(f"📢 **Announcement:** {msg}")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Log Steps", "📈 My Progress", "🏆 Team Leaderboard", "📊 Team Dashboard", "📥 Export Data"])
    
    with tab1:
        st.markdown("### Log Steps")
        
        # Who are we logging for?
        all_members = db.get_all_usernames()
        log_for_options = ["Myself (" + username + ")"] + sorted([m for m in all_members if m != username])
        log_for_options.append("Add new person (enter name below)")
        
        log_for_choice = st.selectbox(
            "Log steps for:",
            options=log_for_options,
            key="log_for_select"
        )
        
        if log_for_choice == "Add new person (enter name below)":
            log_for_name = st.text_input("Enter their name:", key="log_for_new_name", placeholder="e.g. Sam")
        else:
            log_for_name = username if log_for_choice.startswith("Myself") else log_for_choice
        
        col1, col2 = st.columns(2)
        
        with col1:
            log_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today(),
                key="log_date_input"
            )
        
        with col2:
            target_user_data = db.get_user_data(log_for_name) if (log_for_name and log_for_name.strip()) else None
            current_steps = target_user_data["history"].get(log_date.isoformat(), 0) if target_user_data else 0
            steps = st.number_input(
                "Step Count",
                min_value=0,
                max_value=100000,
                value=current_steps,
                step=100,
                key="steps_input"
            )
        
        if st.button("💾 Save Steps", use_container_width=True, type="primary", key="save_steps_btn"):
            who = (log_for_name or "").strip()
            if not who:
                st.error("Please choose who to log for or enter a name.")
            else:
                db.log_steps(who, steps, log_date.isoformat())
                st.success(f"✅ Logged {steps:,} steps for **{who}** on {log_date}")
                st.rerun()
        
        # Today's progress
        st.markdown("---")
        today = date.today().isoformat()
        today_steps = user_data["history"].get(today, 0)
        goal = user_data["daily_goal"]
        
        st.markdown("### Today's Progress")
        
        # Progress gauge
        fig = create_progress_chart(today_steps, goal)
        st.plotly_chart(fig, use_container_width=True)
        
        # Progress metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Steps Today", f"{today_steps:,}")
        
        with col2:
            st.metric("Daily Goal", f"{goal:,}")
        
        with col3:
            percentage = (today_steps / goal * 100) if goal > 0 else 0
            st.metric("Progress", f"{percentage:.1f}%")
        
        # Celebration
        if today_steps >= goal:
            st.balloons()
            st.success("🎉 Congratulations! You've reached your goal today! 🎉")
        elif today_steps > 0:
            remaining = goal - today_steps
            st.info(f"🚶 {remaining:,} steps remaining to reach your goal!")
    
    with tab2:
        st.markdown("### Your Step History")
        
        if user_data["history"]:
            # History chart
            days_to_show = st.slider("Days to show", 7, 30, 14)
            fig = create_history_chart(user_data["history"], user_data["daily_goal"], days_to_show)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Recent entries table
            st.markdown("#### Recent Entries")
            sorted_history = sorted(user_data["history"].items(), reverse=True)[:10]
            
            table_data = []
            for log_date, steps in sorted_history:
                goal = user_data["daily_goal"]
                percentage = (steps / goal * 100) if goal > 0 else 0
                status = "✅" if steps >= goal else "⏳"
                table_data.append({
                    "Status": status,
                    "Date": log_date,
                    "Steps": f"{steps:,}",
                    "Progress": f"{percentage:.1f}%"
                })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("📝 No history yet. Start logging your steps!")
    
    with tab3:
        st.markdown("### Team Leaderboard")
        
        period = st.radio("Period", ["today", "week"], horizontal=True, key="leaderboard_period")
        
        period_label = "Today" if period == "today" else "This Week"
        st.markdown(f"#### {period_label}'s Rankings")
        
        leaderboard_df = create_team_leaderboard(db, period)
        
        if not leaderboard_df.empty:
            # Add medals for top 3
            for idx in range(min(3, len(leaderboard_df))):
                medal = ["🥇", "🥈", "🥉"][idx]
                leaderboard_df.at[idx, 'User'] = f"{medal} {leaderboard_df.at[idx, 'User']}"
            
            # Format steps column
            leaderboard_df['Steps'] = leaderboard_df['Steps'].apply(lambda x: f"{x:,}")
            leaderboard_df['Goal'] = leaderboard_df['Goal'].apply(lambda x: f"{x:,}")
            
            st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)
            
            # Team totals
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            total_steps = sum(int(s.replace(',', '')) for s in leaderboard_df['Steps'])
            
            with col1:
                st.metric(f"Team Total ({period_label})", f"{total_steps:,} steps")
            
            with col2:
                st.metric("Active Members", len(leaderboard_df))
        else:
            st.info("No data yet. Be the first to log steps!")
    
    with tab4:
        st.markdown("### 📊 Team Dashboard - Overall View")
        
        msg = db.get_admin_message()
        if msg:
            st.info(f"📢 **Announcement:** {msg}")
        
        # Weekly team goal (if set)
        wg = db.get_weekly_goal()
        if wg.get("goal"):
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            steps_this_week = db.get_team_steps_this_week()
            goal = wg["goal"]
            pct = min((steps_this_week / goal * 100), 100) if goal else 0
            st.markdown("#### 📅 This Week's Goal")
            st.caption(f"Week: {week_start} – {week_end}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Weekly goal", f"{goal:,} steps")
            with col2:
                st.metric("Steps this week", f"{steps_this_week:,}")
            with col3:
                st.metric("Progress", f"{pct:.1f}%")
            st.progress(pct / 100)
            st.markdown("---")
        
        # Team Challenge progress (if challenge exists)
        c = db.get_challenge()
        if c.get("team_goal") and c.get("start_date"):
            steps_in_challenge = db.get_team_steps_in_challenge()
            goal = c["team_goal"]
            pct = min((steps_in_challenge / goal * 100), 100) if goal else 0
            end_display = c.get("end_date") or date.today().isoformat()
            period_label = f"Challenge period: {c['start_date']} → {end_display}"
            st.markdown("#### 🎯 Team Challenge Progress")
            st.caption(period_label)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Team Goal", f"{goal:,} steps")
            with col2:
                st.metric("Steps in challenge", f"{steps_in_challenge:,}")
            with col3:
                st.metric("Progress", f"{pct:.1f}%")
            st.progress(pct / 100)
            # Days left + pace (only when challenge is still active)
            if c.get("active"):
                today = date.today()
                start_d = date.fromisoformat(c["start_date"])
                target_end = c.get("target_end_date")
                if target_end:
                    try:
                        end_d = date.fromisoformat(target_end)
                        if end_d >= today:
                            days_left = (end_d - today).days
                            steps_needed = max(0, goal - steps_in_challenge)
                            steps_per_day = (steps_needed / days_left) if days_left else 0
                            st.markdown("**⏱️ Days left & pace**")
                            st.write(f"**{days_left}** days left. Need **{steps_per_day:,.0f}** steps/day to reach the goal.")
                        else:
                            st.caption("Target end date has passed. End the challenge when ready.")
                    except (ValueError, TypeError):
                        pass
                else:
                    days_in = (today - start_d).days or 1
                    avg_per_day = steps_in_challenge / days_in
                    steps_remaining = max(0, goal - steps_in_challenge)
                    if avg_per_day > 0 and steps_remaining > 0:
                        days_to_goal = int(steps_remaining / avg_per_day)
                        st.markdown("**⏱️ Pace**")
                        st.write(f"**{days_in}** days in. Averaging **{avg_per_day:,.0f}** steps/day. At this pace, goal in **~{days_to_goal}** days.")
                    else:
                        st.write(f"**{days_in}** days in. Keep logging steps!")
            if c.get("end_date"):
                st.caption(f"✅ Challenge ended on {c['end_date']}. All steps are kept for the record.")
            st.markdown("---")
        
        stats = get_team_statistics(db)
        
        if stats and stats['total_members'] > 0:
            # Top metrics row
            st.markdown("#### 🎯 Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Members", stats['total_members'])
            
            with col2:
                st.metric("Active Today", f"{stats['active_today']}/{stats['total_members']}")
            
            with col3:
                st.metric("Steps Today", f"{stats['total_steps_today']:,}")
            
            with col4:
                st.metric("Goals Met Today", f"{stats['goals_met_today']}/{stats['total_members']}")
            
            st.markdown("---")
            
            # Charts row
            col1, col2 = st.columns(2)
            
            with col1:
                # Team progress over time
                st.markdown("#### 📈 Team Progress Trend")
                days_to_show = st.selectbox("Time Period", [7, 14, 30], index=0, key="trend_days")
                progress_chart = create_team_progress_chart(db, days_to_show)
                st.plotly_chart(progress_chart, use_container_width=True)
            
            with col2:
                # Team contribution pie chart
                st.markdown("#### 👥 Member Contributions")
                contribution_period = st.radio("Period", ["today", "week"], horizontal=True, key="contribution_period")
                contribution_chart = create_team_contribution_chart(db, contribution_period)
                if contribution_chart:
                    st.plotly_chart(contribution_chart, use_container_width=True)
                else:
                    st.info("No data available for this period")
            
            st.markdown("---")
            
            # Weekly performance
            st.markdown("#### 📅 This Week's Performance")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Weekly Steps", f"{stats['total_steps_week']:,}")
            
            with col2:
                st.metric("Avg Steps/Member", f"{stats['avg_steps_per_member_week']:,}")
            
            with col3:
                st.metric("Weekly Goals Met", f"{stats['goals_met_week']}/{stats['total_members']}")
            
            with col4:
                st.metric("Active This Week", f"{stats['active_this_week']}/{stats['total_members']}")
            
            st.markdown("---")
            
            # Achievements & Milestones
            st.markdown("#### 🏆 Team Achievements")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("##### 🔥 Streaks")
                st.metric("Longest Current Streak", f"{stats['longest_streak']} days")
                st.metric("Average Streak", f"{stats['avg_streak']} days")
            
            with col2:
                st.markdown("##### 🚀 All-Time Stats")
                st.metric("Total Steps Ever", f"{stats['total_steps_all_time']:,}")
                avg_daily = stats['total_steps_all_time'] // max(1, stats['total_members'])
                st.metric("Avg Steps/Member (All-Time)", f"{avg_daily:,}")
            
            with col3:
                st.markdown("##### 🎯 Team Health")
                participation_rate = (stats['active_this_week'] / stats['total_members'] * 100) if stats['total_members'] > 0 else 0
                st.metric("Weekly Participation", f"{participation_rate:.0f}%")
                
                goal_success_rate = (stats['goals_met_week'] / stats['total_members'] * 100) if stats['total_members'] > 0 else 0
                st.metric("Goal Success Rate", f"{goal_success_rate:.0f}%")
            
            st.markdown("---")
            
            # Milestones
            st.markdown("#### 🎉 Team Milestones")
            
            milestones = []
            total = stats['total_steps_all_time']
            
            # Define milestone thresholds
            milestone_levels = [
                (10000000, "🌟 10 Million Steps!", "Incredible achievement!"),
                (5000000, "💎 5 Million Steps!", "Outstanding effort!"),
                (1000000, "🏆 1 Million Steps!", "Amazing teamwork!"),
                (500000, "⭐ 500K Steps!", "Great progress!"),
                (100000, "🎯 100K Steps!", "Nice start!")
            ]
            
            achieved_milestone = None
            next_milestone = None
            
            for threshold, title, desc in milestone_levels:
                if total >= threshold:
                    achieved_milestone = (threshold, title, desc)
                    break
            
            for threshold, title, desc in reversed(milestone_levels):
                if total < threshold:
                    next_milestone = (threshold, title, total)
                    break
            
            col1, col2 = st.columns(2)
            
            with col1:
                if achieved_milestone:
                    st.success(f"### {achieved_milestone[1]}")
                    st.write(f"**{achieved_milestone[2]}**")
                    st.write(f"Your team has walked {total:,} total steps!")
                else:
                    st.info("Keep walking to unlock your first milestone!")
            
            with col2:
                if next_milestone:
                    remaining = next_milestone[0] - next_milestone[2]
                    progress_pct = (next_milestone[2] / next_milestone[0]) * 100
                    st.info(f"### Next: {next_milestone[1]}")
                    st.write(f"**{remaining:,} steps to go!**")
                    st.progress(progress_pct / 100)
                    st.write(f"Progress: {progress_pct:.1f}%")
            
            st.markdown("---")
            
            # Team Tips
            st.markdown("#### 💡 Team Tips")
            
            tips = []
            
            if participation_rate < 50:
                tips.append("🔔 **Reminder:** Encourage inactive members to log their steps!")
            
            if goal_success_rate < 30:
                tips.append("🎯 **Tip:** Consider adjusting individual goals to be more achievable")
            
            if stats['avg_steps_per_member_today'] < 5000:
                tips.append("🚶 **Challenge:** Try a lunchtime walking meeting to boost today's steps")
            
            if stats['longest_streak'] >= 7:
                tips.append(f"🔥 **Amazing:** Someone has a {stats['longest_streak']}-day streak! Keep it going!")
            
            if not tips:
                tips.append("✨ **Great job!** Your team is doing fantastic. Keep up the momentum!")
            
            for tip in tips:
                st.write(tip)
        
        else:
            st.info("📝 No team data yet. Team members need to start logging steps to see the dashboard!")
            st.markdown("""
            **To get started:**
            1. Share this app URL with your team
            2. Each person enters their name to join
            3. Everyone logs their daily steps
            4. Watch the team dashboard come alive with stats and charts!
            """)
            
            # Show how to invite
            st.markdown("---")
            st.markdown("### 👥 Invite Your Team")
            st.markdown("""
            **Share this link with your teammates:**
            
            Copy the URL from your browser and send it via:
            - Email
            - Slack/Teams message
            - Text message
            
            They just need to:
            1. Open the link
            2. Enter their name
            3. Start tracking!
            """)
    
    with tab5:
        st.markdown("### 📥 Export & View All Data")
        st.markdown("""
        **Storage:** Data is stored in the app until you delete it.  
        **Download:** Use the buttons below to save a copy to your computer or Google Drive.  
        **Restore:** If the app ever resets, go to Admin → Backup & Restore and upload a backup file.
        """)
        rows = db.get_all_steps_for_export()
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Download as CSV",
                data=csv,
                file_name=f"team_steps_export_{date.today().isoformat()}.csv",
                mime="text/csv",
                key="download_csv"
            )
        else:
            st.info("No step data yet. Entries will appear here as the team logs steps.")


def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Team Step Tracker",
        page_icon="👟",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    if st.session_state.username is None:
        login_page()
    else:
        main_app()


if __name__ == "__main__":
    main()

