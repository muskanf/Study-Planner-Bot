# PlannerPro 

MADE BY: MUSKAN FATIMA & ELIZABETH BANGIYEV

PlannerPro is an AI-powered study planning assistant built with Streamlit and OpenAI’s GPT API. It helps students design and update study plans based on deadlines, exam dates, study preferences, and break habits. The assistant generates plans through a conversational interface, making it easy for users to interact and change their schedules. The app also includes a dynamic to-do list and calendar for task management.

Contributions:
- Muskan Fatima: Chatbot implementation, test prompting, and to-do list integration
- Elizabeth Bangiyev: Calendar integration, chatbot testing, and debugging

---

##  Features

- **Chat Interface**: Users can ask PlannerPro to create or revise a study schedule.
- **Dynamic To-Do List**: Tasks extracted from chat responses are auto-saved to a to-do list.
- **Calendar**: Users can manually add tasks and deadlines to the calendar. Additionally, chat reponses are parsed for tasks and deadlines, which are then added to the calendar.
- **Scope Guard**: Limits interaction to study-related topics only.
- **Safety Guard**: Basic protection against prompt injections.
- **Model Controls**: Adjustable generation parameters like temperature and token limits.

---

## 🛠️ Design & Architecture

- Frontend: Built with Streamlit’s chat and form APIs.
- Model: Uses `gpt-4o-mini` via OpenAI's Python SDK.
- **Prompt Engineering**: Custom system prompt to enforce consistent behavior and a scoped persona.
- **Memory**: Persists the conversation and extracted todos in `st.session_state`.
- **Modularity**: Regex-based parsing for scope filtering and bullet task detection.



pip install -r requirements.txt