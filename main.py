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
        "Name": row["Name"],
        "Company": row["Company"]
    }
    update = {
        "AI Summary": row["AI Summary"],
        "Email Draft": row["Email Draft"],
        "Lead Score": int(row["Lead Score"]) if row["Lead Score"] else 0,
        "Status": row["Status"],
        "Email": row.get("Email", "")
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

# === Editable Data Table ===
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "AI Summary": st.column_config.TextColumn(width="medium"),
        "Email Draft": st.column_config.TextColumn(width="large"),
        "Lead Score": st.column_config.NumberColumn(format="%d")
    }
)

# === Save Button ===
if st.button("💾 Save All Changes to Google Sheet"):
    with st.spinner("Saving..."):
        success_count = 0
        for _, row in edited_df.iterrows():
            if save_row(row):
                success_count += 1
        st.success(f"✅ {success_count} rows updated successfully!")

# === Manual Send Section ===
st.subheader("📨 Send Emails Manually")

for i, row in edited_df.iterrows():
    if row["Status"].lower() != "sent":
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            **{row['Name']}** at **{row['Company']}**  
            ✉️ Email: `{row.get('Email', 'Not provided')}`  
            📄 **Draft Preview:**  
            `{row['Email Draft'][:120] if row['Email Draft'] else '[No Draft]'}`
            """)
        with col2:
            if st.button("Send Now", key=f"send_{i}"):
                if not row.get("Email"):
                    st.warning(f"⚠️ No email address for {row['Name']}")
                elif not row.get("Email Draft"):
                    st.warning(f"⚠️ No email draft for {row['Name']}")
                else:
                    success, result = send_email(
                        to_email=row["Email"],
                        subject=f"Quick note for {row['Company']}",
                        message_body=row["Email Draft"]
                    )
                    if success:
                        row["Status"] = "Sent"
                        save_row(row)
                        st.success(f"✅ Email sent to {row['Email']}")
                    else:
                        st.error(f"❌ Failed to send: {result}")
