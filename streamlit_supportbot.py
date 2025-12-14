# streamlit_dialogflow_final.py
import streamlit as st
import os, json, re
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# -------- CONFIG --------
LOGO_PATH = "/mnt/data/8d2549da-e39a-4651-ae15-7337e54a3fc2.png"

# FIXED WINDOWS PATH WITH RAW STRING
LOCAL_SA_PATH = r"D:\Future Interns\cust-supportbot-jpsj-38fcbd179cea.json"

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
DIALOGFLOW_BASE = "https://dialogflow.googleapis.com/v2"

st.set_page_config(page_title="SupportBot • Live", page_icon="🤖", layout="wide")

# -------- Helpers --------
def load_logo():
    return LOGO_PATH if os.path.exists(LOGO_PATH) else None

def load_creds_from_file(path):
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

def load_creds_from_json_str(json_str):
    return service_account.Credentials.from_service_account_info(json.loads(json_str), scopes=SCOPES)

def detect_intent(project_id: str, session_id: str, text: str, language_code: str, creds):
    authed = AuthorizedSession(creds)
    url = f"{DIALOGFLOW_BASE}/projects/{project_id}/agent/sessions/{session_id}:detectIntent"
    body = {"query_input": {"text": {"text": text, "language_code": language_code}}}
    r = authed.post(url, json=body, timeout=20)
    r.raise_for_status()
    resp = r.json()

    texts = []
    for m in resp.get("queryResult", {}).get("fulfillmentMessages", []):
        if "text" in m and "text" in m["text"]:
            texts.extend(m["text"]["text"])

    return " ".join(texts) if texts else resp.get("queryResult", {}).get("fulfillmentText", "")


# -------- UI --------
def header():
    st.markdown("<br>", unsafe_allow_html=True)
    cols = st.columns([1,6,1])
    with cols[1]:
        logo = load_logo()
        if logo:
            st.image(logo, width=72)
        st.markdown("<h2 style='text-align:center;margin-top:6px;'>SupportBot — Live</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:gray;margin-top:-6px;'>Professional Dialogflow integration (DetectIntent)</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

def chat_area(project_id, creds):
    if "messages" not in st.session_state:
        st.session_state.messages = [{"from":"bot","text":"Hi — I'm SupportBot. Ask about orders, cancellations, or delivery."}]

    left, right = st.columns([0.72, 0.28])

    # ------- Chat Window ------
    with left:
        for m in st.session_state.messages:
            if m["from"] == "user":
                st.markdown(
                    f"<div style='text-align:right;margin:6px'><div style='display:inline-block;background:#0ea5a4;color:#fff;padding:10px;border-radius:10px;max-width:78%'>{m['text']}</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='text-align:left;margin:6px'><div style='display:inline-block;background:#f1f5f9;color:#0f172a;padding:10px;border-radius:10px;max-width:78%'>{m['text']}</div></div>",
                    unsafe_allow_html=True
                )

        # ------- User Input ------
        with st.form("msg_form", clear_on_submit=True):
            txt = st.text_input("Type your message", "")
            send = st.form_submit_button("Send")

            if send and txt.strip():
                st.session_state.messages.append({"from":"user","text":txt})

                try:
                    session_id = "sess-" + re.sub(r"\W+", "", txt)[:20]
                    reply = detect_intent(project_id, session_id, txt, "en", creds)
                except Exception as e:
                    reply = f"[Error] {e}"

                st.session_state.messages.append({"from":"bot","text":reply})

                st.rerun()  # FIXED


    # ------- Sidebar Buttons ------
    with right:
        st.markdown("### Controls")
        st.markdown("- Enter project ID in sidebar\n- Upload JSON if automatic load fails")

        if st.button("Quick: Track my order"):
            st.session_state.messages.append({"from":"user","text":"track my order 12345"})
            try:
                reply = detect_intent(project_id, "quick-track", "track my order 12345", "en", creds)
            except Exception as e:
                reply = f"[Error] {e}"

            st.session_state.messages.append({"from":"bot","text":reply})
            st.rerun()  # FIXED


# -------- MAIN --------
def main():
    header()
    st.sidebar.title("Dialogflow Setup")

    project_id = st.sidebar.text_input("GCP Project ID (Dialogflow)", value="", help="Copy from Dialogflow → Settings")

    creds = None
    used_source = None

    # 1) Auto-load from local path
    if os.path.exists(LOCAL_SA_PATH):
        try:
            creds = load_creds_from_file(LOCAL_SA_PATH)
            used_source = "Local JSON Path"
            st.sidebar.success(f"Loaded credentials from {LOCAL_SA_PATH}")
        except Exception as e:
            st.sidebar.error(f"Local JSON error: {e}")

    # 2) Upload JSON manually
    if creds is None:
        uploaded = st.sidebar.file_uploader("Upload service-account JSON", type=["json"])
        if uploaded:
            try:
                creds = load_creds_from_json_str(uploaded.read().decode("utf-8"))
                used_source = "Uploaded JSON"
                st.sidebar.success("Credentials loaded from upload.")
            except Exception as e:
                st.sidebar.error(f"Upload failed: {e}")

    # 3) Use Streamlit Secrets
    if creds is None and st.sidebar.checkbox("Use Streamlit Secrets (Cloud)", value=False):
        sa_json = st.secrets.get("DIALOGFLOW_SA_JSON", None)
        if sa_json:
            try:
                creds = load_creds_from_json_str(sa_json)
                used_source = "Streamlit Secrets"
                st.sidebar.success("Loaded credentials from secrets.")
            except Exception as e:
                st.sidebar.error(f"Secrets error: {e}")
        else:
            st.sidebar.info("Add DIALOGFLOW_SA_JSON to Secrets.")

    if not project_id:
        st.info("Enter your Dialogflow PROJECT ID in sidebar.")
        return

    if creds is None:
        st.warning("No credentials loaded. Upload JSON or fix path.")
        return

    st.sidebar.markdown(f"**Using credentials from:** {used_source}")
    chat_area(project_id, creds)


if __name__ == "__main__":
    main()
