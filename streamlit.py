import streamlit as st
import pandas as pd

st.set_page_config(page_title="Snowflake LLM Chatbot", layout="wide")
st.title("💬 LLM-Powered SQL Chatbot on Your Data")

with st.sidebar:
    st.markdown("## Configuration")
    st.info("You are working with your current database/schema.")
    if st.button("Reset Conversation", key="reset"):
        st.session_state.messages = []
        st.rerun()

# Session message memory
if "messages" not in st.session_state:
    st.session_state.messages = []

def run_agent(query: str):
    """
    Uses the built-in Snowflake Cortex LLM (no custom model).
    It attempts to convert NL to SQL or run SQL directly if you type SQL.
    """
    # Get project session
    session = st.connection("snowflake")
    # If user input is plain SQL, run directly (advanced users)
    if query.strip().lower().startswith("select") or query.strip().lower().startswith("with"):
        try:
            result = session.query(query)
            data = result.to_pandas()
            return data
        except Exception as e:
            return f"❌ Invalid SQL: {str(e)}"
    # Otherwise, send to Cortex COMPLETE
    cortex_prompt = (
        "You are an expert Snowflake data assistant. "
        "For questions about the data, write a correct SQL query using available tables. "
        "If a plot is requested, return the SQL results and describe the chart type."
    )
    try:
        cortex_sql = (
            f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{cortex_prompt}\\nUser: {query}\\nAssistant:') AS response"
        )
        result = session.query(cortex_sql)
        resp_text = result.collect()[0]
        # Try extracting code from answer if any!
        code = ""
        import re
        match = re.search(r"``````", resp_text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            try:
                df = session.query(code)
                data = df.to_pandas()
                return {"llm_response": resp_text, "df": data, "sql": code}
            except Exception as e:
                return f"{resp_text}\n\n❌ SQL returned by LLM did not work: {e}"
        return resp_text
    except Exception as e:
        return f"❌ Error from LLM: {str(e)}"

def plot_if_possible(agent_response):
    """Plot results if the response is a DataFrame or has SQL results."""
    if isinstance(agent_response, dict):
        # Show LLM natural language explanation
        if "llm_response" in agent_response:
            st.markdown(agent_response["llm_response"])
            # Show the SQL if present
            if "sql" in agent_response and agent_response["sql"]:
                st.code(agent_response["sql"], language="sql")
            # Show and plot DataFrame
            if "df" in agent_response and isinstance(agent_response["df"], pd.DataFrame):
                st.dataframe(agent_response["df"])
                try:
                    st.bar_chart(agent_response["df"])
                except Exception:
                    pass
    elif isinstance(agent_response, pd.DataFrame):
        st.dataframe(agent_response)
        try:
            st.bar_chart(agent_response)
        except Exception:
            pass
    else:
        st.markdown(agent_response)

# Show Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        plot_if_possible(msg['content'])

# Chat input
user_input = st.chat_input("Ask an analytics/SQL/BI question, or write a SELECT query directly...")
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Working..."):
        agent_response = run_agent(user_input)

    with st.chat_message("assistant"):
        plot_if_possible(agent_response)

    st.session_state.messages.append({"role": "assistant", "content": agent_response})
