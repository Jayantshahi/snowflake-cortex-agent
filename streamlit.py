import streamlit as st
import pandas as pd
import json

# Title and Sidebar
st.set_page_config(page_title="Snowflake LLM Chatbot", layout="wide")
st.title("💬 LLM-Powered SQL Chatbot with Cortex Search")

with st.sidebar:
    st.markdown("## 🗂️ App Configuration")
    st.info("You're using your Snowflake Project context and database.")
    if st.button("Reset Conversation", key="reset"):
        st.session_state.messages = []
        st.rerun()

# Ensure message history is initialized
if "messages" not in st.session_state:
    st.session_state.messages = []

def run_agent(query: str):
    """
    Calls the Cortex LLM agent on Snowflake via the SQL EXECUTE FUNCTION method.
    Modify this block if you use a different invocation setup for Cortex.
    """

    # Get the active session. Adjust if needed for your environment.
    session = st.connection("snowflake")  # provided by Snowflake Streamlit

    # Your semantic model, cortex search, and related configs
    SEMANTIC_MODEL = "@sales_intelligence.data.models/sales_metrics_model.yaml"
    CORTEX_SEARCH_SERVICE = "sales_intelligence.data.sales_conversation_search"

    # The function below is provided as a template; you might need to adjust for your actual Cortex LLM endpoint.
    # We'll use a hypothetical SQL UDF called AGENT_EXECUTE, adjust if you have a different implementation.
    # Suppose you installed Cortex agent function as: cortex_agent_fn('query')
    try:
        # For demonstration, replace with your actual Cortex/UDF invocation.
        # This just runs as SQL against your database schema.
        cortex_sql = f"SELECT cortex_complete('{query}', '{SEMANTIC_MODEL}', '{CORTEX_SEARCH_SERVICE}') AS response"
        result = session.query(cortex_sql)
        data = result.to_pandas()
        # Extract text output (if JSON is returned, parse accordingly)
        answer_raw = data['RESPONSE'][0]
        try:
            # Some LLMs return a stringified dict
            answer = json.loads(answer_raw)
        except Exception:
            answer = answer_raw
        return answer
    except Exception as e:
        return f"❌ Error from Cortex/Agent: {str(e)}"

def plot_if_possible(agent_response):
    """Tries to plot results if agent response is a valid SQL table or JSON result."""
    # If it looks like a markdown table or JSON, try to parse it
    if isinstance(agent_response, pd.DataFrame):
        st.dataframe(agent_response)
        try:
            st.bar_chart(agent_response)
        except Exception:
            pass
    elif isinstance(agent_response, dict):
        df = pd.DataFrame(agent_response)
        st.dataframe(df)
        try:
            st.bar_chart(df)
        except Exception:
            pass
    elif isinstance(agent_response, str) and agent_response.startswith("[") and agent_response.endswith("]"):
        try:
            df = pd.DataFrame(json.loads(agent_response))
            st.dataframe(df)
            try:
                st.bar_chart(df)
            except Exception:
                pass
        except Exception:
            pass
    # Otherwise: just print the output
    else:
        st.markdown(agent_response)

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        plot_if_possible(msg['content'])

# The chat input
user_input = st.chat_input("Type your business/SQL/analytics question and press Enter...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("👩‍💻 Thinking..."):
        # Call your agent for a response
        agent_response = run_agent(user_input)

    # Show assistant reply and possibly plot
    with st.chat_message("assistant"):
        plot_if_possible(agent_response)

    st.session_state.messages.append({"role": "assistant", "content": agent_response})
