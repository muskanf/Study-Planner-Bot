# plannerpro_app.py
import re
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from openai import OpenAI
import os
import calendar
import datetime
import plotly.graph_objects as go

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("No OPENAI_API_KEY found in .env or environment variables.")

# Create OpenAI client
client = OpenAI(api_key=API_KEY)

MODEL = "gpt-4o-mini"

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are PlannerPro, a friendly and flexible assistant for students and professionals.\n"
    "Help users organize their tasks, manage their time, and balance work, study, and relaxation.\n"
    "You can assist with planning study schedules, managing deadlines, organizing personal tasks, or even suggesting ways to relax.\n"
    "Tasks can be added to a checklist without requiring a date, and abbreviations like 'hw' (homework) are acceptable.\n"
    "When providing a response, include specific tasks, deadlines, and optional suggestions for breaks or fun activities.\n"
    "Always include dates and events in the following format if applicable:\n"
    "YYYY-MM-DD: Event description (e.g., 2025-05-05: Chemistry exam).\n"
    "Use a conversational tone and avoid being overly strict or formal.\n"
    "End each response with a bullet list headed **Current Plan**.\n"
    "If a query is unrelated to planning or scheduling, politely redirect the user to focus on their goals, but remain helpful and open to their needs."
)
SCOPE_RE = re.compile(
    r"\b(deadline|exam|quiz|test|homework|assignment|project|study|schedule|plan|break)\b",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"^[\-\*\u2022]\s+(.*)", re.MULTILINE)


def is_safe(text: str) -> bool:
    """Tiny injection guard; replace with Moderation API if needed."""
    return not re.search(r'"role"\s*:\s*"system"', text)


# ─────────────────────────────────────────────────────────────
# Streamlit setup
# ─────────────────────────────────────────────────────────────
st.set_page_config("PlannerPro", "📚", layout="wide")
client = OpenAI()

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
if "todos" not in st.session_state:
    st.session_state.todos = []
if "events" not in st.session_state:
    st.session_state.events = {}

# Sidebar: generation knobs
with st.sidebar:
    st.header("Model Settings")
    temperature = st.slider("temperature", 0.0, 1.0, 0.3, 0.05)
    top_p = st.slider("top_p", 0.0, 1.0, 0.95, 0.05)
    max_tokens = st.number_input("max_tokens", 50, 2048, 350, 50)
    presence_penalty = st.slider("presence_penalty", -2.0, 2.0, 0.5, 0.1)
    if st.button("🔄 Reset conversation"):
        st.session_state.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        st.rerun()

# ─────────────────────────────────────────────────────────────
# Tabs: Chat | To-Do | Calendar
# ─────────────────────────────────────────────────────────────
chat_tab, todo_tab, calendar_tab = st.tabs(["💬 Chat", "📋 To-Do List", "📅 Calendar"])

# ========== CHAT TAB ==========
with chat_tab:
    st.subheader("PlannerPro – Study-Schedule Assistant")

    # Temporary note on how to use the chatbot
    if "show_note" not in st.session_state:
        st.session_state.show_note = True  # Initialize the note state

    if st.session_state.show_note:
        st.info(
            "💡 **How to Use PlannerPro:**\n"
            "- Ask me to create or revise your study plan.\n"
            "- Mention deadlines, exams, or tasks you want to add.\n"
            "- Be specific about what you want, e.g., 'Add a chemistry exam on May 5, 2025.'\n"
            "- Check the **To-Do List** and **Calendar** tabs for updates."
        )
    # Warning about short-term memory loss
    st.warning("⚠️ **Note:** I have short-term memory loss and can only remember the recent messages you send, so please fully describe what you want me to do per message.")

    # Show conversation history
    for m in st.session_state.messages:
        if m["role"] != "system":
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

    # Input box
    user_msg = st.chat_input("Ask me to build or revise your study plan…")
    if user_msg:
        with st.chat_message("user"):
            st.markdown(user_msg)

        # Safety / scope
        if not is_safe(user_msg):
            st.chat_message("assistant").markdown("⚠️ Input looks unsafe. Please rephrase.")
            st.stop()
        if not SCOPE_RE.search(user_msg):
            st.chat_message("assistant").markdown(
                "I’m focused on study planning and scheduling. "
                "Could you ask something related to those topics?"
            )
            st.stop()

        # Store user message
        st.session_state.messages.append({"role": "user", "content": user_msg})

        # Hidden chain-of-thought cue
        st.session_state.messages.append(
            {
                "role": "system",
                "content": "Think step by step about the schedule update, "
                           "but hide that reasoning.",
            }
        )

        # Call OpenAI
        resp = client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            presence_penalty=presence_penalty,
        )
        reply = resp.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": reply})


        # Parse tasks under **Current Plan**
        cp_block = re.search(r"\*\*Current Plan\*\*(.*)", reply,
                             re.IGNORECASE | re.DOTALL)
        if cp_block:
            for task_text in BULLET_RE.findall(cp_block.group(1)):
                task_text = task_text.strip()
                if task_text and task_text not in [t["text"] for t in st.session_state.todos]:
                    st.session_state.todos.append({"text": task_text, "done": False})


        date_event_pattern = r"(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},\s+\d{4})\s*:\s*(.+)"  # Matches "YYYY-MM-DD: Event description" or "Month DD, YYYY: Event description"
        for match in re.finditer(date_event_pattern, reply):
            event_date_str, event_description = match.groups()
            try:
                if "-" in event_date_str:  # YYYY-MM-DD
                    event_date = datetime.datetime.strptime(event_date_str, "%Y-%m-%d").date()
                else:  # Month DD, YYYY
                    event_date = datetime.datetime.strptime(event_date_str, "%B %d, %Y").date()

                event_key = event_date.strftime("%Y-%m-%d")
                if event_key not in st.session_state.events:
                    st.session_state.events[event_key] = []
                if event_description not in st.session_state.events[event_key]:
                    st.session_state.events[event_key].append(event_description)
            except ValueError:
                st.warning(f"Could not parse date: {event_date_str}")


        with st.chat_message("assistant"):
            st.markdown(reply)
            st.caption(
                f"Params ▸ temp {temperature} · top_p {top_p} · "
                f"max_tokens {max_tokens} · presence_pen {presence_penalty}"
            )

# ========== TO-DO TAB ==========
with todo_tab:
    st.subheader("My To-Do List")

    # Add new task
    with st.form("add_task"):
        new_task = st.text_input("Add a new task (e.g., 'Math hw' or 'Prepare for quiz')")
        submitted = st.form_submit_button("➕ Add")
        if submitted and new_task.strip():
            st.session_state.todos.append({"text": new_task.strip(), "done": False})

    # Render tasks
    for idx, task in enumerate(st.session_state.todos):
        cols = st.columns([0.08, 0.78, 0.14])
        done = cols[0].checkbox("", value=task["done"], key=f"todo_{idx}")
        st.session_state.todos[idx]["done"] = done
        style = "~~" if done else ""
        cols[1].markdown(f"{style}{task['text']}{style}")
        if cols[2].button("🗑️", key=f"del_{idx}"):
            st.session_state.todos.pop(idx)
            st.rerun()

    # Clear completed tasks
    if st.session_state.todos and st.button("Clear completed tasks"):
        st.session_state.todos = [t for t in st.session_state.todos if not t["done"]]
        st.rerun()
# ========== CALENDAR TAB ==========
with calendar_tab:
    st.subheader("📅 Calendar")

    # Getting currentdat date
    today = datetime.date.today()
    year = st.number_input("Year", min_value=1900, max_value=2100, value=today.year, step=1)
    month = st.selectbox("Month", range(1, 13), index=today.month - 1)

    # Generate calendar for selected month and year
    cal = calendar.Calendar()
    month_days = cal.monthdayscalendar(year, month)  # List of weeks, each week is a list of days (0 for empty days)

    # Creating figure for the calendar
    fig = go.Figure()

    # Adding banner for calendar title
    fig.add_trace(go.Scatter(
        x=[3],  
        y=[6],  
        mode="text",
        text=[f"{calendar.month_name[month]} {year}"],
        textfont=dict(size=30, color="white"),
        hoverinfo="skip",
    ))
    fig.add_shape(
        type="rect",
        x0=-0.5, x1=6.5, y0=5.5, y1=6.5,  
        fillcolor="steelblue",
        line=dict(width=0),
        layer="below",  
    )

    # Add days of week as headers
    for day_idx, day_name in enumerate(calendar.day_abbr):
        fig.add_trace(go.Scatter(
            x=[day_idx],
            y=[5],
            mode="text",
            text=[day_name],
            textfont=dict(size=20, color="black"),
            hoverinfo="skip",
        ))

    # Add days to calendar grid
    for week_idx, week in enumerate(month_days):
        for day_idx, day in enumerate(week):
            if day == 0:
                continue  # Skip empty days
            date_str = f"{year}-{month:02d}-{day:02d}"
            events = st.session_state.events.get(date_str, [])
            event_text = "<br>".join(events) if events else "No events"
            fig.add_trace(go.Scatter(
                x=[day_idx],
                y=[4 - week_idx], 
                mode="markers+text",
                marker=dict(
                    size=60,
                    color="lightblue" if events else "white",
                    line=dict(color="black", width=1),
                    symbol="square",
                ),
                text=[f"{day}"],
                textfont=dict(size=20, color="black"),
                hovertext=[f"{calendar.day_name[day_idx]}<br>{event_text}"],
                hoverinfo="text",
            ))

    # Update layout for the calendar
    fig.update_layout(
        title="",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=list(calendar.day_abbr),  
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(6)),
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        plot_bgcolor="white",
        height=600,
        margin=dict(l=20, r=20, t=20, b=20),
    )

    # Display the calendar
    st.plotly_chart(fig, use_container_width=True)

    # Add events
    st.subheader("Add Event")
    with st.form("add_event_form"):
        event_date = st.date_input(
            "Select a date",  # Non-empty label
            min_value=datetime.date(year, month, 1),
            max_value=datetime.date(year, month, calendar.monthrange(year, month)[1]),
            label_visibility="visible"  
        )
        event_description = st.text_input(
            "Event Description",  # Non-empty label
            label_visibility="visible"  
        )
        submitted = st.form_submit_button("➕ Add Event")
        if submitted:
            event_key = event_date.strftime("%Y-%m-%d")
            if event_key not in st.session_state.events:
                st.session_state.events[event_key] = []
            st.session_state.events[event_key].append(event_description)
            st.success(f"Event added for {event_date}: {event_description}")
            st.rerun()

    # Display events for the selected date
    st.subheader("Events for Selected Date")
    selected_date = st.date_input("View events for", value=today)
    selected_date_str = selected_date.strftime("%Y-%m-%d")

    if selected_date_str in st.session_state.events:
        st.write(f"Events on {selected_date}:")
        for idx, event in enumerate(st.session_state.events[selected_date_str]):
            cols = st.columns([0.85, 0.15])  
            # Format the event description to include standard time if applicable
            if ":" in event:  # Check if the event contains a time
                try:
                    time_part, description = event.split(" ", 1)
                    formatted_time = datetime.datetime.strptime(time_part, "%H:%M").strftime("%I:%M %p")
                    event_display = f"{formatted_time} - {description}"
                except ValueError:
                    event_display = event  # If parsing fails, keep the original event
            else:
                event_display = event

            cols[0].markdown(f"- {event_display}")  
            if cols[1].button("🗑️", key=f"delete_{selected_date_str}_{idx}"):
                # Remove the event from the list
                st.session_state.events[selected_date_str].pop(idx)
                # If no events remain for the date, then delete the date key
                if not st.session_state.events[selected_date_str]:
                    del st.session_state.events[selected_date_str]
                st.success(f"Event removed: {event}")
                st.rerun()
    else:
        st.write("No events for this date.")