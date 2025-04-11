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

@st.cache_data(ttl=60)
def load_data():
    res = requests.get(sheet_url)
    return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()

def save_row(row):
    payload = {"Name": row.get("Name", ""), "Company": row.get("Company", "")}
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

# === Streamlit App Setup ===
st.set_page_config(page_title="AI Lead Dashboard", layout="wide")
st.title("📊 AI Outreach Lead Dashboard")

# === Load Data
df = load_data()

# === Filters + View Toggle
col1, col2, col3 = st.columns([3, 3, 3])
status_filter = col1.selectbox("Filter by Status", ["All", "Pending", "Processed", "Sent"])
search_term = col2.text_input("Search by Company")
view_mode = col3.radio("View Mode", ["Expanded View", "Table View"], horizontal=True)

if status_filter != "All":
    df = df[df["Status"].str.lower() == status_filter.lower()]
if search_term:
    df = df[df["Company"].str.contains(search_term, case=False)]

st.markdown(f"**{len(df)} leads matched.**")

# === Table View
if view_mode == "Table View":
    st.markdown("### 📋 Unified Table View")

    # Inject custom CSS for table styling
    st.markdown("""
    <style>
    .scroll-container {
        overflow-x: auto;
        padding: 0.5rem;
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    .table-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        padding: 0.25rem 0;
        border-bottom: 1px solid #eee;
    }
    .table-header {
        font-weight: 600;
        background-color: #f9f9f9;
        border-bottom: 2px solid #ccc;
        padding: 0.3rem 0;
    }
    .table-cell {
        min-width: 140px;
        flex: 1;
    }
    .send-btn {
        min-width: 80px !important;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # Table headers
    st.markdown("""
    <div class="scroll-container">
        <div class="table-row table-header">
            <div class="table-cell">Name</div>
            <div class="table-cell">Company</div>
            <div class="table-cell">Email</div>
            <div class="table-cell">Job Title</div>
            <div class="table-cell">Headline</div>
            <div class="table-cell">Website</div>
            <div class="table-cell">Status</div>
            <div class="table-cell">Email Draft</div>
            <div class="table-cell">Lead Score</div>
            <div class="table-cell send-btn">Send</div>
        </div>
    """, unsafe_allow_html=True)

    for i, row in df.iterrows():
        with st.container():
            cols = st.columns([1.2, 1.2, 1.8, 1.5, 1.5, 2, 1, 2.5, 0.8, 1])
            name = row.get("Name", "")
            company = row.get("Company", "")
            cols[0].markdown(f"**{name}**")
            cols[1].markdown(f"**{company}**")

            email = cols[2].text_input(f"email_{i}", value=row.get("Email", ""), label_visibility="collapsed")
            job = cols[3].text_input(f"job_{i}", value=row.get("linkedinJobTitle", ""), label_visibility="collapsed")
            headline = cols[4].text_input(f"headline_{i}", value=row.get("linkedinHeadline", ""), label_visibility="collapsed")
            website = cols[5].text_input(f"website_{i}", value=row.get("Company Website", ""), label_visibility="collapsed")
            status = cols[6].selectbox(f"status_{i}", ["Pending", "Processed", "Sent"],
                                       index=["Pending", "Processed", "Sent"].index(row.get("Status", "Pending")),
                                       label_visibility="collapsed")
            email_draft = cols[7].text_area(f"draft_{i}", value=row.get("Email Draft", ""), height=80, label_visibility="collapsed")
            try:
                score = int(row.get("Lead Score") or 0)
            except:
                score = 0
            lead_score = cols[8].number_input(f"score_{i}", value=score, step=1, label_visibility="collapsed")

            if cols[9].button("Send", key=f"send_{i}"):
                if not email:
                    st.warning("⚠️ Missing email.")
                elif not email_draft:
                    st.warning("⚠️ Missing draft.")
                else:
                    success, result = send_email(email, f"Quick note for {company}", email_draft)
                    if success:
                        row.update({
                            "Email": email,
                            "Status": "Sent",
                            "linkedinJobTitle": job,
                            "linkedinHeadline": headline,
                            "Company Website": website,
                            "Email Draft": email_draft,
                            "Lead Score": lead_score
                        })
                        if save_row(row):
                            st.success(f"✅ Email sent to {email}")
                            st.rerun()
                        else:
                            st.warning("⚠️ Sent but failed to update sheet.")
                    else:
                        st.error(f"❌ Failed: {result}")

    st.markdown("</div>", unsafe_allow_html=True)

# === Expanded View
else:
    st.markdown("### 🔍 Expanded View (1 per lead)")
    st.markdown("<div style='overflow-x:auto;'>", unsafe_allow_html=True)

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

            email = st.text_input(f"Email_{i}", value=row.get("Email") or "")
            status = st.selectbox(f"Status_{i}", ["Pending", "Processed", "Sent"], index=["Pending", "Processed", "Sent"].index(row.get("Status", "Pending")))
            email_draft = st.text_area(f"Email Draft_{i}", value=row.get("Email Draft") or "", height=120)
            try:
                score = int(row.get("Lead Score") or 0)
            except:
                score = 0
            lead_score = st.number_input(f"Lead Score_{i}", value=score, step=1)
            ai_summary = row.get("AI Summary", "")
            st.text_area("🧠 AI Summary", value=ai_summary if ai_summary else "No summary generated.", height=100, disabled=True, key=f"ai_summary_{i}")

            if st.button(f"📤 Send Now to {email}", key=f"send_exp_{i}"):
                if not email:
                    st.warning("⚠️ Missing email.")
                elif not email_draft:
                    st.warning("⚠️ Missing draft.")
                else:
                    success, result = send_email(email, f"Quick note for {row.get('Company', '')}", email_draft)
                    if success:
                        row.update({
                            "Email": email,
                            "Status": "Sent",
                            "Email Draft": email_draft,
                            "Lead Score": lead_score
                        })
                        if save_row(row):
                            st.success("✅ Email sent and sheet updated.")
                            st.rerun()
                        else:
                            st.warning("⚠️ Sent, but failed to update sheet.")
                    else:
                        st.error(f"❌ Failed to send email: {result}")

    st.markdown("</div>", unsafe_allow_html=True)
