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
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {"users": {}}
    
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
    
    # Main content
    st.title("👟 Team Step Tracker")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Log Steps", "📈 My Progress", "🏆 Team Leaderboard", "📊 Team Dashboard"])
    
    with tab1:
        st.markdown("### Log Your Steps")
        
        col1, col2 = st.columns(2)
        
        with col1:
            log_date = st.date_input(
                "Date",
                value=date.today(),
                max_value=date.today()
            )
        
        with col2:
            today = date.today().isoformat()
            current_steps = user_data["history"].get(log_date.isoformat(), 0)
            steps = st.number_input(
                "Step Count",
                min_value=0,
                max_value=100000,
                value=current_steps,
                step=100
            )
        
        if st.button("💾 Save Steps", use_container_width=True, type="primary"):
            db.log_steps(username, steps, log_date.isoformat())
            st.success(f"✅ Logged {steps:,} steps for {log_date}")
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

