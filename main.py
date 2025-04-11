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
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": st.secrets["sendgrid"]["from_email"]},
                "subject": subject,
                "content": [{"type": "text/plain", "value": message_body}]
            }
        )
        return response.status_code == 202, response.text
    except Exception as e:
        return False, str(e)

# === Google Sheet Endpoint ===
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

# === Style Fixes (CRM Look) ===
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    .crm-card {
        background-color: #ffffff;
        border: 1px solid #e2e2e2;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        transition: 0.2s ease;
    }
    .crm-card:hover {
        background-color: #f9f9f9;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    textarea, input {
        font-size: 14px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 AI Outreach Lead Dashboard")

df = load_data()

col1, col2, col3 = st.columns(3)
status_filter = col1.selectbox("📌 Filter by Status", ["All", "Pending", "Processed", "Sent"])
search_term = col2.text_input("🔍 Search by Company")
view_mode = col3.radio("🖥️ View Mode", ["Expanded View", "Table View"], horizontal=True)

if status_filter != "All":
    df = df[df["Status"].str.lower() == status_filter.lower()]
if search_term:
    df = df[df["Company"].str.contains(search_term, case=False)]

st.markdown(f"**{len(df)} leads matched.**")

# === Sleek Table View
if view_mode == "Table View":
    for i, row in df.iterrows():
        st.markdown('<div class="crm-card">', unsafe_allow_html=True)
        cols = st.columns([1.5, 1.5, 2, 1.5, 1.5, 2, 1, 3, 0.8, 1])

        name = row.get("Name", "")
        company = row.get("Company", "")
        email = row.get("Email", "")
        job = row.get("linkedinJobTitle", "")
        headline = row.get("linkedinHeadline", "")
        website = row.get("Company Website", "")
        status = row.get("Status", "Pending")
        email_draft = row.get("Email Draft", "")
        score = int(row.get("Lead Score") or 0)

        cols[0].text_input("Name", value=name, key=f"name_{i}", disabled=True)
        cols[1].text_input("Company", value=company, key=f"company_{i}", disabled=True)
        new_email = cols[2].text_input("Email", value=email, key=f"email_{i}")
        new_job = cols[3].text_input("Job Title", value=job, key=f"job_{i}")
        new_headline = cols[4].text_input("Headline", value=headline, key=f"headline_{i}")
        new_website = cols[5].text_input("Website", value=website, key=f"website_{i}")
        new_status = cols[6].selectbox("Status", ["Pending", "Processed", "Sent"],
                                       index=["Pending", "Processed", "Sent"].index(status), key=f"status_{i}")
        new_draft = cols[7].text_area("Email Draft", value=email_draft, height=100, key=f"draft_{i}")
        new_score = cols[8].number_input("Score", value=score, step=1, key=f"score_{i}")

        if cols[9].button("📤", key=f"send_{i}"):
            if not new_email:
                st.warning(f"⚠️ Email missing for {name}")
            elif not new_draft:
                st.warning(f"⚠️ Draft missing for {name}")
            else:
                success, result = send_email(new_email, f"Quick note for {company}", new_draft)
                if success:
                    row.update({
                        "Email": new_email,
                        "Status": "Sent",
                        "linkedinJobTitle": new_job,
                        "linkedinHeadline": new_headline,
                        "Company Website": new_website,
                        "Email Draft": new_draft,
                        "Lead Score": new_score
                    })
                    if save_row(row):
                        st.success(f"✅ Email sent to {new_email}")
                        st.rerun()
                    else:
                        st.warning("⚠️ Sent but sheet not updated.")
                else:
                    st.error(f"❌ Failed: {result}")
        st.markdown('</div>', unsafe_allow_html=True)

# === Expanded View
else:
    st.markdown("### 🔍 Expanded View (1 per lead)")
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
            status = st.selectbox(f"Status_{i}", ["Pending", "Processed", "Sent"],
                                  index=["Pending", "Processed", "Sent"].index(row.get("Status", "Pending")))
            email_draft = st.text_area(f"Email Draft_{i}", value=row.get("Email Draft") or "", height=120)
            score = int(row.get("Lead Score") or 0)
            lead_score = st.number_input(f"Lead Score_{i}", value=score, step=1)
            ai_summary = row.get("AI Summary", "")
            st.text_area("🧠 AI Summary", value=ai_summary if ai_summary else "No summary generated.",
                         height=100, disabled=True, key=f"ai_summary_{i}")

            if st.button(f"📤 Send Now to {email}", key=f"send_exp_{i}"):
                if not email:
                    st.warning("Missing email.")
                elif not email_draft:
                    st.warning("Missing draft.")
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
                            st.warning("Sent, but failed to update sheet.")
                    else:
                        st.error(f"❌ Failed to send email: {result}")
