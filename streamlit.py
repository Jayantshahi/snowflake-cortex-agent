import json
import requests
import streamlit as st

# These constants are project-specific or API-specific:
AGENT_API_ENDPOINT = "/api/v2/cortex/agent:run"
API_TIMEOUT = 50000  # in milliseconds
CORTEX_SEARCH_SERVICES = "sales_intelligence.data.sales_conversation_search"
SEMANTIC_MODELS = "@sales_intelligence.data.models/sales_metrics_model.yaml"
WAREHOUSE = "SALES_INTELLIGENCE_WH"

def run_snowflake_query(query):
    try:
        df = session.sql(query.replace(';',''))
        return df
    except Exception as e:
        st.error(f"Error executing SQL: {str(e)}")
        return None

def agent_api_call(query: str, limit: int = 10):
    payload = {
        "model": "llama3.1-70b",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": query}
                ]
            }
        ],
        "tools": [
            {"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "analyst1"}},
            {"tool_spec": {"type": "cortex_search", "name": "search1"}}
        ],
        "tool_resources": {
            "analyst1": {"semantic_model_file": SEMANTIC_MODELS},
            "search1": {
                "name": CORTEX_SEARCH_SERVICES,
                "max_results": limit
            }
        }
    }
    # The Snowflake access token is automatically handled in projects. 
    # You might not need to add any Authorization/Token header!
    try:
        host_url = f"https://{st.query_params.account_locator}.snowflakecomputing.com"
    except Exception:
        host_url = ""  # fallback to blank (may need to update this depending on your API endpoint location)

    try:
        resp = requests.post(
            url=f"{host_url}{AGENT_API_ENDPOINT}",
            json=payload,
            timeout=API_TIMEOUT / 1000  # Convert ms to seconds
        )
    except Exception as e:
        return f"API call failed: {str(e)}"
    if resp.status_code < 400:
        try:
            parsed = resp.json()
            # Adjust extraction logic according to actual API response JSON
            return json.dumps(parsed, indent=2)
        except Exception as e:
            return f"Failed to parse API response: {str(e)}"
    else:
        return f"Error from API: {resp.status_code} - {resp.text}"

def main():
    global session

    with st.sidebar:
        if st.button("Reset Conversation", key="new_chat"):
            st.session_state.messages = []
            st.rerun()

    st.title("Intelligent Sales Assistant")

    # Get built-in session for Snowflake Streamlit
    try:
        session = st.connection("snowflake")
    except Exception as e:
        st.error(f"Could not get session: {e}")
        return

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'].replace("•", "\n\n-"))

    user_input = st.chat_input("What is your question?")
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("Processing your request..."):
            response = agent_api_call(user_input, 1)
        with st.chat_message("assistant"):
            st.markdown(str(response))
        st.session_state.messages.append({"role": "assistant", "content": str(response)})

if __name__ == "__main__":
    main()
