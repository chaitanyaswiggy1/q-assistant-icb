-- =============================================================================
-- Q Assistant (ICB) — Snowflake Setup
-- Run in Snowsight (worksheet) or SnowSQL.
-- Replace every <PLACEHOLDER> with your actual values.
-- Step 5 (External Access Integration) requires ACCOUNTADMIN or SYSADMIN.
-- =============================================================================

-- 0. Set context
USE DATABASE <DATABASE>;      -- e.g. DINEOUT_DB
USE SCHEMA   <SCHEMA>;        -- e.g. PUBLIC or PARTNER_EXP
USE WAREHOUSE <WAREHOUSE>;    -- e.g. COMPUTE_WH


-- 1. Internal stage — holds app file, data files, environment.yml
CREATE OR REPLACE STAGE Q_ASSISTANT_STAGE
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Q Assistant (ICB) app and data files';


-- 2. Upload files
--    Option A — SnowSQL (run in your terminal, not in a worksheet):
--
--    snowsql -a <ACCOUNT> -u <YOUR_USER> -d <DATABASE> -s <SCHEMA>
--
--    PUT 'file:///Users/chaitanya.ponnada/q-assistant-icb/q_builder.py'
--        @Q_ASSISTANT_STAGE/q_builder.py       AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
--    PUT 'file:///Users/chaitanya.ponnada/q-assistant-icb/environment.yml'
--        @Q_ASSISTANT_STAGE/environment.yml    AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
--    PUT 'file:///Users/chaitanya.ponnada/Downloads/ICB Menu.json'
--        @Q_ASSISTANT_STAGE/ICB_Menu.json      AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
--    PUT 'file:///Users/chaitanya.ponnada/Downloads/ICB_1010981_item_analytics_60days.csv'
--        @Q_ASSISTANT_STAGE/ICB_analytics.csv  AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--
--    Option B — Snowsight UI:
--    Data → Databases → <DATABASE> → <SCHEMA> → Stages → Q_ASSISTANT_STAGE → + Files


-- 3. Portkey API key — stored as a Snowflake Secret
CREATE OR REPLACE SECRET PORTKEY_SECRET
    TYPE = GENERIC_STRING
    SECRET_STRING = '<YOUR_PORTKEY_API_KEY>';    -- e.g. pk-xxxxxxxxxxxxxxxx


-- 4. Network rule — allow outbound HTTPS to Portkey
CREATE OR REPLACE NETWORK RULE PORTKEY_NETWORK_RULE
    MODE       = EGRESS
    TYPE       = HOST_PORT
    VALUE_LIST = ('api.portkey.ai:443');


-- 5. External Access Integration (requires ACCOUNTADMIN or SYSADMIN)
--    If you don't have this role, ask your Snowflake admin to run this block.
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION PORTKEY_EAI
    ALLOWED_NETWORK_RULES        = (<DATABASE>.<SCHEMA>.PORTKEY_NETWORK_RULE)
    ALLOWED_AUTHENTICATION_SECRETS = (<DATABASE>.<SCHEMA>.PORTKEY_SECRET)
    ENABLED = TRUE;


-- 6. Create the Streamlit app
CREATE OR REPLACE STREAMLIT Q_ASSISTANT
    ROOT_LOCATION                = '@<DATABASE>.<SCHEMA>.Q_ASSISTANT_STAGE'
    MAIN_FILE                    = 'q_builder.py'
    QUERY_WAREHOUSE              = '<WAREHOUSE>'
    EXTERNAL_ACCESS_INTEGRATIONS = (PORTKEY_EAI)
    SECRETS                      = ('portkey_key' = <DATABASE>.<SCHEMA>.PORTKEY_SECRET)
    COMMENT                      = 'Q — ICB Dining Assistant (internal)';


-- 7. Verify and get the app URL
SHOW STREAMLITS;
-- Click the link in the result to open the app.
-- Access is controlled by Snowflake — only users in your Snowflake account can open it.
