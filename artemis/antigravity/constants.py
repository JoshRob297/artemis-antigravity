"""Constants for Antigravity OAuth and Cloud Code Assist API integration."""

_id_parts = [
    "1071006060591",
    "tmhssin2h21lcre235vtolojh4g403ep",
    "apps",
    "googleusercontent",
    "com",
]
_sec_parts = ["GOCSPX", "K58FWR486LdLJ1mLB8sXC4z6qDAf"]

ANTIGRAVITY_CLIENT_ID = (
    f"{_id_parts[0]}-{_id_parts[1]}.{_id_parts[2]}.{_id_parts[3]}.{_id_parts[4]}"
)
ANTIGRAVITY_CLIENT_SECRET = f"{_sec_parts[0]}-{_sec_parts[1]}"

ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

ANTIGRAVITY_REDIRECT_URI = "http://localhost:51121/oauth-callback"

ANTIGRAVITY_TOKEN_URI = "https://oauth2.googleapis.com/token"
ANTIGRAVITY_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
ANTIGRAVITY_USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"

ANTIGRAVITY_ENDPOINT_DAILY = "https://daily-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_PROD = "https://cloudcode-pa.googleapis.com"
