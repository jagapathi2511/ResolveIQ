
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="ResolveIQ | AI Support Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://127.0.0.1:8000"


# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>
    .stApp {
        background-color: #F5F7FB;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #172554, #312E81);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
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
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
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

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================
# API HELPER
# ==================================================

def api_request(method, endpoint, data=None, params=None):

    try:
        response = requests.request(
            method=method,
            url=f"{API_URL}{endpoint}",
            json=data,
            params=params,
            timeout=30
        )

        if response.status_code >= 400:
            try:
                error_detail = response.json().get(
                    "detail",
                    response.text
                )
            except Exception:
                error_detail = response.text

            st.error(f"API Error ({response.status_code}): {error_detail}")
            return None

        if response.status_code == 204:
            return {}

        if response.text:
            return response.json()

        return {}

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to FastAPI. "
            "Please start the backend using uvicorn."
        )
        return None

    except requests.exceptions.Timeout:
        st.error("The API request timed out. Please try again.")
        return None

    except Exception as error:
        st.error(f"Unexpected error: {error}")
        return None


# ==================================================
# COMMON DATA HELPERS
# ==================================================

def get_customers():
    return api_request("GET", "/customers") or []


def get_tickets():
    return api_request("GET", "/tickets") or []


def get_analyses():
    return api_request("GET", "/ticket-analyses") or []


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


# ==================================================
# SIDEBAR NAVIGATION
# ==================================================

st.sidebar.title("🧠 ResolveIQ")
st.sidebar.caption("AI-Powered Customer Support Memory Agent")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Customers",
        "Create Ticket",
        "Ticket Management",
        "AI Support Chat",
        "Ticket Analysis"
    ]
)

st.sidebar.divider()
st.sidebar.info("ResolveIQ | Intelligent Customer Support")


# ==================================================
# 1. DASHBOARD
# ==================================================

if page == "Dashboard":

    show_page_title(
        "📊 Dashboard",
        "Monitor customer support performance and AI insights."
    )

    tickets = get_tickets()
    customers = get_customers()
    analyses = get_analyses()

    if tickets is None:
        st.stop()

    ticket_df = pd.DataFrame(tickets)

    total_tickets = len(tickets)
    total_customers = len(customers)

    open_tickets = sum(
        1 for ticket in tickets
        if ticket.get("status") == "open"
    )

    resolved_tickets = sum(
        1 for ticket in tickets
        if ticket.get("status") == "resolved"
    )

    resolution_rate = (
        round((resolved_tickets / total_tickets) * 100, 1)
        if total_tickets else 0
    )

    # KPI cards

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Total Tickets", total_tickets, "🎫")

    with c2:
        metric_card("Total Customers", total_customers, "👥")

    with c3:
        metric_card("Open Tickets", open_tickets, "📂")

    with c4:
        metric_card("Resolution Rate", f"{resolution_rate}%", "✅")

    st.divider()

    # Ticket filters

    st.subheader("🎯 Ticket Overview")

    if not ticket_df.empty:

        filter1, filter2 = st.columns(2)

        with filter1:
            status_options = ["All"] + sorted(
                ticket_df["status"].dropna().unique().tolist()
            )

            selected_status = st.selectbox(
                "Filter by Status",
                status_options
            )

        with filter2:
            priority_options = ["All"] + sorted(
                ticket_df["priority"].dropna().unique().tolist()
            )

            selected_priority = st.selectbox(
                "Filter by Priority",
                priority_options
            )

        filtered_df = ticket_df.copy()

        if selected_status != "All":
            filtered_df = filtered_df[
                filtered_df["status"] == selected_status
            ]

        if selected_priority != "All":
            filtered_df = filtered_df[
                filtered_df["priority"] == selected_priority
            ]

        # Status chart

        chart1, chart2 = st.columns(2)

        with chart1:

            status_data = (
                ticket_df["status"]
                .value_counts()
                .reset_index()
            )

            status_data.columns = ["Status", "Count"]

            fig_status = px.pie(
                status_data,
                names="Status",
                values="Count",
                hole=0.55,
                title="Ticket Status Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2
            )

            fig_status.update_layout(
                template="plotly_white",
                height=350
            )

            st.plotly_chart(
                fig_status,
                use_container_width=True
            )

        # Priority chart

        with chart2:

            priority_data = (
                ticket_df["priority"]
                .value_counts()
                .reset_index()
            )

            priority_data.columns = ["Priority", "Count"]

            fig_priority = px.bar(
                priority_data,
                x="Priority",
                y="Count",
                color="Priority",
                text="Count",
                title="Ticket Priority Distribution",
                color_discrete_sequence=px.colors.qualitative.Bold
            )

            fig_priority.update_layout(
                template="plotly_white",
                height=350,
                showlegend=False
            )

            st.plotly_chart(
                fig_priority,
                use_container_width=True
            )

        # Customer ticket chart

        if "customer_id" in ticket_df.columns:

            customer_counts = (
                ticket_df.groupby("customer_id")
                .size()
                .reset_index(name="Tickets")
            )

            customer_counts["Customer"] = (
                customer_counts["customer_id"].apply(
                    lambda customer_id: next(
                        (
                            customer.get("name", f"Customer {customer_id}")
                            for customer in customers
                            if customer.get("id") == customer_id
                        ),
                        f"Customer {customer_id}"
                    )
                )
            )

            fig_customer = px.bar(
                customer_counts.sort_values(
                    "Tickets",
                    ascending=True
                ),
                x="Tickets",
                y="Customer",
                orientation="h",
                title="Tickets by Customer",
                text="Tickets",
                color="Tickets",
                color_continuous_scale="Blues"
            )

            fig_customer.update_layout(
                template="plotly_white",
                height=350
            )

            st.plotly_chart(
                fig_customer,
                use_container_width=True
            )

        # Ticket creation trend

        if "created_at" in ticket_df.columns:

            trend_df = ticket_df.copy()

            trend_df["created_at"] = pd.to_datetime(
                trend_df["created_at"],
                errors="coerce"
            )

            trend_df = trend_df.dropna(
                subset=["created_at"]
            )

            if not trend_df.empty:

                trend_df["Date"] = (
                    trend_df["created_at"].dt.date
                )

                daily_tickets = (
                    trend_df.groupby("Date")
                    .size()
                    .reset_index(name="Tickets")
                )

                fig_trend = px.line(
                    daily_tickets,
                    x="Date",
                    y="Tickets",
                    markers=True,
                    title="Daily Ticket Creation Trend"
                )

                fig_trend.update_layout(
                    template="plotly_white",
                    height=350
                )

                st.plotly_chart(
                    fig_trend,
                    use_container_width=True
                )

        st.subheader("📋 Ticket Records")

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No tickets available. Create your first ticket.")

    # ------------------------------------------
    # AI SENTIMENT ANALYTICS
    # ------------------------------------------

    st.divider()

    st.subheader("🧠 AI Customer Sentiment Analytics")

    if st.button("🚀 Analyze All Tickets with AI"):

        if tickets:

            progress = st.progress(0)
            success_count = 0

            for index, ticket in enumerate(tickets):

                result = api_request(
                    "POST",
                    f"/tickets/{ticket['id']}/analyze"
                )

                if result is not None:
                    success_count += 1

                progress.progress(
                    (index + 1) / len(tickets)
                )

            st.success(
                f"Successfully analyzed {success_count} "
                f"out of {len(tickets)} tickets."
            )

            st.rerun()

        else:
            st.info("No tickets available for analysis.")

    # Reload saved analyses

    analyses = get_analyses()

    if analyses:

        sentiment_df = pd.DataFrame(analyses)

        sentiment_df["sentiment"] = (
            sentiment_df["sentiment"]
            .astype(str)
            .str.title()
        )

        positive = int(
            (sentiment_df["sentiment"] == "Positive").sum()
        )

        neutral = int(
            (sentiment_df["sentiment"] == "Neutral").sum()
        )

        negative = int(
            (sentiment_df["sentiment"] == "Negative").sum()
        )

        # Sentiment KPI cards

        s1, s2, s3 = st.columns(3)

        with s1:
            metric_card("Positive Sentiment", positive, "😊")

        with s2:
            metric_card("Neutral Sentiment", neutral, "😐")

        with s3:
            metric_card("Negative Sentiment", negative, "😠")

        st.write("")

        sentiment_chart, category_chart = st.columns(2)

        # Sentiment donut chart

        with sentiment_chart:

            sentiment_data = pd.DataFrame({
                "Sentiment": [
                    "Positive",
                    "Neutral",
                    "Negative"
                ],
                "Count": [
                    positive,
                    neutral,
                    negative
                ]
            })

            fig_sentiment = px.pie(
                sentiment_data,
                names="Sentiment",
                values="Count",
                hole=0.55,
                title="Customer Sentiment Distribution",
                color="Sentiment",
                color_discrete_map={
                    "Positive": "#20BF6B",
                    "Neutral": "#FFB020",
                    "Negative": "#EE4266"
                }
            )

            fig_sentiment.update_layout(
                template="plotly_white",
                height=400
            )

            st.plotly_chart(
                fig_sentiment,
                use_container_width=True
            )

        # Category chart

        with category_chart:

            category_data = (
                sentiment_df["category"]
                .value_counts()
                .reset_index()
            )

            category_data.columns = [
                "Category",
                "Tickets"
            ]

            fig_category = px.bar(
                category_data,
                x="Category",
                y="Tickets",
                color="Category",
                text="Tickets",
                title="Ticket Category Distribution",
                color_discrete_sequence=px.colors.qualitative.Bold
            )

            fig_category.update_layout(
                template="plotly_white",
                height=400,
                showlegend=False
            )

            st.plotly_chart(
                fig_category,
                use_container_width=True
            )

        # Saved analysis records

        st.subheader("📋 AI Ticket Analysis Records")

        display_columns = [
            "ticket_id",
            "category",
            "sentiment",
            "priority",
            "summary"
        ]

        st.dataframe(
            sentiment_df[display_columns],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No saved AI analysis found. "
            "Click 'Analyze All Tickets with AI' to begin."
        )


# ==================================================
# 2. CUSTOMER MANAGEMENT
# ==================================================

elif page == "Customers":

    show_page_title(
        "👥 Customer Management",
        "Create and view registered customers."
    )

    tab1, tab2 = st.tabs([
        "➕ Add Customer",
        "📋 Customer List"
    ])

    with tab1:

        st.subheader("Register New Customer")

        with st.form("customer_form"):

            name = st.text_input("Customer Name")

            email = st.text_input("Customer Email")

            submit = st.form_submit_button(
                "Create Customer",
                use_container_width=True
            )

            if submit:

                if not name.strip() or not email.strip():
                    st.warning("Please enter name and email.")

                else:

                    result = api_request(
                        "POST",
                        "/customers",
                        data={
                            "name": name,
                            "email": email
                        }
                    )

                    if result is not None:
                        st.success("Customer created successfully!")
                        st.json(result)

    with tab2:

        st.subheader("Registered Customers")

        customers = get_customers()

        if customers:

            st.dataframe(
                pd.DataFrame(customers),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No customers registered yet.")


# ==================================================
# 3. CREATE TICKET
# ==================================================

elif page == "Create Ticket":

    show_page_title(
        "🎫 Create Support Ticket",
        "Register a new customer support issue."
    )

    customers = get_customers()

    if customers:

        customer_options = {
            f"{customer['name']} ({customer['email']})":
            customer["id"]
            for customer in customers
        }

        with st.form("ticket_form"):

            selected_customer = st.selectbox(
                "Select Customer",
                list(customer_options.keys())
            )

            subject = st.text_input(
                "Ticket Subject"
            )

            description = st.text_area(
                "Describe the Issue",
                height=150
            )

            priority = st.selectbox(
                "Priority",
                ["low", "normal", "high", "urgent"]
            )

            submit = st.form_submit_button(
                "Create Ticket",
                use_container_width=True
            )

            if submit:

                if not subject.strip() or not description.strip():
                    st.warning(
                        "Please enter the subject and description."
                    )

                else:

                    result = api_request(
                        "POST",
                        "/tickets",
                        data={
                            "customer_id": customer_options[
                                selected_customer
                            ],
                            "subject": subject,
                            "description": description,
                            "priority": priority
                        }
                    )

                    if result is not None:
                        st.success("Ticket created successfully!")
                        st.json(result)

    else:

        st.warning(
            "No customers found. Please create a customer first."
        )


# ==================================================
# 4. TICKET MANAGEMENT
# ==================================================

elif page == "Ticket Management":

    show_page_title(
        "🛠️ Ticket Management",
        "Track tickets and update their status."
    )

    tickets = get_tickets()

    if tickets:

        for ticket in tickets:

            with st.container(border=True):

                col1, col2 = st.columns([3, 1])

                with col1:

                    st.markdown(
                        f"### Ticket #{ticket['id']} "
                        f"- {ticket['subject']}"
                    )

                    st.write(
                        ticket.get("description", "")
                    )

                    st.caption(
                        f"Customer ID: {ticket['customer_id']} | "
                        f"Priority: {ticket['priority']}"
                    )

                with col2:

                    st.write(
                        f"**Status:** {ticket['status']}"
                    )

                    status_options = [
                        "open",
                        "in_progress",
                        "resolved"
                    ]

                    current_status = ticket.get(
                        "status",
                        "open"
                    )

                    selected_status = st.selectbox(
                        "Update Status",
                        status_options,
                        index=(
                            status_options.index(current_status)
                            if current_status in status_options
                            else 0
                        ),
                        key=f"status_{ticket['id']}"
                    )

                    if st.button(
                        "Update Status",
                        key=f"update_{ticket['id']}"
                    ):

                        result = api_request(
                            "PATCH",
                            f"/tickets/{ticket['id']}/status",
                            params={
                                "status": selected_status
                            }
                        )

                        if result is not None:
                            st.success("Status updated!")
                            st.rerun()

                    if st.button(
                        "🧠 Analyze Ticket",
                        key=f"analyze_{ticket['id']}"
                    ):

                        result = api_request(
                            "POST",
                            f"/tickets/{ticket['id']}/analyze"
                        )

                        if result is not None:
                            st.success("AI analysis completed!")
                            st.json(result)


    else:

        st.info("No tickets available.")


# ==================================================
# 5. AI SUPPORT CHAT
# ==================================================

elif page == "AI Support Chat":

    show_page_title(
        "🤖 AI Support Chat",
        "Chat with ResolveIQ using customer-specific memory."
    )

    customers = get_customers()

    if customers:

        customer_options = {
            f"{customer['name']} ({customer['email']})":
            customer["id"]
            for customer in customers
        }

        selected_customer = st.selectbox(
            "Select Customer",
            list(customer_options.keys())
        )

        customer_id = customer_options[selected_customer]

        if "chat_histories" not in st.session_state:
            st.session_state.chat_histories = {}

        if customer_id not in st.session_state.chat_histories:
            st.session_state.chat_histories[customer_id] = []

        chat_history = st.session_state.chat_histories[
            customer_id
        ]

        # Display chat history

        for message in chat_history:

            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input

        user_input = st.chat_input(
            "Describe your customer support issue..."
        )

        if user_input:

            chat_history.append({
                "role": "user",
                "content": user_input
            })

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
                        }
                    )

                    if result is not None:

                        response_text = result.get(
                            "response",
                            "No response received."
                        )

                        previous_memories = result.get(
                            "previous_memories",
                            []
                        )

                        st.markdown(response_text)

                        if previous_memories:

                            with st.expander(
                                "🧠 Previous Customer Memories"
                            ):

                                for memory in previous_memories:
                                    st.write(f"• {memory}")

                        chat_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                    else:

                        st.error(
                            "Unable to get a response from ResolveIQ."
                        )

            st.rerun()

        if st.button("Clear Current Chat"):
            st.session_state.chat_histories[customer_id] = []
            st.rerun()

    else:

        st.warning(
            "Please create a customer before using AI Support Chat."
        )


# ==================================================
# 6. TICKET ANALYSIS
# ==================================================

elif page == "Ticket Analysis":

    show_page_title(
        "🔍 AI Ticket Analysis",
        "Analyze ticket category, sentiment, priority and summary."
    )

    tab1, tab2 = st.tabs([
        "Analyze Existing Ticket",
        "Analyze Custom Issue"
    ])

    # ------------------------------------------
    # ANALYZE EXISTING TICKET
    # ------------------------------------------

    with tab1:

        tickets = get_tickets()

        if tickets:

            ticket_options = {
                f"Ticket #{ticket['id']} - {ticket['subject']}":
                ticket
                for ticket in tickets
            }

            selected_ticket_name = st.selectbox(
                "Select Ticket",
                list(ticket_options.keys())
            )

            selected_ticket = ticket_options[
                selected_ticket_name
            ]

            st.write("**Issue Description:**")
            st.write(selected_ticket["description"])

            if st.button(
                "🧠 Analyze and Save",
                use_container_width=True
            ):

                with st.spinner("AI is analyzing the ticket..."):

                    result = api_request(
                        "POST",
                        f"/tickets/{selected_ticket['id']}/analyze"
                    )

                if result is not None:

                    st.success(
                        "Ticket analyzed and saved successfully!"
                    )

                    a1, a2, a3 = st.columns(3)

                    a1.metric(
                        "Category",
                        result.get("category", "N/A")
                    )

                    a2.metric(
                        "Sentiment",
                        result.get("sentiment", "N/A")
                    )

                    a3.metric(
                        "Priority",
                        result.get("priority", "N/A")
                    )

                    st.subheader("AI Summary")

                    st.write(
                        result.get("summary", "No summary available.")
                    )

        else:

            st.info("Create a ticket before analyzing it.")

    # ------------------------------------------
    # ANALYZE CUSTOM ISSUE
    # ------------------------------------------

    with tab2:

        st.subheader("Analyze a Custom Customer Issue")

        issue = st.text_area(
            "Enter Customer Issue",
            height=150,
            key="custom_analysis_issue"
        )

        customer_history = st.text_area(
            "Previous Customer History (Optional)",
            height=100,
            key="custom_analysis_history"
        )

        if st.button(
            "Analyze Custom Issue",
            use_container_width=True
        ):

            if not issue.strip():

                st.warning("Please enter a customer issue.")

            else:

                with st.spinner("ResolveIQ is analyzing..."):

                    result = api_request(
                        "POST",
                        "/ai/analyze",
                        data={
                            "issue": issue,
                            "customer_history": customer_history
                        }
                    )

                if result is not None:

                    st.success("AI analysis completed!")

                    if isinstance(result, dict):

                        if "category" in result:

                            st.json(result)

                        elif "response" in result:

                            st.write(result["response"])

                        else:

                            st.json(result)

                    else:

                        st.write(result)


# ==================================================
# FOOTER
# ==================================================

st.sidebar.divider()

st.sidebar.caption(
    "ResolveIQ | AI-Powered Customer Support"
)

st.sidebar.caption(
    "Built with Python, FastAPI, Streamlit, Groq and Hindsight"
)
