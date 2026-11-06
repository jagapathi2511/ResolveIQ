import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="ResolveIQ | AI Support Agent",
    page_icon="🧠",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

# =========================================================
# 2. SESSION STATE
# =========================================================

if "token" not in st.session_state:
    st.session_state.token = None

if "current_customer" not in st.session_state:
    st.session_state.current_customer = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "troubleshooting_history" not in st.session_state:
    st.session_state.troubleshooting_history = {}

if "recommendations" not in st.session_state:
    st.session_state.recommendations = {}

# =========================================================
# 3. CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #F5F7FB;
    }

    [data-testid="stSidebar"] {
        background-color: #172554;
    }

    [data-testid="stSidebar"] * {
        color: white;
    }

    .main-title {
        font-size: 32px;
        font-weight: 800;
        color: #172554;
    }

    .subtitle {
        color: #64748B;
        font-size: 15px;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }

    .metric-label {
        color: #64748B;
        font-size: 14px;
    }

    .metric-value {
        color: #172554;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 4. API HELPER
# =========================================================

def api_request(method, endpoint, data=None, params=None, timeout=60):
    headers = {}

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:
        response = requests.request(
            method=method,
            url=f"{API_URL}{endpoint}",
            json=data,
            params=params,
            headers=headers,
            timeout=timeout
        )

        if response.status_code >= 400:
            try:
                detail = response.json().get(
                    "detail",
                    response.text
                )
            except Exception:
                detail = response.text

            st.error(
                f"API Error ({response.status_code}): {detail}"
            )
            return None

        if not response.text:
            return {}

        return response.json()

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the backend. "
            "Start FastAPI using: uvicorn backend.main:app --reload"
        )
        return None

    except requests.exceptions.Timeout:
        st.error("The API request timed out. Please try again.")
        return None

    except Exception as error:
        st.error(f"Unexpected error: {error}")
        return None


def get_customers():
    result = api_request("GET", "/customers")

    if isinstance(result, list):
        return result

    if isinstance(result, dict):
        return [result]

    return []


def get_tickets():
    result = api_request("GET", "/tickets")

    if isinstance(result, list):
        return result

    return []


def get_analyses():
    result = api_request("GET", "/ticket-analyses")

    if isinstance(result, list):
        return result

    return []


def show_page_title(title, subtitle=""):
    st.markdown(
        f'<div class="main-title">{title}</div>',
        unsafe_allow_html=True
    )

    if subtitle:
        st.markdown(
            f'<div class="subtitle">{subtitle}</div>',
            unsafe_allow_html=True
        )

    st.write("")


def metric_card(label, value, emoji):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{emoji} {label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 5. LOGIN AND REGISTRATION
# =========================================================

def login_user(email, password):
    result = api_request(
        "POST",
        "/login",
        data={
            "email": email,
            "password": password
        }
    )

    if result and result.get("access_token"):
        st.session_state.token = result["access_token"]

        customers = get_customers()

        if customers:
            st.session_state.current_customer = customers[0]
            st.session_state.chat_history = []
            return True

        st.error(
            "Login succeeded, but the customer profile "
            "could not be loaded."
        )
        st.session_state.token = None

    return False


def authentication_page():
    st.title("🧠 ResolveIQ")
    st.subheader("AI-Powered Customer Support Memory Agent")

    st.write(
        "Welcome! Sign in to manage your support tickets "
        "and access your AI customer support assistant."
    )

    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )

    with login_tab:
        st.markdown("### Login to ResolveIQ")

        with st.form("login_form"):
            email = st.text_input(
                "Email Address",
                key="login_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            submitted = st.form_submit_button("Login")

            if submitted:
                if not email or not password:
                    st.warning("Enter your email and password.")
                else:
                    if login_user(email, password):
                        st.success("Login successful!")
                        st.rerun()

    with register_tab:
        st.markdown("### Create Your Account")

        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email Address")
            password = st.text_input(
                "Create Password",
                type="password"
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create Account"
            )

            if submitted:
                if not name or not email or not password:
                    st.warning("Please complete all fields.")

                elif password != confirm_password:
                    st.error("Passwords do not match.")

                elif len(password) < 8:
                    st.warning(
                        "Use a password with at least 8 characters."
                    )

                else:
                    result = api_request(
                        "POST",
                        "/customers",
                        data={
                            "name": name,
                            "email": email,
                            "password": password
                        }
                    )

                    if result:
                        st.success(
                            "Account created successfully. "
                            "Logging you in..."
                        )

                        if login_user(email, password):
                            st.rerun()


# =========================================================
# 6. AUTHENTICATION GATE
# =========================================================

if not st.session_state.token:
    authentication_page()
    st.stop()

customer = st.session_state.current_customer

if not customer:
    customers = get_customers()

    if customers:
        customer = customers[0]
        st.session_state.current_customer = customer
    else:
        st.error("Unable to load your customer profile.")
        st.stop()

customer_id = customer["id"]

# =========================================================
# 7. SIDEBAR NAVIGATION
# =========================================================

st.sidebar.title("🧠 ResolveIQ")
st.sidebar.caption("AI-Powered Customer Support Memory Agent")
st.sidebar.divider()

st.sidebar.write(
    f"Logged in as: **{customer.get('name', 'Customer')}**"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Customers",
        "Create Ticket",
        "Ticket Management",
        "AI Support Chat",
        "Ticket Analysis",
        "Customer Memory Profile"
    ]
)

st.sidebar.divider()

if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.session_state.current_customer = None
    st.session_state.chat_history = []
    st.session_state.troubleshooting_history = {}
    st.session_state.recommendations = {}
    st.rerun()

st.sidebar.caption("ResolveIQ | Intelligent Customer Support")

# =========================================================
# 8. DASHBOARD
# =========================================================

if page == "Dashboard":

    show_page_title(
        "📊 Dashboard",
        "Monitor your customer support performance."
    )

    tickets = get_tickets()
    analyses = get_analyses()

    total_tickets = len(tickets)

    open_tickets = sum(
        1 for ticket in tickets
        if ticket.get("status") == "open"
    )

    in_progress = sum(
        1 for ticket in tickets
        if ticket.get("status") == "in_progress"
    )

    resolved_tickets = sum(
        1 for ticket in tickets
        if ticket.get("status") == "resolved"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("Total Tickets", total_tickets, "🎫")

    with col2:
        metric_card("Open Tickets", open_tickets, "📂")

    with col3:
        metric_card("In Progress", in_progress, "⏳")

    with col4:
        metric_card("Resolved", resolved_tickets, "✅")

    st.divider()

    if tickets:
        ticket_df = pd.DataFrame(tickets)

        st.subheader("Ticket Overview")

        st.dataframe(
            ticket_df,
            width="stretch",
            hide_index=True
        )

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            if "status" in ticket_df.columns:
                status_counts = (
                    ticket_df["status"]
                    .value_counts()
                    .reset_index()
                )
                status_counts.columns = ["Status", "Count"]

                fig = px.pie(
                    status_counts,
                    names="Status",
                    values="Count",
                    hole=0.45,
                    title="Tickets by Status"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

        with chart_col2:
            if "priority" in ticket_df.columns:
                priority_counts = (
                    ticket_df["priority"]
                    .value_counts()
                    .reset_index()
                )
                priority_counts.columns = ["Priority", "Count"]

                fig = px.bar(
                    priority_counts,
                    x="Priority",
                    y="Count",
                    color="Priority",
                    title="Tickets by Priority"
                )

                st.plotly_chart(
                    fig,
                    width="stretch"
                )

    else:
        st.info(
            "No support tickets found. "
            "Create your first ticket to get started."
        )

    st.divider()
    st.subheader("AI Insights")

    if analyses:
        analysis_df = pd.DataFrame(analyses)

        if "sentiment" in analysis_df.columns:
            sentiment_counts = (
                analysis_df["sentiment"]
                .value_counts()
                .reset_index()
            )
            sentiment_counts.columns = ["Sentiment", "Count"]

            fig = px.pie(
                sentiment_counts,
                names="Sentiment",
                values="Count",
                title="Customer Sentiment Distribution"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        st.dataframe(
            analysis_df,
            width="stretch",
            hide_index=True
        )

    else:
        st.info(
            "No AI analysis available yet. "
            "Analyze tickets to see AI insights."
        )


# =========================================================
# 9. CUSTOMER PROFILE
# =========================================================

elif page == "Customers":

    show_page_title(
        "👤 Customer Profile",
        "View your registered customer information."
    )

    st.subheader("Your Account Details")

    col1, col2 = st.columns(2)

    with col1:
        st.text_input(
            "Customer ID",
            value=str(customer.get("id", "")),
            disabled=True
        )

        st.text_input(
            "Customer Name",
            value=customer.get("name", ""),
            disabled=True
        )

    with col2:
        st.text_input(
            "Email Address",
            value=customer.get("email", ""),
            disabled=True
        )

    st.info(
        "Your account is linked to your support tickets "
        "and customer-specific AI memory."
    )

    st.divider()

    st.subheader("Your Support History")

    tickets = get_tickets()

    if tickets:
        st.dataframe(
            pd.DataFrame(tickets),
            width="stretch",
            hide_index=True
        )
    else:
        st.info("You have not created any support tickets yet.")


# =========================================================
# 10. CREATE SUPPORT TICKET
# =========================================================

elif page == "Create Ticket":

    show_page_title(
        "🎫 Create Support Ticket",
        "Submit a new customer support issue."
    )

    with st.form("ticket_form"):

        st.text_input(
            "Customer",
            value=customer.get("name", ""),
            disabled=True
        )

        subject = st.text_input("Ticket Subject")

        description = st.text_area(
            "Describe Your Issue",
            height=150
        )

        priority = st.selectbox(
            "Priority",
            ["low", "medium", "high", "critical"]
        )

        submitted = st.form_submit_button(
            "Create Support Ticket"
        )

        if submitted:

            if not subject.strip() or not description.strip():
                st.warning(
                    "Please enter both the subject and description."
                )

            else:
                result = api_request(
                    "POST",
                    "/tickets",
                    data={
                        "customer_id": customer_id,
                        "subject": subject,
                        "description": description,
                        "priority": priority
                    }
                )

                if result:
                    st.success("Ticket created successfully!")
                    st.json(result)
                    st.rerun()


# =========================================================
# 11. TICKET MANAGEMENT
# =========================================================

elif page == "Ticket Management":

    show_page_title(
        "🛠️ Ticket Management",
        "Manage tickets and review AI troubleshooting recommendations."
    )

    tickets = get_tickets()

    if not tickets:
        st.info("No tickets available.")
        st.stop()

    for ticket in tickets:

        ticket_id = ticket["id"]

        with st.expander(
            f"Ticket #{ticket_id} — {ticket.get('subject', 'Support Issue')}",
            expanded=False
        ):

            st.write(
                "**Description:**",
                ticket.get("description", "")
            )

            st.write(
                "**Current Status:**",
                ticket.get("status", "N/A")
            )

            st.write(
                "**Priority:**",
                ticket.get("priority", "N/A")
            )

            st.divider()

            st.markdown("### Update Ticket Status")

            status_options = [
                "open",
                "in_progress",
                "resolved"
            ]

            current_status = ticket.get("status", "open")

            if current_status not in status_options:
                current_status = "open"

            new_status = st.selectbox(
                "Select Status",
                status_options,
                index=status_options.index(current_status),
                key=f"status_{ticket_id}"
            )

            if st.button(
                "Update Status",
                key=f"update_{ticket_id}"
            ):
                result = api_request(
                    "PATCH",
                    f"/tickets/{ticket_id}/status",
                    params={"status": new_status}
                )

                if result is not None:
                    st.success("Ticket status updated.")
                    st.rerun()

            st.divider()

            st.markdown("### AI Ticket Analysis")

            if st.button(
                "Analyze This Ticket",
                key=f"analyze_{ticket_id}"
            ):
                result = api_request(
                    "POST",
                    f"/tickets/{ticket_id}/analyze"
                )

                if result:
                    st.success("Ticket analyzed.")
                    st.json(result)

            st.divider()

            st.markdown("### Troubleshooting History")

            if st.button(
                "Load Troubleshooting History",
                key=f"history_{ticket_id}"
            ):
                history = api_request(
                    "GET",
                    f"/tickets/{ticket_id}/troubleshooting-attempts"
                )

                if history is not None:
                    st.session_state.troubleshooting_history[
                        ticket_id
                    ] = history

            history = st.session_state.troubleshooting_history.get(
                ticket_id
            )

            if history is not None:

                if history:
                    history_df = pd.DataFrame(history)

                    st.dataframe(
                        history_df,
                        width="stretch",
                        hide_index=True
                    )

                    if "outcome" in history_df.columns:
                        outcomes = (
                            history_df["outcome"]
                            .astype(str)
                            .str.lower()
                        )

                        successful = outcomes.str.contains(
                            "success"
                        ).sum()

                        failed = outcomes.str.contains(
                            "fail"
                        ).sum()

                        col1, col2, col3 = st.columns(3)

                        col1.metric(
                            "Total Attempts",
                            len(history_df)
                        )

                        col2.metric(
                            "Successful",
                            int(successful)
                        )

                        col3.metric(
                            "Failed",
                            int(failed)
                        )

                else:
                    st.info(
                        "No troubleshooting attempts recorded yet."
                    )

            st.divider()

            st.markdown("### AI Next Recommendation")

            if st.button(
                "Generate Next Recommendation",
                key=f"recommend_{ticket_id}"
            ):
                recommendation = api_request(
                    "POST",
                    f"/tickets/{ticket_id}/next-recommendation"
                )

                if recommendation:
                    st.session_state.recommendations[
                        ticket_id
                    ] = recommendation

            recommendation = st.session_state.recommendations.get(
                ticket_id
            )

            if recommendation:

                st.info(
                    recommendation.get(
                        "recommendation",
                        str(recommendation)
                    )
                )

                st.caption(
                    "Previous attempts: "
                    f"{recommendation.get('previous_attempts', 'N/A')}"
                )

                feedback_notes = st.text_area(
                    "Customer Feedback / Notes",
                    key=f"feedback_{ticket_id}"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button(
                        "✅ It Worked",
                        key=f"success_{ticket_id}"
                    ):
                        result = api_request(
                            "POST",
                            f"/tickets/{ticket_id}/troubleshooting-feedback",
                            data={
                                "customer_id": customer_id,
                                "ticket_id": ticket_id,
                                "successful": True,
                                "notes": feedback_notes
                            }
                        )

                        if result is not None:
                            st.success(
                                "Successful feedback recorded."
                            )
                            st.session_state.recommendations.pop(
                                ticket_id,
                                None
                            )
                            st.rerun()

                with col2:
                    if st.button(
                        "❌ It Did Not Work",
                        key=f"failure_{ticket_id}"
                    ):
                        result = api_request(
                            "POST",
                            f"/tickets/{ticket_id}/troubleshooting-feedback",
                            data={
                                "customer_id": customer_id,
                                "ticket_id": ticket_id,
                                "successful": False,
                                "notes": feedback_notes
                            }
                        )

                        if result is not None:
                            st.warning(
                                "Unsuccessful feedback recorded."
                            )
                            st.session_state.recommendations.pop(
                                ticket_id,
                                None
                            )
                            st.rerun()


# =========================================================
# 12. AI SUPPORT CHAT
# =========================================================

elif page == "AI Support Chat":

    show_page_title(
        "🤖 AI Support Chat",
        "Chat with an AI assistant that uses customer-specific memory."
    )

    st.info(
        "ResolveIQ uses previous customer support interactions "
        "to help avoid repeating unsuccessful troubleshooting steps."
    )

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input(
        "Describe your support issue..."
    )

    if user_input:

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_input
            }
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):

            with st.spinner(
                "ResolveIQ is checking customer memory..."
            ):
                result = api_request(
                    "POST",
                    "/ai/memory-chat",
                    data={
                        "customer_id": customer_id,
                        "issue": user_input
                    },
                    timeout=120
                )

                if result:

                    response_text = result.get(
                        "response",
                        "No response received."
                    )

                    st.markdown(response_text)

                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": response_text
                        }
                    )

                    previous_memories = result.get(
                        "previous_memories",
                        []
                    )

                    if previous_memories:
                        with st.expander(
                            "🧠 Previous Customer Memories"
                        ):
                            for memory in previous_memories:
                                st.write(f"• {memory}")

                else:
                    st.error(
                        "Unable to get a response from ResolveIQ."
                    )

        st.rerun()

    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()


# =========================================================
# 13. AI TICKET ANALYSIS
# =========================================================

elif page == "Ticket Analysis":

    show_page_title(
        "🔍 AI Ticket Analysis",
        "Analyze ticket category, sentiment, priority and summary."
    )

    tab1, tab2 = st.tabs(
        [
            "Analyze Existing Ticket",
            "Analyze Custom Issue"
        ]
    )

    with tab1:

        tickets = get_tickets()

        if tickets:

            ticket_options = {
                (
                    f"Ticket #{ticket['id']} — "
                    f"{ticket.get('subject', 'Support Issue')}"
                ): ticket
                for ticket in tickets
            }

            selected_name = st.selectbox(
                "Select a Ticket",
                list(ticket_options.keys())
            )

            selected_ticket = ticket_options[selected_name]

            st.write("**Issue Description:**")
            st.write(
                selected_ticket.get("description", "")
            )

            if st.button("Analyze and Save Ticket"):

                result = api_request(
                    "POST",
                    f"/tickets/{selected_ticket['id']}/analyze"
                )

                if result:
                    st.success("Analysis completed.")
                    st.json(result)

        else:
            st.info("No tickets available for analysis.")

    with tab2:

        custom_issue = st.text_area(
            "Enter a Customer Issue",
            height=150,
            placeholder="Example: My internet connection keeps disconnecting."
        )

        if st.button("Analyze Custom Issue"):

            if not custom_issue.strip():
                st.warning("Please enter an issue.")

            else:
                result = api_request(
                    "POST",
                    "/ai/analyze",
                    data={
                        "issue": custom_issue,
                        "customer_history": ""
                    }
                )

                if result:
                    st.success("AI analysis completed.")
                    st.json(result)

    st.divider()

    st.subheader("Previous Ticket Analysis Records")

    analyses = get_analyses()

    if analyses:
        st.dataframe(
            pd.DataFrame(analyses),
            width="stretch",
            hide_index=True
        )
    else:
        st.info("No previous analysis records found.")


# =========================================================
# 14. CUSTOMER MEMORY PROFILE
# =========================================================

elif page == "Customer Memory Profile":

    show_page_title(
        "🧠 Customer Memory Profile",
        "Understand customer patterns using AI-powered memory insights."
    )

    st.subheader("Customer Information")

    st.write(f"**Name:** {customer.get('name', '')}")
    st.write(f"**Email:** {customer.get('email', '')}")
    st.write(f"**Customer ID:** {customer_id}")

    st.divider()

    st.subheader("AI Customer Memory Insights")

    st.write(
        "Generate a report based on previous support tickets "
        "and troubleshooting history."
    )

    if st.button("✨ Generate AI Memory Insights"):

        with st.spinner(
            "AI is analyzing customer support history..."
        ):
            result = api_request(
                "GET",
                f"/customers/{customer_id}/memory-insights",
                timeout=120
            )

        if result:

            st.success("AI Memory Insights Generated!")

            if "customer_name" in result:
                st.markdown(
                    f"### Customer: {result['customer_name']}"
                )

            if "total_tickets" in result:
                st.metric(
                    "Total Support Tickets",
                    result["total_tickets"]
                )

            if "insights" in result:
                st.markdown("### 📊 AI Analysis Report")
                st.markdown(result["insights"])
            else:
                st.json(result)

    st.divider()

    st.subheader("Your Ticket History")

    tickets = get_tickets()

    if tickets:
        st.dataframe(
            pd.DataFrame(tickets),
            width="stretch",
            hide_index=True
        )
    else:
        st.info("No support ticket history available.")


# =========================================================
# 15. FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#64748B; padding:15px;">
        <b>ResolveIQ</b> | AI-Powered Customer Support Memory Agent
        <br>
        Built with Python, FastAPI, Streamlit, Groq AI and Hindsight Memory
    </div>
    """,
    unsafe_allow_html=True
)