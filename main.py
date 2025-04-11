import streamlit as st
import pandas as pd
import requests
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === Gmail Email Sender ===
def send_email(to_email, subject, message_body):
    try:
        creds = Credentials(
            None,
            client_id=st.secrets["gmail"]["client_id"],
            client_secret=st.secrets["gmail"]["client_secret"],
            token_uri=st.secrets["gmail"]["token_uri"],
        )

        message = MIMEText(message_body)
        message["to"] = to_email
        message["from"] = "me"
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service = build("gmail", "v1", credentials=creds)
        send = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        return True, send["id"]

    except Exception as e:
        return False, str(e)

# === Sheet.best API endpoint ===
sheet_url = "https://api.sheetbest.com/sheets/8e32f642-267a-4b79-a5f1-349733d44d71"

# === Load Data from Google Sheet ===
@st.cache_data(ttl=60)
def load_data():
    response = requests.get(sheet_url)
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        st.error("Failed to load data.")
        return pd.DataFrame()

# === Save Changes to Google Sheet ===
def save_row(row):
    payload = {
        "Name": row.get("Name", ""),
        "Company": row.get("Company", "")
    }
    update = {
        "Email": row.get("Email", ""),
        "LinkedIn URL": row.get("LinkedIn URL", ""),
        "linkedinJobTitle": row.get("linkedinJobTitle", ""),
        "linkedinHeadline": row.get("linkedinHeadline", ""),
        "Company Website": row.get("Company Website", ""),
        "Status": row.get("Status", ""),
        "AI Summary": row.get("AI Summary", ""),
        "Email Draft": row.get("Email Draft", ""),
        "Lead Score": int(row.get("Lead Score") or 0)
    }
    patch = requests.patch(f"{sheet_url}/search", params=payload, json=update)
    return patch.status_code == 200

# === Streamlit UI ===
st.set_page_config(page_title="AI Lead Dashboard", layout="wide")
st.title("📊 AI Outreach Lead Dashboard")

df = load_data()

# === Filter Sidebar ===
st.sidebar.header("🔍 Filter Leads")
status_filter = st.sidebar.selectbox("Filter by Status", options=["All", "Pending", "Processed", "Sent"])
search_term = st.sidebar.text_input("Search by Company Name")

if status_filter != "All":
    df = df[df["Status"].str.lower() == status_filter.lower()]
if search_term:
    df = df[df["Company"].str.contains(search_term, case=False)]

st.markdown(f"**Showing {len(df)} leads**")

# === Table Header ===
header = st.columns([1.2, 1.2, 1.8, 1.8, 1.5, 1.5, 2, 1, 2.5, 3, 0.8, 1])
headers = [
    "👤 Name", "🏢 Company", "✉️ Email", "🔗 LinkedIn", "💼 Job Title",
    "📝 Headline", "🌐 Website", "📌 Status", "🧠 AI Summary", "📄 Email Draft", "⭐ Score", "🚀 Action"
]
for col, label in zip(header, headers):
    col.markdown(f"**{label}**")

# === Table Body ===
for i, row in df.iterrows():
    cols = st.columns([1.2, 1.2, 1.8, 1.8, 1.5, 1.5, 2, 1, 2.5, 3, 0.8, 1])

    # Read-only
    cols[0].markdown(row.get("Name", ""))
    cols[1].markdown(row.get("Company", ""))
    cols[3].markdown(row.get("LinkedIn URL", ""))
    cols[4].markdown(row.get("linkedinJobTitle", ""))
    cols[5].markdown(row.get("linkedinHeadline", ""))
    cols[6].markdown(row.get("Company Website", ""))

    ai_summary = row.get("AI Summary", "")
    cols[8].markdown((ai_summary[:150] + "...") if isinstance(ai_summary, str) and ai_summary else "[No Summary]")

    # === Editable Fields with Safe Defaults ===
    email = cols[2].text_input(f"email_{i}", value=row.get("Email") or "", label_visibility="collapsed")

    current_status = row.get("Status", "Pending")
    status_options = ["Pending", "Processed", "Sent"]
    status_index = status_options.index(current_status) if current_status in status_options else 0
    status = cols[7].selectbox(f"status_{i}", options=status_options, index=status_index, label_visibility="collapsed")

    email_draft = cols[9].text_area(f"draft_{i}", value=row.get("Email Draft") or "", height=80, label_visibility="collapsed")

    try:
        score_value = int(row.get("Lead Score") or 0)
    except:
        score_value = 0
    lead_score = cols[10].number_input(f"score_{i}", value=score_value, step=1, label_visibility="collapsed")

    # === Send Now Button ===
    if cols[11].button("Send Now", key=f"send_{i}"):
        if not email:
            st.warning(f"⚠️ No email for {row.get('Name', 'Unknown')}")
        elif not email_draft:
            st.warning(f"⚠️ No draft for {row.get('Name', 'Unknown')}")
        else:
            success, result = send_email(
                to_email=email,
                subject=f"Quick note for {row.get('Company', 'your business')}",
                message_body=email_draft
            )
            if success:
                row["Email"] = email
                row["Status"] = "Sent"
                row["Email Draft"] = email_draft
                row["Lead Score"] = lead_score
                if save_row(row):
                    st.success(f"✅ Email sent to {email}")
                else:
                    st.warning("⚠️ Email sent, but failed to update sheet.")
            else:
                st.error(f"❌ Failed to send: {result}")
