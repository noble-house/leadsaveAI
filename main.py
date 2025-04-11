import streamlit as st
import pandas as pd
import requests

# === SendGrid Email Sender ===
def send_email(to_email, subject, message_body):
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {st.secrets['sendgrid']['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "personalizations": [{
                    "to": [{"email": to_email}]
                }],
                "from": {"email": st.secrets['sendgrid']['from_email']},
                "subject": subject,
                "content": [{
                    "type": "text/plain",
                    "value": message_body
                }]
            }
        )
        if response.status_code == 202:
            return True, "Sent successfully"
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

# === Google Sheet API Endpoint ===
sheet_url = "https://api.sheetbest.com/sheets/8e32f642-267a-4b79-a5f1-349733d44d71"

# === Load and Save Sheet Data ===
@st.cache_data(ttl=60)
def load_data():
    res = requests.get(sheet_url)
    return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()

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

# === Streamlit App ===
st.set_page_config(page_title="AI Lead Dashboard", layout="wide")
st.markdown("<h1 style='margin-bottom:1rem;'>📊 AI Outreach Lead Dashboard</h1>", unsafe_allow_html=True)

df = load_data()

# === Top Filters ===
col1, col2 = st.columns(2)
status_filter = col1.selectbox("Filter by Status", ["All", "Pending", "Processed", "Sent"])
search_term = col2.text_input("Search by Company")

if status_filter != "All":
    df = df[df["Status"].str.lower() == status_filter.lower()]
if search_term:
    df = df[df["Company"].str.contains(search_term, case=False)]

st.markdown(f"**{len(df)} leads matched. Scroll down and right → to view/edit.**")
st.markdown("<div style='overflow-x:auto;'>", unsafe_allow_html=True)

# === Lead Rows ===
for i, row in df.iterrows():
    with st.expander(f"💼 {row.get('Company', '')} — {row.get('Name', '')}"):
        col1, col2, col3 = st.columns([2, 2, 6])
        col1.write(f"**Email:** {row.get('Email') or 'N/A'}")
        col2.write(f"**Status:** {row.get('Status') or 'Pending'}")
        col3.write(f"**LinkedIn:** {row.get('LinkedIn URL') or 'N/A'}")

        col4, col5, col6 = st.columns(3)
        col4.write(f"**Job Title:** {row.get('linkedinJobTitle', '')}")
        col5.write(f"**Headline:** {row.get('linkedinHeadline', '')}")
        col6.write(f"**Website:** {row.get('Company Website', '')}")

        # === Editable Fields
        email = st.text_input(f"Email_{i}", value=row.get("Email") or "")
        status_options = ["Pending", "Processed", "Sent"]
        status = st.selectbox(f"Status_{i}", status_options,
                              index=status_options.index(row.get("Status", "Pending")) if row.get("Status") in status_options else 0)
        email_draft = st.text_area(f"Email Draft_{i}", value=row.get("Email Draft") or "", height=120)

        try:
            lead_score = int(row.get("Lead Score") or 0)
        except:
            lead_score = 0
        score = st.number_input(f"Lead Score_{i}", value=lead_score, step=1)

        # === Read-only AI Summary
        ai_summary = row.get("AI Summary", "")
        st.text_area("🧠 AI Summary", value=ai_summary if ai_summary else "No summary generated.", height=100, disabled=True, key=f"ai_summary_{i}")

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
                    row["Lead Score"] = score
                    if save_row(row):
                        st.success("✅ Email sent and sheet updated.")
                        st.experimental_rerun()  # 🔁 Force UI refresh
                    else:
                        st.warning("⚠️ Email sent, but failed to update sheet.")
                else:
                    st.error(f"❌ Failed to send email: {result}")

st.markdown("</div>", unsafe_allow_html=True)
