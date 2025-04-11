import streamlit as st
import pandas as pd
import requests
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# === Gmail Sender ===
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

# === Google Sheet API Endpoint ===
sheet_url = "https://api.sheetbest.com/sheets/8e32f642-267a-4b79-a5f1-349733d44d71"

# === Load Sheet Data ===
@st.cache_data(ttl=60)
def load_data():
    res = requests.get(sheet_url)
    return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()

# === Update Sheet Row ===
def save_row(row):
    payload = { "Name": row.get("Name", ""), "Company": row.get("Company", "") }
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
    return requests.patch(f"{sheet_url}/search", params=payload, json=update).status_code == 200

# === Streamlit UI Setup ===
st.set_page_config(page_title="AI Lead Dashboard", layout="wide")
st.markdown("<h1 style='margin-bottom:1rem;'>📊 AI Outreach Lead Dashboard</h1>", unsafe_allow_html=True)

df = load_data()

# === Filters on Top ===
col_filter1, col_filter2 = st.columns([3, 3])
status_filter = col_filter1.selectbox("Filter by Status", options=["All", "Pending", "Processed", "Sent"])
search_term = col_filter2.text_input("Search by Company")

if status_filter != "All":
    df = df[df["Status"].str.lower() == status_filter.lower()]
if search_term:
    df = df[df["Company"].str.contains(search_term, case=False)]

st.markdown(f"**{len(df)} leads matched. Scroll down and right → to view/edit.**")

# === Scrollable Table Area ===
st.markdown("<div style='overflow-x:auto;'>", unsafe_allow_html=True)

for i, row in df.iterrows():
    with st.expander(f"💼 {row.get('Company', '')} — {row.get('Name', '')}"):
        col1, col2, col3 = st.columns([2, 2, 6])
        col1.write(f"**Email:** {row.get('Email') or 'N/A'}")
        col2.write(f"**Status:** {row.get('Status') or 'Pending'}")
        col3.write(f"**LinkedIn:** {row.get('LinkedIn URL') or 'N/A'}")

        col4, col5, col6 = st.columns([2, 2, 2])
        col4.write(f"**Job Title:** {row.get('linkedinJobTitle', '')}")
        col5.write(f"**Headline:** {row.get('linkedinHeadline', '')}")
        col6.write(f"**Website:** {row.get('Company Website', '')}")

        # === Editable Fields
        email = st.text_input(f"Email_{i}", value=row.get("Email") or "")
        status_options = ["Pending", "Processed", "Sent"]
        status_index = status_options.index(row.get("Status", "Pending")) if row.get("Status", "Pending") in status_options else 0
        status = st.selectbox(f"Status_{i}", status_options, index=status_index)

        email_draft = st.text_area(f"Email Draft_{i}", value=row.get("Email Draft") or "", height=120)

        try:
            score_value = int(row.get("Lead Score") or 0)
        except:
            score_value = 0
        lead_score = st.number_input(f"Lead Score_{i}", value=score_value, step=1)

        # === Read-only AI Summary
        ai_summary = row.get("AI Summary", "")
        st.text_area(
            label="🧠 AI Summary",
            value=ai_summary if ai_summary else "No summary generated.",
            height=100,
            disabled=True,
            key=f"ai_summary_{i}"  # ✅ Unique key fix
        )

        # === Send Now
        if st.button(f"📤 Send Now to {email}", key=f"send_{i}"):
            if not email:
                st.warning("⚠️ Missing email.")
            elif not email_draft:
                st.warning("⚠️ Missing draft.")
            else:
                success, result = send_email(email, f"Quick note for {row.get('Company', '')}", email_draft)
                if success:
                    row["Email"] = email
                    row["Status"] = "Sent"
                    row["Email Draft"] = email_draft
                    row["Lead Score"] = lead_score
                    if save_row(row):
                        st.success("✅ Email sent and sheet updated.")
                    else:
                        st.warning("⚠️ Email sent, but failed to update sheet.")
                else:
                    st.error(f"❌ Failed to send email: {result}")

st.markdown("</div>", unsafe_allow_html=True)
