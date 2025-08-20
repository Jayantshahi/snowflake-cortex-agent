import json
import requests
import streamlit as st
import snowflake.connector

# Snowflake secrets/connection details are loaded from st.secrets
HOST = st.secrets["snowflake"]["host"]
ACCOUNT = st.secrets["snowflake"]["account"]
USER = st.secrets["snowflake"]["user"]
PASSWORD = st.secrets["snowflake"]["password"]
ROLE = st.secrets["snowflake"]["role"]
WAREHOUSE = "SALES_INTELLIGENCE_WH"

AGENT_API_ENDPOINT = "/api/v2/cortex/agent:run"
API_TIMEOUT = 50000  # in milliseconds

CORTEX_SEARCH_SERVICES = "sales_intelligence.data.sales_conversation_search"
SEMANTIC_MODELS = "@sales_intelligence.data.models/sales_metrics_model.yaml"

# Make sure session is initialized
session = None

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
                    {
                        "type": "text",
                        "text": query
                    }
                ]
            }
        ],
        "tools": [
            {
                "tool_spec": {
                    "type": "cortex_analyst_text_to_sql",
                    "name": "analyst1"
                }
            },
            {
                "tool_spec": {
                    "type": "cortex_search",
                    "name": "search1"
                }
            }
        ],
        "tool_resources": {
            "analyst1": {"semantic_model_file": SEMANTIC_MODELS},
            "search1": {
                "name": CORTEX_SEARCH_SERVICES,
                "max_results": limit
            }
        }
    }

    # Send a POST request
    try:
        resp = requests.post(
            url=f"https://{HOST}{AGENT_API_ENDPOINT}",
            json=payload,
            headers={
                "Authorization": f'Snowflake Token=\"{st.session_state.CONN.rest.token}\"',
                "Content-Type": "application/json",
            },
            timeout=API_TIMEOUT / 1000  # Convert ms to seconds
        )
    except Exception as e:
        return f"API call failed: {str(e)}"

    if resp.status_code < 400:
        try:
            parsed = resp.json()
            # Try to extract primary text reply
            # Update this key-path as per your actual API structure!
            if "delta" in parsed and "content" in parsed["delta"]:
                contents = parsed["delta"]["content"]
                if contents and isinstance(contents, list) and "text" in contents[0]:
                    return contents["text"]
            # Alternate generic stringification fallback
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

    # connection
    if 'CONN' not in st.session_state or st.session_state.CONN is None:
        try:
            st.session_state.CONN = snowflake.connector.connect(
                user=USER,
                password=PASSWORD,
                account=ACCOUNT,
                host=HOST,
                port=443,
                role=ROLE,
                warehouse=WAREHOUSE
            )
            session = st.session_state.CONN
            st.info('Snowflake Connection established!', icon="💡")
        except Exception as e:
            st.error('Connection not established. Check your Snowflake credentials!', icon="🚨")
            return

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'].replace("•", "\n\n-"))

    user_input = st.chat_input("What is your question?")
    if user_input:
        # Add user message to chat
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Get response from API
        with st.spinner("Processing your request..."):
            response = agent_api_call(user_input, 1)
        with st.chat_message("assistant"):
            st.markdown(str(response))
        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": str(response)})

if __name__ == "__main__":
    main()
